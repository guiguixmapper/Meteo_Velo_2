"""
infrastructure/open_meteo_client.py
=====================================
Tous les appels à l'API Open-Meteo (météo, UV, pollen).
"""

import streamlit as st
import requests
import logging
import time
from datetime import datetime
from config.settings import CACHE_METEO_TTL, RETRY_METEO_DELAYS, MAX_CHECKPOINTS_METEO

logger = logging.getLogger(__name__)

# ==============================================================================
# UTILITAIRES
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
        95: "⛈️ Orage", 96: "⛈️ Orage", 99: "⛈️ Orage",
    }
    return mapping.get(code, "❓ Inconnu")


def label_uv(uv: float) -> tuple:
    if uv is None:   return "—", "Inconnu", "#9ca3af"
    if uv < 3:       return "🟢", f"UV {uv} — Faible",     "#22c55e"
    if uv < 6:       return "🟡", f"UV {uv} — Modéré",     "#eab308"
    if uv < 8:       return "🟠", f"UV {uv} — Élevé",      "#f97316"
    if uv < 11:      return "🔴", f"UV {uv} — Très élevé", "#ef4444"
    return                 "🟣", f"UV {uv} — Extrême",     "#8b5cf6"


def label_pollen(val: float | None, nom: str) -> str | None:
    if val is None or val < 10: return None
    niv = "Modéré" if val < 50 else "Élevé" if val < 200 else "Très élevé"
    return f"{nom} — {niv} ({int(val)} grains/m³)"


# ==============================================================================
# MÉTÉO BATCH
# ==============================================================================

@st.cache_data(ttl=CACHE_METEO_TTL, show_spinner=False)
def recuperer_meteo_batch(checkpoints_frozen: tuple,
                          is_past: bool = False,
                          date_str: str = None) -> list | None:
    """Météo pour tous les checkpoints. Retry backoff sur 429. Cache 1h."""
    if not checkpoints_frozen:
        return []

    lats = ",".join(str(c[0]) for c in checkpoints_frozen)
    lons = ",".join(str(c[1]) for c in checkpoints_frozen)

    if is_past and date_str:
        url = (
            "https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={lats}&longitude={lons}"
            f"&start_date={date_str}&end_date={date_str}"
            "&hourly=temperature_2m,precipitation,weathercode,"
            "wind_speed_10m,wind_direction_10m,wind_gusts_10m&timezone=auto"
        )
    else:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lats}&longitude={lons}"
            "&hourly=temperature_2m,precipitation_probability,weathercode,"
            "wind_speed_10m,wind_direction_10m,wind_gusts_10m&timezone=auto"
        )

    for attempt, delay in enumerate(RETRY_METEO_DELAYS + [None]):
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 429:
                if delay is not None:
                    logger.warning(f"Météo 429 — tentative {attempt+1}, attente {delay}s")
                    time.sleep(delay)
                    continue
                else:
                    logger.error("Météo 429 — toutes les tentatives épuisées")
                    return None
            r.raise_for_status()
            d = r.json()
            return d if isinstance(d, list) else [d]
        except Exception as e:
            if delay is not None:
                logger.warning(f"Météo erreur {attempt+1} : {e} — retry {delay}s")
                time.sleep(delay)
            else:
                logger.error(f"Erreur météo batch : {e}")
                return None
    return None


def extraire_meteo(donnees_api: dict, heure_api: str) -> dict:
    """Extrait les données météo pour une heure donnée."""
    from core.utils.geo import wind_chill

    vide = dict(Ciel="—", temp_val=None, Pluie="—", pluie_pct=None,
                vent_val=None, rafales_val=None, Dir="—",
                dir_deg=None, effet="—", ressenti=None)

    if not donnees_api or "hourly" not in donnees_api:
        return vide

    heures = donnees_api["hourly"].get("time", [])
    if heure_api not in heures:
        return vide

    idx = heures.index(heure_api)
    h   = donnees_api["hourly"]

    def sg(key, default=None):
        vals = h.get(key, [])
        return vals[idx] if idx < len(vals) else default

    dir_deg   = sg("wind_direction_10m")
    dirs      = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    dir_label = dirs[round(dir_deg / 45) % 8] if dir_deg is not None else "—"
    temp      = sg("temperature_2m")
    vent      = sg("wind_speed_10m")

    try:
        if "precipitation_probability" in h:
            pluie_pct = int(sg("precipitation_probability"))
        elif "precipitation" in h:
            val = sg("precipitation", 0) or 0
            pluie_pct = 100 if val > 0.5 else (50 if val > 0 else 0)
        else:
            pluie_pct = None
    except Exception:
        pluie_pct = None

    return dict(
        Ciel=obtenir_icone_meteo(sg("weathercode", 0)),
        temp_val=temp,
        Pluie=f"{pluie_pct}%" if pluie_pct is not None else "—",
        pluie_pct=pluie_pct,
        vent_val=vent,
        rafales_val=sg("wind_gusts_10m"),
        Dir=dir_label, dir_deg=dir_deg, effet="—",
        ressenti=wind_chill(temp, vent) if (temp is not None and vent is not None) else None,
    )


# ==============================================================================
# SOLEIL
# ==============================================================================

@st.cache_data(show_spinner=False)
def recuperer_soleil(lat: float, lon: float, date_str: str) -> dict | None:
    try:
        r = requests.get(
            f"https://api.sunrise-sunset.org/json?lat={lat}&lng={lon}&date={date_str}&formatted=0",
            timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "OK":
            return None
        return dict(
            lever=datetime.fromisoformat(data["results"]["sunrise"]),
            coucher=datetime.fromisoformat(data["results"]["sunset"]),
        )
    except Exception as e:
        logger.warning(f"Soleil indisponible : {e}")
        return None


@st.cache_data(show_spinner=False)
def recuperer_fuseau(lat: float, lon: float) -> str:
    try:
        r = requests.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m&timezone=auto", timeout=10)
        r.raise_for_status()
        return r.json().get("timezone", "UTC")
    except Exception as e:
        logger.warning(f"Fuseau indisponible : {e}")
        return "UTC"


# ==============================================================================
# UV & POLLEN
# ==============================================================================

@st.cache_data(ttl=CACHE_METEO_TTL, show_spinner=False)
def recuperer_uv_pollen(lat: float, lon: float, date_str: str) -> dict:
    res = dict(uv_max=None, uv_emoji="—", uv_label="Données indisponibles",
               uv_couleur="#9ca3af", pollens=[])
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast",
            params=dict(latitude=lat, longitude=lon, daily="uv_index_max",
                        start_date=date_str, end_date=date_str, timezone="auto"),
            timeout=10)
        r.raise_for_status()
        vals = r.json().get("daily", {}).get("uv_index_max", [])
        if vals and vals[0] is not None:
            uv = round(vals[0], 1)
            emoji, lbl, coul = label_uv(uv)
            res.update(uv_max=uv, uv_emoji=emoji, uv_label=lbl, uv_couleur=coul)
    except Exception as e:
        logger.warning(f"UV indisponible : {e}")

    try:
        r = requests.get("https://air-quality-api.open-meteo.com/v1/air-quality",
            params=dict(latitude=lat, longitude=lon, timezone="auto",
                        hourly="grass_pollen,birch_pollen,olive_pollen,alder_pollen,mugwort_pollen,ragweed_pollen",
                        start_date=date_str, end_date=date_str),
            timeout=10)
        r.raise_for_status()
        hourly = r.json().get("hourly", {})
        ESPECES = [
            ("grass_pollen",   "🌾 Graminées"),
            ("birch_pollen",   "🌳 Bouleau"),
            ("olive_pollen",   "🫒 Olivier"),
            ("alder_pollen",   "🌲 Aulne"),
            ("mugwort_pollen", "🌿 Armoise"),
            ("ragweed_pollen", "🌻 Ambroisie"),
        ]
        for cle, nom in ESPECES:
            vals = [v for v in hourly.get(cle, []) if v is not None]
            if vals:
                lbl = label_pollen(max(vals), nom)
                if lbl:
                    res["pollens"].append(lbl)
    except Exception as e:
        logger.warning(f"Pollen indisponible : {e}")

    return res
