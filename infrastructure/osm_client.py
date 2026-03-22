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
    if tags.get("mountain_pass") == "yes": return "mountain_pass"
    nat = tags.get("natural", "")
    if nat == "saddle":  return "saddle"
    if nat == "peak":    return "peak"
    if nat == "volcano": return "volcano"
    return "other"


def _point_au_km(points_gpx: list, km_cible: float) -> tuple | None:
    if not points_gpx:
        return None
    dist_cum = 0.0
    best_pt, best_diff = points_gpx[0], float("inf")
    for i in range(1, len(points_gpx)):
        p1, p2 = points_gpx[i-1], points_gpx[i]
        dist_cum += p1.distance_2d(p2) or 0.0
        diff = abs(dist_cum / 1000 - km_cible)
        if diff < best_diff:
            best_diff = diff
            best_pt   = p2
    return best_pt.latitude, best_pt.longitude


@st.cache_data(ttl=CACHE_OSM_TTL, show_spinner=False)
def _requete_osm_cached(min_lat, max_lat, min_lon, max_lon) -> list:
    query = f"""
[out:json][timeout:{TIMEOUT_OSM_S}][bbox:{min_lat:.5f},{min_lon:.5f},{max_lat:.5f},{max_lon:.5f}];
(
  node["mountain_pass"="yes"];
  node["natural"="saddle"]["name"];
  node["natural"="peak"]["name"];
  node["natural"="volcano"]["name"];
);
out body;
"""
    headers = {"User-Agent": "VeloMeteoApp/8.0 Streamlit",
               "Content-Type": "application/x-www-form-urlencoded"}
    for tentative in range(MAX_RETRIES_OSM):
        serveur = OVERPASS_URLS[tentative % len(OVERPASS_URLS)]
        try:
            r = requests.post(serveur, data={"data": query},
                              headers=headers, timeout=TIMEOUT_OSM_S)
            if r.status_code in [429, 503, 504]:
                raise Exception(f"Serveur surchargé ({r.status_code})")
            r.raise_for_status()
            nodes = []
            for el in r.json().get("elements", []):
                tags = el.get("tags", {})
                nom  = tags.get("name:fr") or tags.get("name") or tags.get("name:en")
                if not nom:
                    continue
                alt_tag = tags.get("ele")
                try:    alt = int(float(alt_tag)) if alt_tag else None
                except: alt = None
                t = _type_noeud(tags)
                nodes.append(dict(nom=nom, alt=alt, lat=el["lat"], lon=el["lon"],
                                  type=t, priorite=OSM_TYPES_PRIORITE.get(t, 99)))
            return nodes
        except Exception as e:
            logger.warning(f"Overpass tentative {tentative+1} ({serveur}) : {e}")
            if tentative < MAX_RETRIES_OSM - 1:
                time.sleep(RETRY_DELAYS[min(tentative, len(RETRY_DELAYS)-1)])
    st.toast("⚠️ OSM instable — noms des cols potentiellement manquants.")
    return []


def enrichir_cols(ascensions: list, points_gpx: list) -> list:
    """Enrichit chaque ascension avec le nom OSM du col/sommet."""
    if not ascensions or not points_gpx:
        return ascensions

    coords_sommets = []
    for asc in ascensions:
        coords = _point_au_km(points_gpx, asc["_sommet_km"])
        if coords:
            try:
                alt_gpx = int(asc.get("Alt. sommet", "").replace(" m", "").strip() or 0) or None
            except (ValueError, AttributeError):
                alt_gpx = None
            coords_sommets.append((asc, coords[0], coords[1], alt_gpx))
        else:
            asc["Nom"] = "—"; asc["Nom OSM alt"] = None

    if not coords_sommets:
        return ascensions

    lats    = [p.latitude  for p in points_gpx]
    lons    = [p.longitude for p in points_gpx]
    min_lat = min(lats) - 0.05; max_lat = max(lats) + 0.05
    min_lon = min(lons) - 0.05; max_lon = max(lons) + 0.05

    osm_nodes = _requete_osm_cached(
        round(min_lat, 5), round(max_lat, 5),
        round(min_lon, 5), round(max_lon, 5)
    )

    for asc, lat, lon, alt_gpx in coords_sommets:
        candidats = []
        for nd in osm_nodes:
            dist = haversine(lat, lon, nd["lat"], nd["lon"])
            if dist <= RAYON_SOMMET_M:
                if alt_gpx and nd["alt"] and abs(nd["alt"] - alt_gpx) > 200:
                    continue
                candidats.append({**nd, "dist": dist})
        if not candidats:
            asc["Nom"] = "—"; asc["Nom OSM alt"] = None
        else:
            candidats.sort(key=lambda c: (c["priorite"], c["dist"]))
            m = candidats[0]
            asc["Nom"] = m["nom"]; asc["Nom OSM alt"] = m["alt"]

    return ascensions


@st.cache_data(ttl=CACHE_OSM_TTL, show_spinner=False)
def recuperer_points_eau(coords_gpx: tuple) -> list:
    """Récupère les fontaines, sources et points d'eau potable."""
    if not coords_gpx:
        return []

    lats    = [lat for lat, lon in coords_gpx]
    lons    = [lon for lat, lon in coords_gpx]
    min_lat = min(lats) - 0.01; max_lat = max(lats) + 0.01
    min_lon = min(lons) - 0.01; max_lon = max(lons) + 0.01

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
    data    = None
    for url in OVERPASS_URLS:
        try:
            r = requests.post(url, data={"data": query},
                              headers={"User-Agent": "VeloMeteoApp/8.0"},
                              timeout=20)
            if r.status_code == 200:
                data = r.json(); break
        except Exception as e:
            logger.warning(f"Points d'eau — {url} : {e}")

    if not data:
        st.toast("⚠️ Points d'eau indisponibles (Overpass timeout).")
        return []

    points = []
    for el in data.get("elements", []):
        lat_w, lon_w = el["lat"], el["lon"]
        tags = el.get("tags", {})
        for lat_p, lon_p in pts_ref:
            if abs(lat_w - lat_p) < 0.015 and abs(lon_w - lon_p) < 0.015:
                if haversine(lat_w, lon_w, lat_p, lon_p) <= RAYON_EAU_M:
                    amenity  = tags.get("amenity", "")
                    natural  = tags.get("natural", "")
                    type_eau = ("fontaine" if amenity == "drinking_water"
                                else "borne" if amenity == "water_point"
                                else "source" if natural == "spring"
                                else "eau")
                    points.append(dict(lat=lat_w, lon=lon_w,
                                       nom=tags.get("name", "Point d'eau"),
                                       type=type_eau))
                    break
    return points
