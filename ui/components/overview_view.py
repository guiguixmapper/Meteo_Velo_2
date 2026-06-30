"""
ui/components/overview_view.py
==============================
Onglet Vue Globale — Carte + Infos essentielles + Levé/coucher soleil
"""

import streamlit as st
from streamlit_folium import st_folium
from ui.map_builder import creer_carte
from config.settings import FONDS_CARTE
from pytz import timezone


def render_overview_view(points_gpx, resultats, ascensions, points_eau, infos_soleil,
                         score, dist_tot, d_plus, d_moins, temps_s, heure_arr, 
                         vit_moy_reelle, fuseau="UTC"):
    """Vue globale : Carte + Infos clés + Soleil."""
    
    col_map, col_info = st.columns([2.5, 1])
    
    # ── CARTE ──
    with col_map:
        fond_choisi = st.selectbox("🖼️ Fond de carte", options=list(FONDS_CARTE.keys()), 
                                   index=0, key="overview_fond", label_visibility="collapsed")
        tiles, attr = FONDS_CARTE[fond_choisi]

        cache_key = f"carte_{fond_choisi}_{id(points_gpx)}"
        if cache_key not in st.session_state:
            st.session_state[cache_key] = creer_carte(points_gpx, resultats, ascensions,
                                                       points_eau, tiles, attr)
        carte = st.session_state[cache_key]
        st_folium(carte, width="100%", height=600, returned_objects=[])
    
    # ── INFOS LATÉRALES ──
    with col_info:
        st.markdown("### 📊 Résumé")
        
        # Score
        score_total = score["total"]
        score_label = score["label"]
        score_color = ("#22c55e" if score_total >= 7.0 else 
                      "#eab308" if score_total >= 5.0 else "#ef4444")
        
        st.markdown(f"""
        <div style="background:rgba(252,76,2,0.08);border-left:4px solid #FC4C02;
                    padding:12px;border-radius:8px;margin-bottom:12px">
            <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;
                        opacity:0.6;margin-bottom:4px">Score de Roulabilité</div>
            <div style="font-size:2rem;font-weight:900;color:{score_color}">{score_total}/10</div>
            <div style="font-size:0.75rem;color:{score_color};font-weight:600;margin-top:2px">
                {score_label}</div>
        </div>""", unsafe_allow_html=True)
        
        # Métriques essentielles
        metrics = [
            ("📏 Distance", f"{dist_tot/1000:.1f} km"),
            ("⬆️ D+", f"{d_plus:.0f} m"),
            ("⬇️ D−", f"{d_moins:.0f} m"),
            ("⏱️ Durée", f"{int(temps_s//3600)}h{int((temps_s%3600)//60)}m"),
            ("🚴 Vit. moy.", f"{vit_moy_reelle} km/h"),
        ]
        
        for label, value in metrics:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;
                        font-size:0.85rem;padding:6px 0;border-bottom:1px solid #f1f5f9">
                <span>{label}</span>
                <span style="font-weight:700">{value}</span>
            </div>""", unsafe_allow_html=True)
        
        st.divider()
        
        # Soleil
        if infos_soleil:
            tz = timezone(fuseau)
            lever_local = infos_soleil["lever"].astimezone(tz)
            coucher_local = infos_soleil["coucher"].astimezone(tz)
            
            ls = lever_local.strftime("%H:%M")
            cs = coucher_local.strftime("%H:%M")
            ds = infos_soleil["coucher"] - infos_soleil["lever"]
            hj = int(ds.seconds // 3600)
            mj = int((ds.seconds % 3600) // 60)
            
            st.markdown(f"""
            <div style="background:rgba(252,76,2,0.06);border:1px solid rgba(252,76,2,0.2);
                        border-radius:10px;padding:10px;text-align:center">
                <div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;
                            opacity:0.6;margin-bottom:6px">☀️ Soleil</div>
                <div style="display:flex;justify-content:space-around;font-size:0.8rem;
                            font-weight:600;gap:4px">
                    <div>🌅 {ls}</div>
                    <div>🌇 {cs}</div>
                </div>
                <div style="font-size:0.7rem;opacity:0.6;margin-top:4px">{hj}h{mj:02d}m</div>
            </div>""", unsafe_allow_html=True)
