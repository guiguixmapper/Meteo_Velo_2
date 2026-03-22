"""
ui/components/profile_view.py
==============================
Onglet Profil & Cols — profil altimétrique + profil détaillé par montée.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from config.settings import COULEURS_CAT, LEGENDE_UCI
from core.services.climbing_service import (
    estimer_watts, estimer_fc, get_zone, zones_actives,
)


def creer_figure_profil(df, ascensions, vitesse, ref_val, mode, poids, idx_survol=None):
    fig   = go.Figure()
    dists = df["Distance (km)"].tolist()
    alts  = df["Altitude (m)"].tolist()

    fig.add_trace(go.Scatter(
        x=dists, y=alts, fill="tozeroy",
        fillcolor="rgba(148,163,184,0.10)",
        line=dict(color="rgba(148,163,184,0.5)", width=1.5),
        hovertemplate="<b>Km %{x:.1f}</b><br>Altitude : %{y:.0f} m<extra></extra>",
        name="Profil", showlegend=False))

    for i, asc in enumerate(ascensions):
        d0, d1 = asc["_debut_km"], asc["_sommet_km"]
        cat    = asc["Catégorie"]
        nom    = asc.get("Nom", "—")
        coul   = COULEURS_CAT.get(cat, "#94a3b8")
        op     = 1.0 if idx_survol is None or idx_survol == i else 0.15
        sx     = [d for d in dists if d0 <= d <= d1]
        sy     = [alts[j] for j, d in enumerate(dists) if d0 <= d <= d1]
        if not sx:
            continue
        w = estimer_watts(asc["_pente_moy"], vitesse, poids)
        hover_extra = (f"FC est. : {estimer_fc(w, ref_val, ref_val)}bpm"
                       if mode == "🫀 FC"
                       else f"Puissance est. : {w} W ({round(w/ref_val*100) if ref_val>0 else '?'}% FTP)")
        r, g, b = int(coul[1:3], 16), int(coul[3:5], 16), int(coul[5:7], 16)
        fig.add_trace(go.Scatter(
            x=sx, y=sy, fill="tozeroy",
            fillcolor=f"rgba({r},{g},{b},{round(op*0.30,2)})",
            line=dict(color=coul, width=3 if idx_survol == i else 2.5), opacity=op,
            hovertemplate=(f"<b>{cat}{' — '+nom if nom!='—' else ''}</b>"
                           f"<br>Km %{{x:.1f}}<br>Alt : %{{y:.0f}} m<br>{hover_extra}<extra></extra>"),
            name=nom if nom != "—" else cat, showlegend=True, legendgroup=cat))
        fig.add_annotation(
            x=d1, y=sy[-1] if sy else 0,
            text=f"▲ {nom if nom != '—' else cat.split()[0]}",
            showarrow=True, arrowhead=2, arrowsize=.8,
            arrowcolor=coul, font=dict(size=10, color=coul),
            bgcolor="rgba(255,255,255,0.85)", bordercolor=coul, borderwidth=1, opacity=op)

    fig.update_layout(
        height=480, margin=dict(l=50, r=20, t=20, b=10),
        xaxis=dict(title="Distance (km)", showgrid=True, gridcolor="#e2e8f0",
                   title_font=dict(color="#1e293b"), tickfont=dict(color="#1e293b")),
        yaxis=dict(title="Altitude (m)", showgrid=True, gridcolor="#e2e8f0",
                   title_font=dict(color="#1e293b"), tickfont=dict(color="#1e293b")),
        showlegend=False,
        hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
        font=dict(color="#1e293b"))
    return fig


def creer_figure_col(df_profil, asc, nb_segments=None):
    d0, d1 = asc["_debut_km"], asc["_sommet_km"]
    dk     = d1 - d0
    mask      = [d0 <= d <= d1 for d in df_profil["Distance (km)"]]
    dists_col = [d for d, m in zip(df_profil["Distance (km)"], mask) if m]
    alts_col  = [a for a, m in zip(df_profil["Altitude (m)"], mask) if m]
    if len(dists_col) < 2:
        return None

    seg_km = dk / nb_segments if nb_segments else (0.5 if dk < 5 else 1.0 if dk < 15 else 2.0)

    def couleur_pente(p):
        if p < 3:    return "#22c55e"
        elif p < 6:  return "#84cc16"
        elif p < 8:  return "#eab308"
        elif p < 10: return "#f97316"
        elif p < 12: return "#ef4444"
        else:        return "#7f1d1d"

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dists_col, y=alts_col, fill="tozeroy",
        fillcolor="rgba(203,213,225,0.2)", line=dict(color="#94a3b8", width=1),
        hoverinfo="skip", showlegend=False))

    km_d = dists_col[0]
    while km_d < dists_col[-1] - 0.05:
        km_f = min(km_d + seg_km, dists_col[-1])
        sx   = [d for d in dists_col if km_d <= d <= km_f]
        sy   = [alts_col[j] for j, d in enumerate(dists_col) if km_d <= d <= km_f]
        if len(sx) >= 2:
            dist_m = (sx[-1] - sx[0]) * 1000
            pente  = (max(0, sy[-1] - sy[0]) / dist_m * 100) if dist_m > 0 else 0
            coul   = couleur_pente(pente)
            r, g, b = int(coul[1:3], 16), int(coul[3:5], 16), int(coul[5:7], 16)
            fig.add_trace(go.Scatter(
                x=sx, y=sy, fill="tozeroy", fillcolor=f"rgba({r},{g},{b},0.4)",
                line=dict(color=coul, width=3),
                hovertemplate=f"<b>{round(pente,1)}%</b><br>Km %{{x:.1f}}<br>Alt : %{{y:.0f}} m<extra></extra>",
                showlegend=False))
            if dist_m > 300:
                fig.add_annotation(
                    x=(sx[0]+sx[-1])/2, y=sy[len(sy)//2],
                    text=f"<b>{round(pente,1)}%</b>", showarrow=False,
                    font=dict(size=10, color=coul), bgcolor="rgba(255,255,255,0.8)",
                    bordercolor=coul, borderwidth=1, yshift=12)
        km_d = km_f

    fig.add_trace(go.Scatter(x=dists_col, y=alts_col, mode="lines",
        line=dict(color="#1e293b", width=2),
        hovertemplate="Km %{x:.1f} — Alt : %{y:.0f} m<extra></extra>",
        showlegend=False))

    nom   = asc.get("Nom", "—")
    titre = (f"{nom+' — ' if nom != '—' else ''}{asc['Catégorie']} — "
             f"{asc['Longueur']} · {asc['Dénivelé']} · {asc['Pente moy.']} moy. · {asc['Pente max']} max")
    fig.update_layout(
        height=380, margin=dict(l=50, r=20, t=40, b=40),
        xaxis=dict(title="Distance (km)", showgrid=True, gridcolor="#f1f5f9",
                   title_font=dict(color="#1e293b"), tickfont=dict(color="#1e293b")),
        yaxis=dict(title="Altitude (m)", showgrid=True, gridcolor="#f1f5f9",
                   title_font=dict(color="#1e293b"), tickfont=dict(color="#1e293b")),
        plot_bgcolor="white", paper_bgcolor="white", font=dict(color="#1e293b"),
        hovermode="x unified",
        title=dict(text=titre, font=dict(size=13, color="#1e293b"), x=0))
    return fig


def render_profile_view(df_profil, ascensions, vitesse, ref_val, mode, poids):
    lbl_mode = "FTP" if mode == "⚡ Puissance" else "FC max"
    st.caption(f"Segments colorés selon la catégorie UCI des ascensions.")

    idx_survol = None
    if ascensions:
        noms_liste = ["(toutes les côtes)"] + [
            f"{a.get('Nom','') + ' — ' if a.get('Nom','—') != '—' else ''}"
            f"{a['Catégorie']} — Km {a['Départ (km)']}→{a['Sommet (km)']} ({a['Longueur']})"
            for a in ascensions]
        choix = st.selectbox("🔍 Mettre en avant :", options=noms_liste, index=0, key="profile_highlight")
        if choix != "(toutes les côtes)":
            idx_survol = noms_liste.index(choix) - 1

    if not df_profil.empty:
        st.plotly_chart(
            creer_figure_profil(df_profil, ascensions, vitesse, ref_val, mode, poids, idx_survol),
            width='stretch', key="profile_main_chart")

    # Légende catégories UCI
    cats_presentes = list({asc["Catégorie"]: COULEURS_CAT.get(asc["Catégorie"], "#94a3b8")
                           for asc in ascensions}.items()) if ascensions else []
    if cats_presentes:
        legende = " &nbsp;·&nbsp; ".join(
            f'<span style="display:inline-flex;align-items:center;gap:4px">'
            f'<span style="width:10px;height:10px;border-radius:2px;background:{coul};display:inline-block"></span>'
            f'<span style="font-size:0.72rem;font-weight:500">{cat}</span></span>'
            for cat, coul in cats_presentes)
        st.markdown(f'<div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:8px;opacity:0.8">{legende}</div>',
                    unsafe_allow_html=True)

    # Profil détaillé d'une montée
    if ascensions:
        st.divider()
        st.subheader("🔍 Profil détaillé d'une montée")
        noms_cols = [
            f"{a.get('Nom','') + ' — ' if a.get('Nom','—') != '—' else ''}"
            f"{a['Catégorie']} — Km {a['Départ (km)']}→{a['Sommet (km)']} ({a['Longueur']}, {a['Dénivelé']})"
            for a in ascensions]
        col_choix = st.selectbox("Choisir une montée :", options=noms_cols, index=0, key="profile_selectbox")
        asc_sel   = ascensions[noms_cols.index(col_choix)]
        dk_sel    = asc_sel["_sommet_km"] - asc_sel["_debut_km"]
        seg_defaut = 0.5 if dk_sel < 5 else 1.0 if dk_sel < 15 else 2.0
        col_ctrl1, col_ctrl2 = st.columns([3, 1])
        with col_ctrl1:
            seg_km = st.slider("Longueur des segments (km)", 0.25,
                               min(5.0, dk_sel / 2), float(seg_defaut), 0.25, key="profile_slider")
        with col_ctrl2:
            st.metric("Segments", max(2, int(dk_sel / seg_km)))
        if not df_profil.empty:
            fig_col = creer_figure_col(df_profil, asc_sel, nb_segments=max(2, int(dk_sel / seg_km)))
            if fig_col:
                st.plotly_chart(fig_col, width='stretch', key="profile_col_chart")
            st.markdown("**Intensité de pente :** 🟢 <3% · 🟡 3–6% · 🟠 6–8% · 🔴 8–12% · 🟤 >12%")
