"""
infrastructure/open_meteo_client.py
Version complète RESTAURÉE — compatible app.py + route_service.py
"""

import streamlit as st
import requests
import logging
import time
from datetime import datetime
from config.settings import CACHE_METEO_TTL, RETRY_METEO_DELAYS

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# MÉTÉO BATCH
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


# ─────────────────────────────────────────────────
