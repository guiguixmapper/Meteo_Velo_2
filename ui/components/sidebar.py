"""
ui/components/sidebar.py
=========================
Sidebar — design Strava : orange, blanc, sections labellisées.
"""

import streamlit as st
import base64
from config.settings import (
    SENSIBILITE_LABELS, SENSIBILITE_PARAMS,
    SEUIL_DEBUT, SEUIL_FIN, MAX_DESCENTE_FUSION_M,
)
import core.services.climbing_service as climbing_module


def render_sidebar():
    # ── Logo header Strava style ───────────────────────────────────────────────
    st.sidebar.markdown("""
    <div style="padding:14px 0 12px 0;border-bottom:2px solid #FC4C02;margin-bottom:10px">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="width:34px;height:34px;border-radius:8px;
                    background:#FC4C02;
                    display:flex;align-items:center;justify-content:center;
                    font-size:1.1rem;box-shadow:0 2px 8px rgba(252,76,2,0.4)">🚴</div>
        <div>
          <div style="font-weight:900;font-size:0.95rem;color:#FC4C02;letter-spacing:-0.3px">Vélo & Météo</div>
          <div style="font-size:0.63rem;opacity:0.5;margin-top:1px;font-weight:500">Analyse de tracé GPX</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Fichier ───────────────────────────────────────────────────────────────
    st.sidebar.markdown('<div class="sb-section">📂 Fichier</div>', unsafe_allow_html=True)
    fichier = st.sidebar.file_uploader("Trace GPX", type=["gpx"], label_visibility="collapsed")

    # ── Sortie ────────────────────────────────────────────────────────────────
    from datetime import date
    st.sidebar.markdown('<div class="sb-section">🗓️ Sortie</div>', unsafe_allow_html=True)
    date_dep = st.sidebar.date_input("Date", value=date.today(), label_visibility="collapsed")
    col_h1, col_h2 = st.sidebar.columns(2)
    with col_h1:
        heure_dep = st.time_input("Heure", label_visibility="collapsed")
    with col_h2:
        vitesse = st.number_input("Vitesse", 5, 60, 25, label_visibility="collapsed")
    st.sidebar.caption("🕐 Heure départ   ·   ⚡ Vitesse plat km/h")

    # ── Physiologie ───────────────────────────────────────────────────────────
    st.sidebar.markdown('<div class="sb-section">💪 Physiologie</div>', unsafe_allow_html=True)
    mode = st.sidebar.radio("Mode", ["⚡ Puissance", "🫀 FC"],
                             horizontal=True, label_visibility="collapsed")
    if mode == "⚡ Puissance":
        col_p1, col_p2 = st.sidebar.columns(2)
        with col_p1: ref_val = st.number_input("FTP (W)", 50, 500, 220)
        with col_p2: poids   = st.number_input("Poids kg", 40, 150, 75)
        fc_max = None; ftp_fc = ref_val
    else:
        col_p1, col_p2 = st.sidebar.columns(2)
        with col_p1: ref_val = st.number_input("FC max", 100, 220, 185)
        with col_p2: poids   = st.number_input("Poids kg", 40, 150, 75)
        fc_max  = ref_val
        ftp_fc  = st.sidebar.number_input("FTP estimé (W)", 50, 500, 220)

    # ── Météo ─────────────────────────────────────────────────────────────────
    st.sidebar.markdown('<div class="sb-section">🌤️ Météo</div>', unsafe_allow_html=True)
    intervalle = st.sidebar.selectbox(
        "Intervalle", options=[5, 10, 15], index=1,
        format_func=lambda x: f"Checkpoints toutes les {x} min",
        label_visibility="collapsed")

    # ── Détection des montées ─────────────────────────────────────────────────
    st.sidebar.divider()
    with st.sidebar.expander("🏔️ Détection des montées", expanded=False):
        for key, default in [("sensibilite", 3),
                              ("seuil_debut", float(SEUIL_DEBUT)),
                              ("seuil_fin",   float(SEUIL_FIN)),
                              ("fusion_m",    int(MAX_DESCENTE_FUSION_M))]:
            if key not in st.session_state:
                st.session_state[key] = default

        st.slider("🎚️ Sensibilité", 1, 5, step=1, key="sensibilite",
                  help="Bas = seulement les vraies montées. Haut = capte toutes les côtes.")
        niv = st.session_state.sensibilite
        st.caption(SENSIBILITE_LABELS[niv])

        if st.button("↺ Réinitialiser", width="stretch"):
            st.session_state["_reset_demande"] = True
            st.rerun()

        if st.session_state.pop("_reset_demande", False):
            for k in ["sensibilite", "seuil_debut", "seuil_fin", "fusion_m", "_last_sensibilite"]:
                st.session_state.pop(k, None)
            st.rerun()

        with st.expander("⚙️ Réglages fins", expanded=False):
            st.caption("Synchronisés avec la sensibilité.")
            sd_sync, sf_sync, fm_sync = SENSIBILITE_PARAMS[niv]
            if st.session_state.get("_last_sensibilite") != niv:
                st.session_state.seuil_debut = sd_sync
                st.session_state.seuil_fin   = sf_sync
                st.session_state.fusion_m    = fm_sync
                st.session_state["_last_sensibilite"] = niv
            st.slider("Seuil départ (%)", 0.5, 5.0, step=0.5, key="seuil_debut")
            st.slider("Seuil fin (%)",    0.0, 3.0, step=0.5, key="seuil_fin")
            st.slider("Fusion (D− max, m)", 10, 200, step=10,  key="fusion_m")

        climbing_module.SEUIL_DEBUT           = st.session_state.seuil_debut
        climbing_module.SEUIL_FIN             = st.session_state.seuil_fin
        climbing_module.MAX_DESCENTE_FUSION_M = st.session_state.fusion_m

    # ── Options avancées ──────────────────────────────────────────────────────
    with st.sidebar.expander("🔧 Options avancées", expanded=False):
        noms_osm = st.toggle("🗺️ Nommer les cols (OpenStreetMap)", value=False,
            help="Peut être lent ou indisponible sur Streamlit Cloud.")
        if noms_osm:
            st.warning("⚠️ Serveurs Overpass souvent surchargés sur Streamlit Cloud.")
        gemini_key = st.text_input("🤖 Clé API Gemini", value="", type="password",
            help="Clé gratuite sur aistudio.google.com.")

    # ── Placeholders ──────────────────────────────────────────────────────────
    ph_fuseau = st.sidebar.empty()
    ph_fuseau.markdown("""
    <div style="background:#F5F5F5;border-radius:8px;padding:7px 12px;
                font-size:0.78rem;color:#9CA3AF;margin:6px 0">
      🌍 Fuseau : en attente…
    </div>""", unsafe_allow_html=True)
    ph_export = st.sidebar.empty()

    return dict(
        fichier=fichier, date_dep=date_dep, heure_dep=heure_dep,
        vitesse=vitesse, mode=mode, ref_val=ref_val, poids=poids,
        fc_max=fc_max, ftp_fc=ftp_fc, intervalle=intervalle,
        intervalle_sec=intervalle * 60, noms_osm=noms_osm,
        gemini_key=gemini_key, ph_fuseau=ph_fuseau, ph_export=ph_export,
    )


def render_export(ph_export, points_gpx, resultats, ascensions, points_eau,
                  score, dist_tot, d_plus, d_moins, temps_s, date_depart,
                  heure_arr, vitesse, vit_moy_reelle, calories, df_profil,
                  ref_val, mode, poids, date_dep):
    from ui.map_builder import creer_carte
    from ui.components.export import generer_html_resume

    nom_f = f"Roadbook_{date_dep.strftime('%Y%m%d')}.html"
    with ph_export.container():
        st.sidebar.markdown('<div class="sb-section">📤 Export</div>', unsafe_allow_html=True)
        if st.sidebar.button("📄 Télécharger le Roadbook", width="stretch"):
            with st.spinner("Génération..."):
                carte_export = creer_carte(points_gpx, resultats, ascensions, points_eau)
                html_bytes   = generer_html_resume(
                    score, ascensions, resultats, dist_tot, d_plus, d_moins, temps_s,
                    date_depart, heure_arr, vitesse, vit_moy_reelle, calories,
                    carte_export, df_profil, ref_val, mode, poids,
                    briefing_ia=st.session_state.get("briefing_ia"))
                b64 = base64.b64encode(html_bytes).decode()
                st.sidebar.markdown(
                    f'<div class="export-btn"><a href="data:text/html;base64,{b64}" '
                    f'download="{nom_f}">⬇️ {nom_f}</a></div>',
                    unsafe_allow_html=True)
