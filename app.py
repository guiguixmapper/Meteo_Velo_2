"""
app.py — Point d'entrée de l'application
==========================================
Vélo & Météo — Analyse de tracé GPX.
Interface Streamlit optimisée avec 4 onglets thématiques.
"""

import streamlit as st
import logging
import pandas as pd
from datetime import datetime

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports architecture
from ui.styles.theme import CSS
from ui.components.sidebar import render_sidebar, render_export
from ui.components.metrics_banner import render_metrics_banner
from ui.components.overview_view import render_overview_view
from ui.components.weather_view import render_weather_view
from ui.components.profile_climbs_view import render_profile_climbs_view
from ui.components.coach_view import render_coach_view

from core.data_processor import DataProcessor, AppConfig, ProcessedData
from core.services.climbing_service import estimer_temps_col


def setup_page():
    """Configure la page Streamlit."""
    st.set_page_config(
        page_title="Vélo & Météo",
        page_icon="🚴‍♂️",
        layout="wide"
    )
    st.markdown(CSS, unsafe_allow_html=True)


def show_welcome_screen():
    """Affiche l'écran de bienvenue."""
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;color:#9ca3af">
      <div style="font-size:3rem;margin-bottom:12px">🗺️</div>
      <div style="font-size:1rem;font-weight:600;color:#374151;margin-bottom:6px">Importez un fichier GPX</div>
      <div style="font-size:0.83rem">Déposez votre trace dans le panneau de gauche pour démarrer l'analyse.</div>
    </div>""", unsafe_allow_html=True)


def enrich_climbs_timing(climbs: list, vitesse_kmh: float, date_depart: datetime) -> None:
    """
    Enrichit les ascensions avec temps et heure d'arrivée au sommet.
    Modifie les ascensions in-place.
    """
    from datetime import timedelta
    
    for climb in climbs:
        # Temps depuis le départ jusqu'au début de l'ascension
        temps_debut_s = (climb["_debut_km"] / vitesse_kmh) * 3600
        
        # Durée de l'ascension
        longueur_km = climb["_sommet_km"] - climb["_debut_km"]
        mins_col, vit_col = estimer_temps_col(
            longueur_km,
            climb["_pente_moy"],
            vitesse_kmh
        )
        
        # Heure d'arrivée au sommet
        heure_sommet = date_depart + timedelta(seconds=temps_debut_s) + \
                      timedelta(minutes=mins_col)
        
        climb["Temps col"] = f"{mins_col} min ({vit_col} km/h)"
        climb["Arrivée sommet"] = heure_sommet.strftime("%H:%M")


def render_tabs(data: ProcessedData) -> None:
    """Affiche les 4 onglets de contenu."""
    tab1, tab2, tab3, tab4 = st.tabs([
        "🗺️ Aperçu Global",
        "🌤️ Météo",
        "📊 Profil & Ascensions",
        "🤖 Coach IA"
    ])
    
    with tab1:
        render_overview_view(
            data.points_gpx,
            data.weather_results,
            data.climbs,
            data.water_points,
            data.sunrise_sunset,
            data.rideability_score,
            data.distance_total_m,
            data.d_plus,
            data.d_moins,
            data.temps_total_s,
            data.heure_arrivee,
            data.avg_speed_kmh,
            data.timezone
        )
    
    with tab2:
        render_weather_view(
            data.weather_results,
            data.weather_analysis,
            data.uv_pollen,
            data.error_weather
        )
    
    with tab3:
        render_profile_climbs_view(
            # Créer DataFrame si nécessaire
            pd.DataFrame(data.profil_data) if data.profil_data else None,
            data.climbs,
            st.session_state.get("vitesse", 0),
            st.session_state.get("ref_val"),
            st.session_state.get("ftp_fc"),
            st.session_state.get("mode", "⚡ Puissance"),
            st.session_state.get("poids", 75),
            ftp_w=st.session_state.get("ref_val") if st.session_state.get("mode") == "⚡ Puissance" else None
        )
    
    with tab4:
        render_coach_view(
            st.session_state.get("gemini_key"),
            data.distance_total_m,
            data.d_plus,
            data.temps_total_s,
            data.calories,
            data.rideability_score,
            data.climbs,
            data.weather_analysis,
            data.weather_results,
            st.session_state.get("heure_dep"),
            data.heure_arrivee,
            data.avg_speed_kmh,
            data.sunrise_sunset,
            data.date_depart.date(),
            data.water_points,
            data.uv_pollen
        )


def main():
    """Point d'entrée principal de l'application."""
    setup_page()
    
    # Sidebar pour paramètres utilisateur
    sidebar_params = render_sidebar()
    
    # Vérifier si fichier est disponible
    if sidebar_params["fichier"] is None:
        show_welcome_screen()
        return
    
    # Afficher espacement
    st.markdown('<div style="height: 1.5rem;"></div>', unsafe_allow_html=True)
    
    # Préparer configuration de l'application
    progress_container = st.empty()
    app_config = AppConfig(
        fichier=sidebar_params["fichier"].read() if sidebar_params["fichier"] else None,
        date_dep=sidebar_params["date_dep"],
        heure_dep=sidebar_params["heure_dep"],
        vitesse_kmh=sidebar_params["vitesse"],
        intervalle_sec=sidebar_params["intervalle_sec"],
        poids_kg=sidebar_params["poids"],
        ref_val=sidebar_params["ref_val"],
        mode=sidebar_params["mode"],
        ftp_fc=sidebar_params["ftp_fc"],
        noms_osm=sidebar_params["noms_osm"],
        gemini_key=sidebar_params["gemini_key"],
        placeholder_fuseau=sidebar_params["ph_fuseau"],
        placeholder_export=sidebar_params["ph_export"],
    )
    
    # Sauvegarder en session pour utilisation ultérieure
    st.session_state["vitesse"] = app_config.vitesse_kmh
    st.session_state["ref_val"] = app_config.ref_val
    st.session_state["ftp_fc"] = app_config.ftp_fc
    st.session_state["mode"] = app_config.mode
    st.session_state["poids"] = app_config.poids_kg
    st.session_state["gemini_key"] = app_config.gemini_key
    st.session_state["heure_dep"] = app_config.heure_dep
    
    # Traiter les données
    processor = DataProcessor(app_config)
    data = processor.process(progress_container)
    
    if data is None:
        # L'erreur détaillée est affichée par processor.process()
        return
    
    # Effacer container de progression
    progress_container.empty()
    
    # Enrichir ascensions avec timing
    enrich_climbs_timing(data.climbs, app_config.vitesse_kmh, data.date_depart)
    
    # Afficher banneau métriques
    render_metrics_banner(
        data.rideability_score,
        data.distance_total_m,
        data.d_plus,
        data.d_moins,
        data.temps_total_s,
        data.avg_speed_kmh,
        data.heure_arrivee,
        data.calories,
        data.sunrise_sunset,
        data.timezone
    )
    
    # Afficher export dans sidebar
    render_export(
        sidebar_params["ph_export"],
        data.points_gpx,
        data.weather_results,
        data.climbs,
        data.water_points,
        data.rideability_score,
        data.distance_total_m,
        data.d_plus,
        data.d_moins,
        data.temps_total_s,
        data.date_depart,
        data.heure_arrivee,
        app_config.vitesse_kmh,
        data.avg_speed_kmh,
        data.calories,
        pd.DataFrame(data.profil_data) if data.profil_data else None,
        app_config.ref_val,
        app_config.mode,
        app_config.poids_kg,
        app_config.date_dep,
    )
    
    # Afficher contenu en onglets
    render_tabs(data)


if __name__ == "__main__":
    main()
