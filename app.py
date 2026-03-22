"""
app.py — Point d'entrée unique
================================
Vélo & Météo — Analyse de tracé GPX.
"""

import streamlit as st
import pandas as pd
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Imports architecture ───────────────────────────────────────────────────────
from ui.styles.theme import CSS
from ui.components.sidebar import render_sidebar, render_export
from ui.components.metrics_banner import render_metrics_banner
from ui.components.map_view import render_map_view
from ui.components.profile_view import render_profile_view
from ui.components.weather_view import render_weather_view
from ui.components.climbs_view import render_climbs_view
from ui.components.detail_view import render_detail_view
from ui.components.coach_view import render_coach_view

from core.services.route_service import (
    parser_gpx, calculer_parcours, enrichir_checkpoints_meteo,
    analyser_meteo_detaillee, calculer_score,
)
from core.services.climbing_service import (
    detecter_ascensions, estimer_temps_col, calculer_calories,
)
from infrastructure.open_meteo_client import (
    recuperer_fuseau, recuperer_soleil, recuperer_uv_pollen, recuperer_meteo_batch,
)
from infrastructure.osm_client import recuperer_points_eau
from config.settings import MAX_CHECKPOINTS_METEO


# ── Cache météo ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def memoire_meteo(frozen):
    latitudes  = [cp[0] for cp in frozen]
    longitudes = [cp[1] for cp in frozen]
    dates_iso  = [cp[2] for cp in frozen]
    return recuperer_meteo_batch(latitudes, longitudes, dates_iso)


def main():
    st.set_page_config(page_title="Vélo & Météo", page_icon="🚴‍♂️", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)

    # ── Sidebar ────────────────────────────────────────────────────────────────
    sidebar_params = render_sidebar()

    fichier     = sidebar_params["fichier"]
    date_dep    = sidebar_params["date_dep"]
    heure_dep   = sidebar_params["heure_dep"]
    vitesse     = sidebar_params["vitesse"]
    mode        = sidebar_params["mode"]
    ref_val     = sidebar_params["ref_val"]
    poids       = sidebar_params["poids"]
    fc_max      = sidebar_params["fc_max"]
    ftp_fc      = sidebar_params["ftp_fc"]
    intervalle  = sidebar_params["intervalle"]
    intervalle_sec = sidebar_params["intervalle_sec"]
    noms_osm    = sidebar_params["noms_osm"]
    gemini_key  = sidebar_params["gemini_key"]
    ph_fuseau   = sidebar_params["ph_fuseau"]
    ph_export   = sidebar_params["ph_export"]

    if not fichier:
        st.info("👈 Chargez un fichier GPX pour commencer l'analyse.")
        return

    # ── Lecture GPX ────────────────────────────────────────────────────────────
    with st.spinner("Lecture du fichier GPX…"):
        points_gpx = parser_gpx(fichier.getvalue())
        if not points_gpx:
            st.error("Impossible de lire le fichier GPX. Vérifiez qu'il est valide.")
            return

    # ── Calcul parcours de base ────────────────────────────────────────────────
    date_depart = datetime.combine(date_dep, heure_dep)
    res = calculer_parcours(points_gpx, vitesse, date_depart, intervalle_sec)

    dist_tot       = res["dist_tot"]
    d_plus         = res["d_plus"]
    d_moins        = res["d_moins"]
    temps_s        = res["temps_s"]
    vit_moy_reelle = res["vit_moy_reelle"]
    heure_arr      = res["heure_arr"]
    checkpoints    = res["checkpoints"]
    df_profil      = res["profil_data"]

    # ── Détection ascensions + points d'eau OSM ────────────────────────────────
    with st.spinner("Analyse du profil altimétrique et points d'eau…"):
        ascensions = detecter_ascensions(df_profil)
        points_eau = recuperer_points_eau(points_gpx)

    # ── Météo ──────────────────────────────────────────────────────────────────
    with st.spinner("Récupération des données météo…"):
        resultats = enrichir_checkpoints_meteo(checkpoints, date_depart)
        analyse_meteo = analyser_meteo_detaillee(resultats)

        milieu_lat = sum(p.latitude for p in points_gpx) / len(points_gpx)
        milieu_lon = sum(p.longitude for p in points_gpx) / len(points_gpx)
        date_str = date_depart.strftime("%Y-%m-%d")
        infos_soleil = recuperer_soleil(milieu_lat, milieu_lon, date_str)
        uv_pollen = recuperer_uv_pollen(milieu_lat, milieu_lon, date_str)

    # ── Score + estimations avancées ───────────────────────────────────────────
    score = calculer_score(dist_tot, d_plus, resultats)

    for asc in ascensions:
        mins_col, vit_col = estimer_temps_col(
            asc["_sommet_km"] - asc["_debut_km"], asc["_pente_moy"], vitesse)
        heure_sommet = date_depart + timedelta(minutes=mins_col)
        asc["Temps col"]      = f"{mins_col} min ({vit_col} km/h)"
        asc["Arrivée sommet"] = heure_sommet.strftime("%H:%M")

    # Correction ici : on passe 'vitesse' en 5e argument
    calories = calculer_calories(dist_tot, d_plus, temps_s, poids, vitesse)

    # ── Affichage ──────────────────────────────────────────────────────────────
    render_metrics_banner(score, dist_tot, d_plus, d_moins, temps_s,
                          vit_moy_reelle, heure_arr, calories)

    render_export(ph_export, points_gpx, resultats, ascensions, points_eau,
                  score, dist_tot, d_plus, d_moins, temps_s, date_depart,
                  heure_arr, vitesse, vit_moy_reelle, calories, df_profil,
                  ref_val, mode, poids, date_dep)

    tab_carte, tab_profil, tab_meteo, tab_cols, tab_detail, tab_analyse = st.tabs([
        "🗺️ Carte", "⛰️ Profil & Cols", "🌤️ Météo", "🏔️ Ascensions", "📋 Détail", "🤖 Coach IA"
    ])

    with tab_carte:
        render_map_view(points_gpx, resultats, ascensions, points_eau,
                        infos_soleil, date_depart, heure_arr)

    with tab_profil:
        render_profile_view(df_profil, ascensions, vitesse, ref_val, mode, poids)

    with tab_meteo:
        render_weather_view(resultats, analyse_meteo, uv_pollen, None)

    with tab_cols:
        render_climbs_view(ascensions, df_profil, vitesse, ref_val, ftp_fc, mode, poids,
                           ftp_w=ref_val if mode == "⚡ Puissance" else ftp_fc)

    with tab_detail:
        render_detail_view(resultats, intervalle)

    with tab_analyse:
        render_coach_view(gemini_key, dist_tot, d_plus, temps_s, calories, score,
                          ascensions, analyse_meteo, resultats, heure_dep, heure_arr,
                          vit_moy_reelle, infos_soleil, date_dep, points_eau, uv_pollen)


if __name__ == "__main__":
    main()
