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
            r = requests.post(serveur, data={"data": query}, headers=headers, timeout=TIMEOUT_OSM_S)
            r.raise_for_status()
            return r.json().get("elements", [])
        except Exception as e:
            logger.warning(f"Overpass retry {tentative+1}/{MAX_RETRIES_OSM} : {e}")
            if tentative < MAX_RETRIES_OSM - 1:
                time.sleep(RETRY_DELAYS[tentative % len(RETRY_DELAYS)])
    return []


@st.cache_data(ttl=CACHE_OSM_TTL, show_spinner=False)
def recuperer_points_eau(_coords_gpx):  # ← underscore ici = on n'hache pas cet argument
    """
    Récupère les points d'eau OSM proches du parcours.
    """
    if not _coords_gpx:
        return []

    lats = [p.latitude for p in _coords_gpx]
    lons = [p.longitude for p in _coords_gpx]
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
    pts_ref = _coords_gpx[::20]  # échantillon pour la proximité
    data = None
    for url in OVERPASS_URLS:
        try:
            r = requests.post(url, data={"data": query},
                              headers={"User-Agent": "VeloMeteoApp/8.0"},
                              timeout=20)
            if r.status_code == 200:
                data = r.json()
                break
        except Exception as e:
            logger.warning(f"Points d'eau — {url} : {e}")

    if not data:
        st.toast("⚠️ Points d'eau indisponibles (Overpass timeout).")
        return []

    points = []
    for el in data.get("elements", []):
        lat_w, lon_w = el["lat"], el["lon"]
        tags = el.get("tags", {})
        for p in pts_ref:
            if haversine(lat_w, lon_w, p.latitude, p.longitude) <= RAYON_EAU_M:
                amenity  = tags.get("amenity", "")
                natural  = tags.get("natural", "")
                type_eau = ("fontaine" if amenity == "drinking_water"
                            else "borne" if amenity == "water_point"
                            else "source" if natural == "spring"
                            else "eau")
                points.append(dict(
                    lat=lat_w,
                    lon=lon_w,
                    nom=tags.get("name", "Point d'eau"),
                    type=type_eau
                ))
                break

    return points
