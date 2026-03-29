"""
ui/components/metrics_banner.py
================================
Bannière score + métriques — colonnes Streamlit natives.
"""

import streamlit as st


def render_metrics_banner(score: dict, dist_tot: float, d_plus: float, d_moins: float,
                           temps_s: float, vit_moy_reelle: float,
                           heure_arr, calories: int):
    dh = int(temps_s // 3600)
    dm = int((temps_s % 3600) // 60)

    cols = st.columns([1.6, 1, 1, 1, 1, 1, 1, 1])

    # ── Bloc score orange ─────────────────────────────────────────────────────
    with cols[0]:
        st.markdown(
            f'<div style="background:#FC4C02;border-radius:10px;padding:6px 10px;'
            f'text-align:center;margin-top:2px">'
            f'<div style="color:white;font-size:1.5rem;font-weight:900;line-height:1;'
            f'letter-spacing:-1px">{score["total"]}'
            f'<span style="font-size:0.75rem;opacity:0.85">/10</span></div>'
            f'<div style="color:white;font-size:0.55rem;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.4px;margin-top:1px">'
            f'{score["label"]}</div>'
            f'<div style="display:flex;gap:3px;margin-top:3px;justify-content:center">'
            f'<span style="background:rgba(255,255,255,0.22);border-radius:8px;'
            f'padding:1px 5px;font-size:0.55rem;color:white;font-weight:600">'
            f'🌤️ {score["score_meteo"]}/6</span>'
            f'<span style="background:rgba(255,255,255,0.22);border-radius:8px;'
            f'padding:1px 5px;font-size:0.55rem;color:white;font-weight:600">'
            f'🏔️ {score["score_cols"]}/4</span>'
            f'</div></div>',
            unsafe_allow_html=True)

    # ── Cellules métriques ────────────────────────────────────────────────────
    metrics = [
        (round(dist_tot / 1000, 1), "km",      False),
        (int(d_plus),               "D+ m",    False),
        (int(d_moins),              "D− m",    False),
        (f"{dh}h{dm:02d}",          "durée",   False),
        (vit_moy_reelle,            "km/h",    True),   # orange
        (heure_arr.strftime('%H:%M'), "arr.",   False),
        (calories,                  "kcal",    False),
    ]

    for i, (val, unit, orange) in enumerate(metrics):
        color = "#FC4C02" if orange else "inherit"
        with cols[i + 1]:
            st.markdown(
                f'<div style="text-align:center;padding:2px 0">'
                f'<div style="font-size:1.1rem;font-weight:900;letter-spacing:-0.3px;'
                f'line-height:1;color:{color}">{val}</div>'
                f'<div style="font-size:0.58rem;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.3px;opacity:0.45;margin-top:2px">{unit}</div>'
                f'</div>',
                unsafe_allow_html=True)
