"""
ui/components/profile_climbs_view.py
====================================
Onglet Profil & Ascensions (FUSIONNÉ) — pas de doublons
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config.settings import COULEURS_CAT, LEGENDE_UCI
from core.services.climbing_service import (
    estimer_watts, estimer_fc, get_zone, zones_actives,
    estimer_temps_col_vam, niveau_cycliste, calculer_vam,
)
from ui.components.profile_view import creer_figure_col


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
        height=420, margin=dict(l=50, r=20, t=20, b=10),
        xaxis=dict(title="Distance (km)", showgrid=True, gridcolor="#e2e8f0",
                   title_font=dict(color="#1e293b"), tickfont=dict(color="#1e293b")),
        yaxis=dict(title="Altitude (m)", showgrid=True, gridcolor="#e2e8f0",
                   title_font=dict(color="#1e293b"), tickfont=dict(color="#1e293b")),
        showlegend=False,
        hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white",
        font=dict(color="#1e293b"))
    return fig


def render_profile_climbs_view(df_profil, ascensions, vitesse, ref_val, ftp_fc, mode, poids, ftp_w=None):
    """Vue fusionnée Profil + Ascensions — pas de répétition."""
    
    if not ascensions:
        st.info("🚴 Aucune ascension catégorisée — parcours roulant !")
        return

    # ── PROFIL ALTIMÉTRIQUE ──
    st.markdown("### 📈 Profil altimétrique")
    
    idx_survol = None
    if ascensions:
        noms_liste = ["(Vue complète)"] + [
            f"{a.get('Nom','') + ' — ' if a.get('Nom','—') != '—' else ''}"
            f"{a['Catégorie']} · Km {a['Départ (km)']}→{a['Sommet (km)']}"
            for a in ascensions]
        choix = st.selectbox("Mettre en avant :", options=noms_liste, index=0, 
                            key="profile_highlight", label_visibility="collapsed")
        if choix != "(Vue complète)":
            idx_survol = noms_liste.index(choix) - 1

    if not df_profil.empty:
        st.plotly_chart(
            creer_figure_profil(df_profil, ascensions, vitesse, ref_val, mode, poids, idx_survol),
            width="stretch", key="profile_main_chart")

    # ── TABLEAU ASCENSIONS (COMPACT) ──
    st.markdown("### 🏔️ Ascensions")
    
    # Calcul VAM
    _ftp = ftp_w if ftp_w and ftp_w > 0 else (ref_val if mode == "⚡ Puissance" else ftp_fc)
    _vam = calculer_vam(_ftp, poids)
    _niveau = niveau_cycliste(_vam)

    for a in ascensions:
        w       = estimer_watts(a["_pente_moy"], vitesse, poids)
        _, zlbl, _ = get_zone(w, ref_val, zones_actives(mode))
        pct     = round(w / ref_val * 100) if ref_val > 0 else 0
        fc_est  = estimer_fc(w, ftp_fc, ref_val)
        a["Puissance"]  = f"{w} W"
        a["Effort val"] = (f"{pct}% FTP" if mode == "⚡ Puissance"
                           else f"~{fc_est} bpm" if fc_est else "—")
        a["Zone"]   = zlbl
        a["Effort"] = ("🔴 Max"       if pct > 105 else "🟠 Très dur"  if pct > 95
                       else "🟡 Difficile" if pct > 80  else "🟢 Modéré"    if pct > 60
                       else "🔵 Endurance")
        # Temps VAM réaliste
        dk_m = (a["_sommet_km"] - a["_debut_km"]) * 1000
        dp_m = float(a["Dénivelé"].replace(" m", ""))
        vam_res = estimer_temps_col_vam(dp_m, dk_m / 1000, _ftp, poids)
        a["Temps VAM"]     = f"{vam_res['mins']} min"
        a["VAM (m/h)"]     = vam_res["vam"]

    cols_aff = ["Catégorie", "Nom", "Longueur", "Dénivelé", "Pente moy.",
                "Alt. sommet", "Temps VAM", "Arrivée sommet", "Effort"]
    df_asc = pd.DataFrame(ascensions)
    if "Nom" not in df_asc.columns:
        df_asc["Nom"] = "—"

    st.dataframe(df_asc[cols_aff], width="stretch", hide_index=True, key="climbs_df",
        column_config={
            "Nom":            st.column_config.TextColumn("🏔️ Nom"),
            "Temps VAM":      st.column_config.TextColumn("⏱️ Temps"),
            "Arrivée sommet": st.column_config.TextColumn("🏁 Arrivée"),
            "Effort":         st.column_config.TextColumn("Effort"),
        })

    st.caption(f"📈 VAM {int(_vam)} m/h — {_niveau} (FTP {int(_ftp)}W / {round(_ftp/poids,1)} W/kg)")

    # ── PROFIL DÉTAILLÉ D'UNE MONTÉE ──
    st.divider()
    st.markdown("### 🔍 Profil détaillé")
    
    noms_cols = [
        f"{a.get('Nom','') + ' — ' if a.get('Nom','—') != '—' else ''}"
        f"{a['Catégorie']} · Km {a['Départ (km)']}→{a['Sommet (km)']} ({a['Longueur']}, {a['Dénivelé']})"
        for a in ascensions]
    col_choix = st.selectbox("Choisir une montée :", options=noms_cols, index=0, 
                            key="climbs_selectbox", label_visibility="collapsed")
    asc_sel   = ascensions[noms_cols.index(col_choix)]
    dk_sel    = asc_sel["_sommet_km"] - asc_sel["_debut_km"]
    seg_defaut = 0.5 if dk_sel < 5 else 1.0 if dk_sel < 15 else 2.0
    col_ctrl1, col_ctrl2 = st.columns([3, 1])
    with col_ctrl1:
        seg_km = st.slider("Longueur des segments (km)", 0.25,
                          min(5.0, dk_sel / 2), float(seg_defaut), 0.25, 
                          key="climbs_slider", label_visibility="collapsed")
    with col_ctrl2:
        nb_segs = max(2, int(dk_sel / seg_km))
        st.metric("Segments", nb_segs)
    if not df_profil.empty:
        fig_col = creer_figure_col(df_profil, asc_sel, nb_segments=nb_segs)
        if fig_col:
            st.plotly_chart(fig_col, width="stretch", key="climbs_fig_col")
