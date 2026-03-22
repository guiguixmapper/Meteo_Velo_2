"""
infrastructure/open_meteo_client.py
=====================================
Optimisé : Récupération de la météo en BATCH pour une vitesse maximale.
"""

import streamlit as st
import requests
import logging
from datetime import datetime
from config.settings import CACHE_METEO_TTL, RETRY_METEO_DELAYS

logger = logging.getLogger(__name__)

# ==============================================================================
# UTILITAIRES VISUELS
# ==============================================================================

def obtenir_icone_meteo(code: int) -> str:
    mapping = {
        0: "☀️ Clair", 1: "⛅ Éclaircies", 2: "⛅ Éclaircies", 3: "☁️ Couvert",
        45: "🌫️ Brouillard", 48: "🌫️ Brouillard",
        51: "🌦️ Bruine", 53: "🌦️ Bruine", 55: "🌦️ Bruine",
        61: "🌧️ Pluie", 63: "🌧️ Pluie", 65: "🌧️ Pluie",
        66: "🌧️ Pluie", 67: "🌧️ Pluie",
        80: "🌧️ Pluie", 81: "🌧️ Pluie", 82: "🌧️ Pluie",
        71: "❄️ Neige", 73: "❄️ Neige", 75: "❄️ Neige",
        77: "❄️ Neige", 85: "❄️ Neige", 86: "❄️ Neige",
        95: "⛈️ Orage", 96: "⛈️ Orage", 99: "⛈️ Orage"
    }
    return mapping.get(code, "☁️ Inconnu")

def label_uv(uv: float) -> tuple:
    if uv >= 11: return ("🟣", "Extrême", "#7e22ce")
    if uv >= 8:  return ("🔴", "Très élevé", "#ef4444")
    if uv >= 6:  return ("🟠", "Élevé", "#f97316")
    if uv >= 3:  return ("🟡", "Modéré", "#eab308")
    return ("🟢", "Faible", "#22c55e")

def label_pollen(val: float) -> str:
    if val > 100: return "🔴 Élevé"
    if val > 10:  return "🟡 Modéré"
    return "🟢 Faible"

# ==============================================================================
# CŒUR DU CLIENT : RÉCUPÉRATION BATCH
# ==============================================================================

@st.cache_data(ttl=CACHE_METEO_TTL, show_spinner=False)
def recuperer_meteo_batch(latitudes: list, longitudes: list, dates_iso: list) -> list:
    """
    Récupère la météo pour TOUS les points du parcours en UNE SEULE requête.
    Vitesse : x10 à x50 par rapport à l'ancien système.
    """
    if not latitudes or not longitudes:
        return []

    # Open-Meteo accepte des listes séparées par des virgules
    lats_str = ",".join([str(round(l, 4)) for l in latitudes])
    lons_str = ",".join([str(round(l, 4)) for l in longitudes])
    
    # On récupère la date min et max pour optimiser la fenêtre de requête
    start_d = min(dates_iso).split('T')[0]
    end_d   = max(dates_iso).split('T')[0]

    params = {
        "latitude": lats_str,
        "longitude": lons_str,
        "hourly": "temperature_2m,weathercode,wind_speed_10m,wind_gusts_10m,wind_direction_10m,precipitation_probability",
        "timezone": "auto",
        "start_date": start_d,
        "end_date": end_d
    }

    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=15)
        r.raise_for_status()
        data_list = r.json()
        
        # Si un seul point est demandé, l'API renvoie un dict, sinon une liste de dicts
        if isinstance(data_list, dict):
            data_list = [data_list]

        resultats_finaux = []
        for i, data in enumerate(data_list):
            target_time = dates_iso[i]
            # Extraction des données pour l'heure précise du passage
            res = _extraire_point_precis(data, target_time)
            resultats_finaux.append(res)
            
        return resultats_finaux

    except Exception as e:
        logger.error(f"Erreur Batch Météo : {e}")
        return [{} for _ in latitudes]

def _extraire_point_precis(data: dict, target_time: str) -> dict:
    """Helper interne pour filtrer l'heure exacte dans un flux horaire."""
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    
    if target_time not in times:
        # Si l'heure exacte n'est pas là, on prend la plus proche (tronquée à l'heure)
        target_time = target_time[:14] + "00"
        
    if target_time in times:
        idx = times.index(target_time)
        v_vent = hourly.get("wind_speed_10m", [0])[idx]
        return {
            "temp_val":    hourly.get("temperature_2m", [None])[idx],
            "vent_val":    v_vent,
            "rafales_val": hourly.get("wind_gusts_10m", [v_vent])[idx],
            "dir_deg":     hourly.get("wind_direction_10m", [0])[idx],
            "pluie_pct":   hourly.get("precipitation_probability", [0])[idx],
            "Ciel":        obtenir_icone_meteo(hourly.get("weathercode", [0])[idx])
        }
    return {}

# ==============================================================================
# AUTRES SERVICES (SERVICES SECONDAIRES)
# ==============================================================================

@st.cache_data(ttl=CACHE_METEO_TTL)
def recuperer_fuseau(lat, lon) -> str:
    try:
        r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&timezone=auto", timeout=5)
        return r.json().get("timezone", "UTC")
    except: return "UTC"

@st.cache_data(ttl=CACHE_METEO_TTL)
def recuperer_soleil(lat, lon, date_str):
    try:
        r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=sunrise,sunset&timezone=auto&start_date={date_str}&end_date={date_str}", timeout=5)
        d = r.json().get("daily", {})
        return {
            "lever": datetime.fromisoformat(d["sunrise"][0]),
            "coucher": datetime.fromisoformat(d["sunset"][0])
        }
    except: return None

@st.cache_data(ttl=CACHE_METEO_TTL)
def recuperer_uv_pollen(lat, lon, date_str):
    res = {"uv_max": 0, "uv_label": "—", "pollens": []}
    # UV
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast",
                         params=dict(latitude=lat, longitude=lon, daily="uv_index_max", 
                                     timezone="auto", start_date=date_str, end_date=date_str), timeout=5)
        val = r.json().get("daily", {}).get("uv_index_max", [0])[0]
        emoji, lbl, coul = label_uv(val)
        res.update(uv_max=val, uv_emoji=emoji, uv_label=lbl, uv_couleur=coul)
    except: pass

    # Pollens
    try:
        r = requests.get("https://air-quality-api.open-meteo.com/v1/air-quality",
                         params=dict(latitude=lat, longitude=lon, hourly="grass_pollen,birch_pollen,olive_pollen",
                                     timezone="auto", start_date=date_str, end_date=date_str), timeout=5)
        h = r.json().get("hourly", {})
        for k, name in [("grass_pollen", "🌾 Graminées"), ("birch_pollen", "🌳 Bouleau"), ("olive_pollen", "🫒 Olivier")]:
            val = max(h.get(k, [0]))
            res["pollens"].append({"nom": name, "label": label_pollen(val)})
    except: pass
    return res
