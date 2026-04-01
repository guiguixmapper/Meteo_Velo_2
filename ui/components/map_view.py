"""
ui/components/map_view.py
==========================
Onglet Carte.
"""

import streamlit as st
from streamlit_folium import st_folium
from ui.map_builder import creer_carte
from config.settings import FONDS_CARTE


def render_map_view(points_gpx, resultats, ascensions, points_eau, infos_soleil,
                    date_depart, heure_arr):
    # Soleil
    if infos_soleil:
        ls = infos_soleil["lever"].strftime("%H:%M")
        cs = infos_soleil["coucher"].strftime("%H:%M")
        ds = infos_soleil["coucher"] - infos_soleil["lever"]
        hj, mj = int(ds.seconds // 3600), int((ds.seconds % 3600) // 60)
        st.markdown(f"""
        <div class="soleil-row">
          <span style="font-size:1.3rem">☀️</span>
          <div class="soleil-item"><div class="s-val">🌅 {ls}</div><div class="s-lbl">Lever (UTC)</div></div>
          <div class="soleil-item"><div class="s-val">🌇 {cs}</div><div class="s-lbl">Coucher (UTC)</div></div>
          <div class="soleil-item"><div class="s-val">{hj}h{mj:02d}m</div><div class="s-lbl">Durée du jour</div></div>
        </div>""", unsafe_allow_html=True)
        tz = infos_soleil["lever"].tzinfo
        if date_depart.replace(tzinfo=tz) < infos_soleil["lever"]:
            st.warning(f"⚠️ Départ avant le lever du soleil ({ls} UTC) — prévoyez un éclairage.")
        if heure_arr.replace(tzinfo=tz) > infos_soleil["coucher"]:
            st.warning(f"⚠️ Arrivée après le coucher ({cs} UTC) — prévoyez un éclairage.")

    # Fond de carte
    fond_choisi = st.selectbox("🖼️ Fond de carte", options=list(FONDS_CARTE.keys()), index=0, key="map_fond")
    tiles, attr = FONDS_CARTE[fond_choisi]

    # Cache carte dans session_state
    cache_key = f"carte_{fond_choisi}_{id(points_gpx)}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = creer_carte(points_gpx, resultats, ascensions,
                                                   points_eau, tiles, attr)
    carte = st.session_state[cache_key]
    st_folium(carte, width="100%", height=700, returned_objects=[])
