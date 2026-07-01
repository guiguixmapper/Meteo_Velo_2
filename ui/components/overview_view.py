"""
ui/components/overview_view.py
==============================
Onglet Vue Globale — Soleil + Carte pleine largeur
"""

import streamlit as st
from streamlit_folium import st_folium
from ui.map_builder import creer_carte
from config.settings import FONDS_CARTE


def render_overview_view(points_gpx, resultats, ascensions, points_eau, infos_soleil,
                         score, dist_tot, d_plus, d_moins, temps_s, heure_arr, 
                         vit_moy_reelle, fuseau="UTC"):
    """Vue globale : Carte pleine largeur."""

    # ── CARTE PLEINE LARGEUR ──
    fond_choisi = st.selectbox("🖼️ Fond de carte", options=list(FONDS_CARTE.keys()), 
                               index=0, key="overview_fond", label_visibility="collapsed")
    tiles, attr = FONDS_CARTE[fond_choisi]

    cache_key = f"carte_{fond_choisi}_{id(points_gpx)}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = creer_carte(points_gpx, resultats, ascensions,
                                                   points_eau, tiles, attr)
    carte = st.session_state[cache_key]
    st_folium(carte, width="100%", height=700, returned_objects=[])
