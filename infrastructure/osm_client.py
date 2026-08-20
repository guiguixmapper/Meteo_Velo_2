"""
infrastructure/osm_client.py
==============================
Appels Overpass API (cols, points d'eau).
"""

import streamlit as st
import requests
import logging
import time
from config.settings import (
    OVERPASS_URLS, RAYON_SOMMET_M, RAYON_EAU_M,
    TIMEOUT_OSM_S, MAX_RETRIES_OSM, RETRY_DELAYS,
    OSM_TYPES_PRIORITE, CACHE_OSM_TTL,
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


def _overpass_query(query: str) -> list:
    """POST Overpass, retry sur plusieurs miroirs. Pas de st.* (cache-safe)."""
    headers = {
        "User-Agent": "VeloMeteoApp/8.0 Streamlit",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    for tentative in range(MAX_RETRIES_OSM):
        serveur = OVERPASS_URLS[tentative % len(OVERPASS_URLS)]
        try:
            r = requests.post(
                serveur, data={"data": query},
                headers=headers, timeout=TIMEOUT_OSM_S,
            )
            if r.status_code in (429, 503, 504):
                raise Exception(f"Serveur surcharge ({r.status_code})")
            r.raise_for_status()
            return _parse_osm_nodes(r.json())
        except requests.exceptions.Timeout:
            logger.warning("OSM tentative %s (%s) : timeout %ss", tentative + 1, serveur, TIMEOUT_OSM_S)
        except requests.exceptions.ConnectionError:
            logger.warning("OSM tentative %s (%s) : connexion refusee", tentative + 1, serveur)
        except Exception as e:
            logger.warning("OSM tentative %s (%s) : %s: %s", tentative + 1, serveur, type(e).__name__, e)
        if tentative < MAX_RETRIES_OSM - 1:
            time.sleep(RETRY_DELAYS[min(tentative, len(RETRY_DELAYS) - 1)])
    logger.warning("OSM - tous les serveurs Overpass indisponibles")
    return []


@st.cache_data(ttl=CACHE_OSM_TTL, show_spinner=False)
def _requete_osm_around(sommets: tuple) -> list:
    """Cols / sommets dans un rayon autour de chaque sommet d'ascension."""
    if not sommets:
        return []
    sommets = sommets[:40]
    rayon = int(RAYON_SOMMET_M)
    blocs = []
    for lat, lon in sommets:
        blocs.append(
            f'  node["mountain_pass"="yes"](around:{rayon},{lat:.5f},{lon:.5f});\n'
            f'  node["natural"="saddle"]["name"](around:{rayon},{lat:.5f},{lon:.5f});\n'
            f'  node["natural"="peak"]["name"](around:{rayon},{lat:.5f},{lon:.5f});\n'
            f'  node["natural"="volcano"]["name"](around:{rayon},{lat:.5f},{lon:.5f});\n'
            f'  node["place"="locality"]["name"~"^[Cc]ol ",i](around:{rayon},{lat:.5f},{lon:.5f});'
        )
    query = (
        f"[out:json][timeout:{TIMEOUT_OSM_S}];\n"
        "(\n" + "\n".join(blocs) + "\n);\nout body;"
    )
    return _overpass_query(query)


def enrichir_cols(ascensions: list, points_gpx: list) -> list:
    """Enrichit chaque ascension avec le nom OSM du col/sommet."""
    if not ascensions:
        return ascensions

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
        return ascensions

    frozen = tuple((round(lat, 4), round(lon, 4)) for _, lat, lon, _ in coords_sommets)
    osm_nodes = _requete_osm_around(frozen)
    logger.info("OSM cols : %s noeuds pour %s sommets", len(osm_nodes), len(coords_sommets))

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

    return ascensions


@st.cache_data(ttl=CACHE_OSM_TTL, show_spinner=False)
def recuperer_points_eau(coords_gpx: tuple) -> list:
    """Recupere les fontaines, sources et points d'eau potable.

    Ne jamais appeler st.* ici : le cache Streamlit rejoue les widgets au hit
    et plante (CacheReplayClosureError) si le layout a change.
    """
    if not coords_gpx:
        return []

    lats = [lat for lat, lon in coords_gpx]
    lons = [lon for lat, lon in coords_gpx]
    min_lat = min(lats) - 0.01
    max_lat = max(lats) + 0.01
    min_lon = min(lons) - 0.01
    max_lon = max(lons) + 0.01

    query = f"""
[out:json][timeout:20][bbox:{min_lat:.5f},{min_lon:.5f},{max_lat:.5f},{max_lon:.5f}];
(
  node["amenity"="drinking_water"];
  node["amenity"="water_point"];
  node["natural"="spring"]["drinking_water"="yes"];
  node["natural"="spring"]["name"];
);
out body;
"""
    pts_ref = coords_gpx[::20]
    data = None
    last_error = None
    for url in OVERPASS_URLS:
        try:
            r = requests.post(
                url, data={"data": query},
                headers={"User-Agent": "VeloMeteoApp/8.0"},
                timeout=20,
            )
            if r.status_code == 200:
                data = r.json()
                break
            if r.status_code == 429:
                last_error = f"Rate limit ({r.status_code})"
                logger.warning("Points d'eau -- %s : Rate limit (429)", url)
            else:
                last_error = f"HTTP {r.status_code}"
                logger.warning("Points d'eau -- %s : HTTP %s", url, r.status_code)
        except requests.exceptions.Timeout:
            last_error = "Timeout (20s)"
            logger.warning("Points d'eau -- %s : Timeout apres 20s", url)
        except requests.exceptions.ConnectionError:
            last_error = "Connexion refusee"
            logger.warning("Points d'eau -- %s : Connexion refusee", url)
        except Exception as e:
            last_error = str(e)
            logger.warning("Points d'eau -- %s : %s: %s", url, type(e).__name__, e)

    if not data:
        logger.warning("Points d'eau indisponibles -- %s", last_error or "aucun serveur Overpass n'a repondu")
        return []

    points = []
    for el in data.get("elements", []):
        lat_w, lon_w = el["lat"], el["lon"]
        tags = el.get("tags", {})
        for lat_p, lon_p in pts_ref:
            if abs(lat_w - lat_p) < 0.015 and abs(lon_w - lon_p) < 0.015:
                if haversine(lat_w, lon_w, lat_p, lon_p) <= RAYON_EAU_M:
                    amenity = tags.get("amenity", "")
                    natural = tags.get("natural", "")
                    type_eau = (
                        "fontaine" if amenity == "drinking_water"
                        else "borne" if amenity == "water_point"
                        else "source" if natural == "spring"
                        else "eau"
                    )
                    points.append(dict(
                        lat=lat_w, lon=lon_w,
                        nom=tags.get("name", "Point d'eau"),
                        type=type_eau,
                    ))
                    break
    return points
