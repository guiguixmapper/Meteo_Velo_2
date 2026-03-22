"""
ui/components/weather_view.py
==============================
Onglet Météo — graphiques + UV/pollen + répartition vent.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from core.utils.geo import label_wind_chill


def creer_figure_meteo(resultats):
    kms, temps, vents, rafales, pluies, cv, cp_ = [], [], [], [], [], [], []
    for r in resultats:
        t = r.get("temp_val"); v = r.get("vent_val")
        if t is None or v is None: continue
        kms.append(r["Km"]); temps.append(t); vents.append(v)
        rafales.append(r.get("rafales_val") or v)
        pluies.append(r.get("pluie_pct") or 0)
        cv.append("#ef4444" if v>=40 else "#f97316" if v>=25 else "#eab308" if v>=10 else "#22c55e")
        p = r.get("pluie_pct") or 0
        cp_.append("#1d4ed8" if p>=70 else "#2563eb" if p>=40 else "#60a5fa" if p>=20 else "#bfdbfe")

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.40, 0.33, 0.27], vertical_spacing=0.06,
        subplot_titles=["🌡️ Température (°C)", "💨 Vent moyen & Rafales (km/h)", "🌧️ Probabilité de pluie (%)"])

    if kms:
        ct = ["#8b5cf6" if t<5 else "#3b82f6" if t<15 else "#22c55e" if t<22
              else "#f97316" if t<30 else "#ef4444" for t in temps]
        fig.add_trace(go.Scatter(x=kms, y=temps, mode="lines+markers",
            line=dict(color="#f97316", width=2.5),
            marker=dict(color=ct, size=9, line=dict(color="white", width=1.5)),
            hovertemplate="<b>Km %{x}</b><br>Temp : %{y}°C<extra></extra>",
            name="Température"), row=1, col=1)
        fig.add_hrect(y0=15, y1=22, row=1, col=1, fillcolor="rgba(34,197,94,0.10)", line_width=0,
            annotation_text="Zone idéale (15–22°C)", annotation_font_size=9,
            annotation_font_color="#16a34a", annotation_position="top left")
        fig.add_trace(go.Bar(x=kms, y=vents, marker_color=cv, name="Vent moyen",
            hovertemplate="<b>Km %{x}</b><br>Vent : %{y} km/h<extra></extra>"), row=2, col=1)
        fig.add_trace(go.Scatter(x=kms, y=rafales, mode="lines+markers",
            line=dict(color="#475569", width=1.8, dash="dot"),
            marker=dict(size=5, color="#475569"), name="Rafales",
            hovertemplate="<b>Km %{x}</b><br>Rafales : %{y} km/h<extra></extra>"), row=2, col=1)
        fig.add_trace(go.Bar(x=kms, y=pluies, marker_color=cp_, name="Pluie",
            hovertemplate="<b>Km %{x}</b><br>Pluie : %{y}%<extra></extra>"), row=3, col=1)
        fig.add_hline(y=50, row=3, col=1, line_dash="dot", line_color="#64748b", line_width=1.5,
            annotation_text="Seuil 50%", annotation_font_size=9,
            annotation_font_color="#64748b", annotation_position="top right")

    fig.update_layout(height=620, margin=dict(l=55, r=20, t=45, b=40),
        hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
        showlegend=False, dragmode=False, font=dict(color="#1e293b"),
        annotationdefaults=dict(font=dict(color="#1e293b")))
    for ann in fig.layout.annotations:
        ann.font.color = "#1e293b"; ann.font.size = 13
    fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9", row=1, col=1, title_text="°C")
    fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9", row=2, col=1, title_text="km/h", rangemode="tozero")
    fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9", row=3, col=1, title_text="%", range=[0, 105])
    fig.update_xaxes(showgrid=True, gridcolor="#f1f5f9", title_text="Distance (km)", row=3, col=1)
    return fig


def render_weather_view(resultats, analyse_meteo, uv_pollen, err_meteo):
    if err_meteo:
        st.warning("⚠️ Données météo indisponibles.")
        return

    # UV & Pollen
    uv_col, poll_col = st.columns([1, 2])
    with uv_col:
        uv    = uv_pollen.get("uv_max")
        emoji = uv_pollen.get("uv_emoji", "—")
        label = uv_pollen.get("uv_label", "—")
        coul  = uv_pollen.get("uv_couleur", "#9ca3af")
        lbl_court = label.split("—")[1].strip() if "—" in label else label
        st.markdown(f"""
        <div style="border:1px solid rgba(128,128,128,0.18);border-radius:12px;
                    padding:14px 18px;background:rgba(128,128,128,0.04)">
          <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.5px;opacity:0.5;margin-bottom:6px">☀️ Indice UV max</div>
          <div style="font-size:2rem;font-weight:900;color:{coul};line-height:1">
            {uv if uv is not None else "—"}</div>
          <div style="font-size:0.8rem;color:{coul};font-weight:600;margin-top:4px">
            {emoji} {lbl_court}</div>
          {"<div style='font-size:0.75rem;opacity:0.55;margin-top:4px'>🧴 Crème solaire recommandée</div>" if uv and uv >= 3 else ""}
        </div>""", unsafe_allow_html=True)

    with poll_col:
        pollens = uv_pollen.get("pollens", [])
        st.markdown(f"""
        <div style="border:1px solid rgba(128,128,128,0.18);border-radius:12px;
                    padding:14px 18px;background:rgba(128,128,128,0.04);height:100%">
          <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.5px;opacity:0.5;margin-bottom:8px">🌿 Alertes Pollen</div>
          {"".join(f'<div style="font-size:0.83rem;font-weight:500;padding:3px 0">{p}</div>' for p in pollens)
            if pollens else
            '<div style="font-size:0.83rem;opacity:0.55">✅ Aucune alerte pollen significative</div>'}
        </div>""", unsafe_allow_html=True)

    st.divider()
    st.caption("Température · Vent & Rafales · Probabilité de pluie.")
    st.plotly_chart(creer_figure_meteo(resultats), width='stretch', key="weather_chart")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Température** — 🟣 <5° · 🔵 5–15° · 🟢 15–22° (idéal) · 🟠 22–30° · 🔴 >30°C")
    with c2:
        st.markdown("**Vent** — 🟢 <10 · 🟡 10–25 · 🟠 25–40 · 🔴 >40 km/h | **Pluie** — clair→foncé")

    if analyse_meteo:
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**💨 Répartition du vent**")
            def barre(pct, couleur, label, emoji):
                st.markdown(f"""
                <div style="margin-bottom:8px">
                  <div style="display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:3px">
                    <span>{emoji} {label}</span><span style="font-weight:700">{pct}%</span>
                  </div>
                  <div style="background:rgba(128,128,128,0.15);border-radius:4px;height:7px">
                    <div style="background:{couleur};width:{pct}%;height:7px;border-radius:4px"></div>
                  </div>
                </div>""", unsafe_allow_html=True)
            barre(analyse_meteo["pct_face"], "#ef4444", "Face",   "⬇️")
            barre(analyse_meteo["pct_cote"], "#eab308", "Côté",   "↔️")
            barre(analyse_meteo["pct_dos"],  "#22c55e", "Dos",    "⬆️")
            if analyse_meteo.get("segments_face"):
                st.caption("Segments avec vent de face :")
                for s in analyse_meteo["segments_face"]:
                    st.caption(f"· Km {s[0]} → {s[1]} ({round(s[1]-s[0],1)} km)")

        with c2:
            st.markdown("**🌧️ Risque de pluie**")
            pp = analyse_meteo["pct_pluie"]
            couleur_pp = "#ef4444" if pp > 60 else "#f97316" if pp > 30 else "#22c55e"
            st.markdown(f"""
            <div style="text-align:center;padding:16px;background:rgba(128,128,128,0.04);
                        border-radius:10px;margin-bottom:12px">
                <div style="font-size:2.5rem;font-weight:900;color:{couleur_pp}">{pp}%</div>
                <div style="font-size:.85rem;opacity:0.6">du parcours avec risque > 50%</div>
            </div>""", unsafe_allow_html=True)
            if analyse_meteo["premier_pluie"]:
                cp_p = analyse_meteo["premier_pluie"]
                st.markdown(f"""
                <div style="background:rgba(251,191,36,0.1);border-radius:8px;padding:10px 14px;font-size:.85rem">
                    🕐 Premier risque à <b>{cp_p['Heure']}</b> — Km {cp_p['Km']}<br>
                    Probabilité : <b>{cp_p.get('pluie_pct','?')}%</b>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background:rgba(34,197,94,0.1);border-radius:8px;padding:10px 14px;font-size:.85rem">
                    ✅ Aucun risque de pluie significatif sur le parcours
                </div>""", unsafe_allow_html=True)
