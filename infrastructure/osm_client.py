"""
infrastructure/osm_client.py
==============================
Appels Overpass API (cols, points d'eau).
Déclenchés uniquement par les boutons de la barre latérale.
"""

import requests
import logging
import time
from config.settings import (
    OVERPASS_URLS, RAYON_SOMMET_M, RAYON_EAU_M,
    TIMEOUT_OSM_S, MAX_RETRIES_OSM, RETRY_DELAYS,
    OSM_TYPES_PRIORITE,
)
from core.utils.geo import haversine

logger = logging.getLogger(__name__)


def _type_noeud(tags: dict) -> str:
    if tags.get("mountain_pass") == "yes":
        return "mountain_pass"
    nat = tags.get("natural", "")
    if nat == "saddle":
        return "saddle"
    if nat == "peak":
        return "peak"
    if nat == "volcano":
        return "volcano"
    if tags.get("place") == "locality":
        return "col_locality"
    return "other"


def _point_au_km(points_gpx: list, km_cible: float) -> tuple | None:
    if not points_gpx:
        return None
    dist_cum = 0.0
    best_pt, best_diff = points_gpx[0], float("inf")
    for i in range(1, len(points_gpx)):
        p1, p2 = points_gpx[i - 1], points_gpx[i]
        dist_cum += p1.distance_2d(p2) or 0.0
        diff = abs(dist_cum / 1000 - km_cible)
        if diff < best_diff:
            best_diff = diff
            best_pt = p2
    return best_pt.latitude, best_pt.longitude


def _parse_osm_nodes(payload: dict) -> list:
    nodes = []
    for el in payload.get("elements", []):
        if "lat" not in el or "lon" not in el:
            continue
        tags = el.get("tags", {})
        nom = tags.get("name:fr") or tags.get("name") or tags.get("name:en")
        if not nom:
            continue
        alt_tag = tags.get("ele")
        try:
            alt = int(float(alt_tag)) if alt_tag else None
        except (TypeError, ValueError):
            alt = None
        t = _type_noeud(tags)
        nodes.append(dict(
            nom=nom, alt=alt, lat=el["lat"], lon=el["lon"],
            type=t, priorite=OSM_TYPES_PRIORITE.get(t, 99),
        ))
    return nodes


def _overpass_json(query: str) -> tuple[dict | None, str | None]:
    """POST une requête courte. Essaie le miroir suivant sans longue attente."""
    headers = {
        "User-Agent": "MeteoVelo/2 (github.com/guiguixmapper/Meteo_Velo_2)",
        "Accept": "application/json",
    }
    last_error = "aucun serveur Overpass n'a répondu"
    essais = OVERPASS_URLS[:MAX_RETRIES_OSM]
    for i, url in enumerate(essais):
        hote = url.split("/")[2]
        try:
            r = requests.post(
                url,
                data={"data": query},
                headers=headers,
                timeout=(6, TIMEOUT_OSM_S + 5),
            )
            if r.status_code == 200:
                try:
                    payload = r.json()
                except ValueError:
                    last_error = f"réponse illisible ({hote})"
                else:
                    remark = str(payload.get("remark") or "").strip()
                    elements = payload.get("elements")
                    if remark and not elements:
                        last_error = f"{hote}: {remark[:160]}"
                        logger.warning("OSM %s", last_error)
                    else:
                        return payload, None
            else:
                last_error = f"HTTP {r.status_code} ({hote})"
                logger.warning("OSM %s : %s", hote, last_error)
        except requests.exceptions.Timeout:
            last_error = f"timeout {TIMEOUT_OSM_S}s ({hote})"
            logger.warning("OSM %s", last_error)
        except requests.exceptions.ConnectionError:
            last_error = f"connexion impossible ({hote})"
            logger.warning("OSM %s", last_error)
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            logger.warning("OSM %s : %s", hote, last_error)
        if i < len(essais) - 1:
            time.sleep(RETRY_DELAYS[min(i, len(RETRY_DELAYS) - 1)])
    return None, last_error


def _echantillon_route(coords: list, pas_m: float, max_pts: int) -> list:
    """Quelques points le long du tracé, pas toute la trace."""
    if not coords:
        return []
    choisi = [coords[0]]
    acc = 0.0
    prev = coords[0]
    for lat, lon in coords[1:]:
        acc += haversine(prev[0], prev[1], lat, lon)
        prev = (lat, lon)
        if acc >= pas_m:
            choisi.append((lat, lon))
            acc = 0.0
            if len(choisi) >= max_pts:
                return choisi
    fin = coords[-1]
    if choisi[-1] != fin and len(choisi) < max_pts:
        choisi.append(fin)
    return choisi


def _bbox_deg(coords: list, pad_deg: float = 0.015) -> tuple[float, float, float, float]:
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return (
        min(lats) - pad_deg,
        min(lons) - pad_deg,
        max(lats) + pad_deg,
        max(lons) + pad_deg,
    )


def _boites_cols(coords: list) -> list[tuple[float, float, float, float]]:
    """Une bbox, ou deux si le parcours est trop étendu pour une seule requête."""
    south, west, north, east = _bbox_deg(coords)
    if (north - south) <= 0.8 and (east - west) <= 1.2:
        return [(south, west, north, east)]
    milieu = sorted(coords, key=lambda c: c[0])
    coupe = max(1, len(milieu) // 2)
    return [_bbox_deg(milieu[:coupe]), _bbox_deg(milieu[coupe:])]


def _query_cols(south: float, west: float, north: float, east: float) -> str:
    # Uniquement cols et cols nommés. Pas de sommets, volcans, ni regex :
    # ces filtres font rejeter ou expirer la requête côté Overpass.
    return (
        f"[out:json][timeout:{TIMEOUT_OSM_S}];\n"
        "(\n"
        f'  node["mountain_pass"="yes"]({south:.5f},{west:.5f},{north:.5f},{east:.5f});\n'
        f'  node["natural"="saddle"]["name"]({south:.5f},{west:.5f},{north:.5f},{east:.5f});\n'
        f'  node["natural"="peak"]["name"]({south:.5f},{west:.5f},{north:.5f},{east:.5f});\n'
        ");\n"
        "out body;\n"
    )


def chercher_noeuds_cols(coords: list) -> tuple[list, str | None]:
    if not coords:
        return [], None
    vus = []
    dedup = set()
    for lat, lon in coords:
        cle = (round(lat, 3), round(lon, 3))
        if cle not in dedup:
            dedup.add(cle)
            vus.append((lat, lon))
    noeuds = []
    deja = set()
    erreurs = []
    for boite in _boites_cols(vus):
        payload, err = _overpass_json(_query_cols(*boite))
        if not payload:
            if err:
                erreurs.append(err)
            continue
        for nd in _parse_osm_nodes(payload):
            cle = (round(nd["lat"], 5), round(nd["lon"], 5), nd["nom"])
            if cle in deja:
                continue
            deja.add(cle)
            noeuds.append(nd)
    if noeuds:
        return noeuds, None
    return [], (erreurs[-1] if erreurs else None)


def enrichir_cols(ascensions: list, points_gpx: list) -> tuple[list, str | None]:
    """Enrichit chaque ascension avec le nom OSM du col. Une requête manuelle."""
    if not ascensions:
        return ascensions, None

    coords_sommets = []
    for asc in ascensions:
        lat = asc.get("_lat_sommet")
        lon = asc.get("_lon_sommet")
        if lat is None or lon is None:
            coords = _point_au_km(points_gpx, asc.get("_sommet_km", 0)) if points_gpx else None
            if coords:
                lat, lon = coords
        if lat is None or lon is None:
            asc["Nom"] = "\u2014"
            asc["Nom OSM alt"] = None
            continue
        try:
            alt_gpx = int(str(asc.get("Alt. sommet", "")).replace(" m", "").strip() or 0) or None
        except (ValueError, AttributeError):
            alt_gpx = None
        coords_sommets.append((asc, float(lat), float(lon), alt_gpx))

    if not coords_sommets:
        return ascensions, None

    osm_nodes, err = chercher_noeuds_cols([(lat, lon) for _, lat, lon, _ in coords_sommets])
    if err and not osm_nodes:
        logger.warning("OSM cols : échec pour %s sommets — %s", len(coords_sommets), err)
        for asc, _, _, _ in coords_sommets:
            asc.setdefault("Nom", "\u2014")
            asc.setdefault("Nom OSM alt", None)
        return ascensions, err

    logger.info("OSM cols : %s nœuds pour %s sommets", len(osm_nodes), len(coords_sommets))
    for asc, lat, lon, alt_gpx in coords_sommets:
        candidats = []
        for nd in osm_nodes:
            dist = haversine(lat, lon, nd["lat"], nd["lon"])
            if dist <= RAYON_SOMMET_M:
                if alt_gpx and nd["alt"] and abs(nd["alt"] - alt_gpx) > 250:
                    continue
                candidats.append({**nd, "dist": dist})
        if not candidats:
            asc["Nom"] = "\u2014"
            asc["Nom OSM alt"] = None
        else:
            candidats.sort(key=lambda c: (c["priorite"], c["dist"]))
            m = candidats[0]
            asc["Nom"] = m["nom"]
            asc["Nom OSM alt"] = m["alt"]

    return ascensions, None


def recuperer_points_eau(coords_gpx: tuple) -> tuple[list, str | None]:
    """Fontaines et bornes le long du tracé. Requête manuelle, sans sources brutes.

    Retourne (points, erreur). erreur est None si le serveur a répondu.
    """
    if not coords_gpx:
        return [], None

    coords = list(coords_gpx)
    longueur = 0.0
    for i in range(1, len(coords)):
        longueur += haversine(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1])
    pas = max(4000.0, longueur / 12.0)
    echantillons = _echantillon_route(coords, pas_m=pas, max_pts=12)
    if not echantillons:
        return [], None

    rayon = int(RAYON_EAU_M)
    lignes = []
    for lat, lon in echantillons:
        lignes.append(
            f'  node["amenity"="drinking_water"](around:{rayon},{lat:.5f},{lon:.5f});'
        )
        lignes.append(
            f'  node["amenity"="water_point"](around:{rayon},{lat:.5f},{lon:.5f});'
        )
    query = (
        f"[out:json][timeout:{TIMEOUT_OSM_S}];\n"
        "(\n" + "\n".join(lignes) + "\n);\n"
        "out body;\n"
    )
    data, err = _overpass_json(query)
    if not data:
        return [], err

    points = []
    deja = set()
    for el in data.get("elements", []):
        if "lat" not in el or "lon" not in el:
            continue
        lat_w, lon_w = el["lat"], el["lon"]
        cle = (round(lat_w, 5), round(lon_w, 5))
        if cle in deja:
            continue
        tags = el.get("tags", {})
        for lat_p, lon_p in echantillons:
            if haversine(lat_w, lon_w, lat_p, lon_p) <= RAYON_EAU_M:
                amenity = tags.get("amenity", "")
                type_eau = (
                    "fontaine" if amenity == "drinking_water"
                    else "borne" if amenity == "water_point"
                    else "eau"
                )
                points.append(dict(
                    lat=lat_w, lon=lon_w,
                    nom=tags.get("name", "Point d'eau"),
                    type=type_eau,
                ))
                deja.add(cle)
                break
    return points, None
