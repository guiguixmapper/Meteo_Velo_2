"""
ui/components/detail_view.py
=============================
Onglet Détail — tableau météo horaire complet.
"""

import streamlit as st
import pandas as pd
from core.utils.geo import label_wind_chill


def render_detail_view(resultats, intervalle):
    st.caption(f"Un point toutes les **{intervalle} min**. Wind Chill si temp ≤ 10°C et vent > 4.8 km/h.")
    lignes = []
    for cp in resultats:
        t  = cp.get("temp_val")
        v  = cp.get("vent_val")
        rg = cp.get("rafales_val")
        lignes.append({
            "Heure":       cp["Heure"],
            "Km":          cp["Km"],
            "Alt (m)":     cp["Alt (m)"],
            "Ciel":        cp.get("Ciel", "—"),
            "Temp (°C)":   f"{t}°C" if t is not None else "—",
            "Ressenti":    label_wind_chill(cp.get("ressenti")),
            "Pluie":       cp.get("Pluie", "—"),
            "Vent (km/h)": f"{v} km/h" if v is not None else "—",
            "Rafales":     f"{rg} km/h" if rg is not None else "—",
            "Direction":   cp.get("Dir", "—"),
            "Effet vent":  cp.get("effet", "—"),
        })

    # Hauteur dynamique : 56px header + 35px par ligne, sans plafond arbitraire.
    # On laisse le tableau s'étendre jusqu'à 2000px max pour les longues sorties
    # (intervalle 5 min sur 200+ km = ~80 lignes = ~2856px sans plafond).
    # Au-delà de 2000px, Streamlit scrolle nativement dans le composant.
    hauteur = min(2000, 56 + 35 * len(lignes))

    st.dataframe(pd.DataFrame(lignes), width='stretch', hide_index=True, key="detail_df",
                 height=hauteur,
        column_config={
            "Heure":       st.column_config.TextColumn("🕐 Heure"),
            "Km":          st.column_config.NumberColumn("📏 Km"),
            "Alt (m)":     st.column_config.NumberColumn("⛰️ Alt"),
            "Ciel":        st.column_config.TextColumn("🌤️ Ciel"),
            "Temp (°C)":   st.column_config.TextColumn("🌡️ Temp"),
            "Ressenti":    st.column_config.TextColumn("🥶 Ressenti"),
            "Pluie":       st.column_config.TextColumn("🌧️ Pluie"),
            "Vent (km/h)": st.column_config.TextColumn("💨 Vent"),
            "Rafales":     st.column_config.TextColumn("🌬️ Rafales"),
            "Direction":   st.column_config.TextColumn("🧭 Direction"),
            "Effet vent":  st.column_config.TextColumn("🚴 Effet"),
        })
