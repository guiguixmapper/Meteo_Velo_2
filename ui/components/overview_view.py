"""
ui/components/overview_view.py
==============================
Onglet Vue Globale — Infos essentielles en haut + Carte pleine largeur
"""

import streamlit as st
from streamlit_folium import st_folium
from ui.map_builder import creer_carte
from config.settings import FONDS_CARTE
from pytz import timezone


def render_overview_view(points_gpx, resultats, ascensions, points_eau, infos_soleil,
                         score, dist_tot, d_plus, d_moins, temps_s, heure_arr, 
                         vit_moy_reelle, fuseau="UTC"):
    """Vue globale : Infos essentielles en haut + Carte pleine largeur."""
    
    # ── SCORE + MÉTRIQUES CLÉS ──
    col_score, col_metrics, col_soleil = st.columns([1, 2, 1])
    
    with col_score:
        score_total = score["total"]
        score_label = score["label"]
        score_color = ("#22c55e" if score_total >= 7.0 else 
                      "#eab308" if score_total >= 5.0 else "#ef4444")
        
        st.markdown(f"""
        <div style="background:rgba(252,76,2,0.08);border-left:4px solid #FC4C02;
                    padding:14px;border-radius:8px;height:100%;display:flex;flex-direction:column;justify-content:center">
            <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;
                        opacity:0.6;margin-bottom:6px">Score</div>
            <div style="font-size:2.5rem;font-weight:900;color:{score_color};line-height:1">
                {score_total}/10</div>
            <div style="font-size:0.8rem;color:{score_color};font-weight:600;margin-top:4px">
                {score_label}</div>
        </div>""", unsafe_allow_html=True)
    
    with col_metrics:
        metrics = [
            ("📏 Distance", f"{dist_tot/1000:.1f} km"),
            ("⬆️ D+", f"{d_plus:.0f} m"),
            ("⬇️ D−", f"{d_moins:.0f} m"),
            ("⏱️ Durée", f"{int(temps_s//3600)}h{int((temps_s%3600)//60)}m"),
            ("🚴 Vitesse moy.", f"{vit_moy_reelle} km/h"),
        ]
        
        metrics_html = "".join([
            f"""<div style="display:flex;justify-content:space-between;padding:6px 0;
                           font-size:0.85rem;border-bottom:1px solid #f1f5f9">
                <span>{label}</span>
                <span style="font-weight:700">{value}</span>
            </div>"""
            for label, value in metrics
        ])
        
        st.markdown(f"""
        <div style="padding:14px;border:1px solid #f1f5f9;border-radius:8px;height:100%">
            {metrics_html}
        </div>""", unsafe_allow_html=True)
    
    with col_soleil:
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
                        border-radius:8px;padding:14px;height:100%;display:flex;flex-direction:column;justify-content:center;text-align:center">
                <div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;
                            opacity:0.6;margin-bottom:10px">☀️ Soleil</div>
                <div style="display:flex;flex-direction:column;gap:8px;font-size:0.85rem;font-weight:600">
                    <div>🌅 {ls}</div>
                    <div>🌇 {cs}</div>
                    <div style="font-size:0.7rem;opacity:0.6;margin-top:2px">{hj}h{mj:02d}m</div>
                </div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#f1f5f9;border-radius:8px;padding:14px;height:100%;
                        display:flex;align-items:center;justify-content:center;font-size:0.8rem;opacity:0.6">
                ⏳ Soleil indisponible
            </div>""", unsafe_allow_html=True)
    
    st.divider()
    
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
