"""
infrastructure/open_meteo_client.py
Version simple, robuste et sans prise de tête
"""

import streamlit as st
import requests
import logging
import time
from datetime import datetime
from config.settings import CACHE_METEO_TTL, RETRY_METEO_DELAYS

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# MÉTÉO BATCH (PRINCIPAL)
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_METEO_TTL, show_spinner=False)
def recuperer_meteo_batch(checkpoints_frozen, is_past=False, date_str=None):
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

    for delay in RETRY_METEO_DELAYS + [None]:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 429:
                if delay is None:
                    return None
                time.sleep(delay)
                continue
            r.raise_for_status()
            return [r.json()]
        except Exception:
            if delay is None:
                return None
            time.sleep(delay)

    return None


# ─────────────────────────────────────────────────────────────
# EXTRACTION MÉTÉO
# ─────────────────────────────────────────────────────────────

def extraire_meteo(donnees_api, heure_api):
    from core.utils.geo import wind_chill

    vide = dict(
        Ciel="—", temp_val=None, Pluie="—", pluie_pct=None,
        vent_val=None, rafales_val=None, Dir="—",
        dir_deg=None, effet="—", ressenti=None
    )

    if not donnees_api or "hourly" not in donnees_api:
        return vide

    heures = donnees_api["hourly"].get("time", [])
    if heure_api not in heures:
        return vide

    i = heures.index(heure_api)
    h = donnees_api["hourly"]

    def val(k):
        return h.get(k, [None])[i]

    temp = val("temperature_2m")
    vent = val("wind_speed_10m")
    dir_deg = val("wind_direction_10m")

    pluie_pct = None
    if "precipitation_probability" in h:
        pluie_pct = val("precipitation_probability")

    return dict(
        Ciel="—",
        temp_val=temp,
        Pluie=f"{pluie_pct}%" if pluie_pct is not None else "—",
        pluie_pct=pluie_pct,
        vent_val=vent,
        rafales_val=val("wind_gusts_10m"),
        Dir="—",
        dir_deg=dir_deg,
        effet="—",
        ressenti=wind_chill(temp, vent) if temp and vent else None,
    )


# ─────────────────────────────────────────────────────────────
# SOLEIL & FUSEAU
# ─────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def recuperer_soleil(lat, lon, date_str):
    try:
        r = requests.get(
            f"https://api.sunrise-sunset.org/json?lat={lat}&lng={lon}&date={date_str}&formatted=0",
            timeout=10
        )
        r.raise_for_status()
        d = r.json().get("results", {})
        return {
            "lever": datetime.fromisoformat(d["sunrise"]),
            "coucher": datetime.fromisoformat(d["sunset"]),
        }
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def recuperer_fuseau(lat, lon):
    try:
        r = requests.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m&timezone=auto",
            timeout=10
        )
        r.raise_for_status()
        return r.json().get("timezone", "UTC")
    except Exception:
        return "UTC"


# ─────────────────────────────────────────────────────────────
# UV & POLLEN (SIMPLE)
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_METEO_TTL, show_spinner=False)
def recuperer_uv_pollen(lat, lon, date_str):
    return {
        "uv_max": None,
        "uv_emoji": "—",
        "uv_label": "Données indisponibles",
        "uv_couleur": "#9ca3af",
        "pollens": []
    }
