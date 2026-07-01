"""
ui/components/overview_view.py
==============================
Onglet Vue Globale — Soleil + Carte pleine largeur
"""

import streamlit as st
from streamlit_folium import st_folium
from ui.map_builder import creer_carte
from config.settings import FONDS_CARTE
from pytz import timezone


def render_overview_view(points_gpx, resultats, ascensions, points_eau, infos_soleil,
                         score, dist_tot, d_plus, d_moins, temps_s, heure_arr, 
                         vit_moy_reelle, fuseau="UTC"):
    """Vue globale : Soleil + Carte pleine largeur."""
    
    # ── SOLEIL ──
    if infos_soleil:
        tz = timezone(fuseau)
        lever_local = infos_soleil["lever"].astimezone(tz)
        coucher_local = infos_soleil["coucher"].astimezone(tz)
        
        ls = lever_local.strftime("%H:%M")
        cs = coucher_local.strftime("%H:%M")
        ds = infos_soleil["coucher"] - infos_soleil["lever"]
        hj = int(ds.seconds // 3600)
        mj = int((ds.seconds % 3600) // 60)
        
        col1, col2, col3 = st.columns([2, 2, 1])
        with col3:
            st.markdown(f"""
            <div style="background:rgba(252,76,2,0.06);border:1px solid rgba(252,76,2,0.2);
                        border-radius:8px;padding:12px;text-align:center">
                <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;
                            opacity:0.6;margin-bottom:8px">☀️ Soleil</div>
                <div style="display:flex;flex-direction:column;gap:6px;font-size:0.9rem;font-weight:600">
                    <div>🌅 {ls}</div>
                    <div>🌇 {cs}</div>
                    <div style="font-size:0.75rem;opacity:0.6;margin-top:2px">{hj}h{mj:02d}m</div>
                </div>
            </div>""", unsafe_allow_html=True)
    
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
