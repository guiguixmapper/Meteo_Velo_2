"""
app.py — Point d'entrée unique
================================
Vélo & Météo — Analyse de tracé GPX.
Ce fichier ne contient QUE le bootstrap et l'orchestration.
Toute la logique est dans core/, infrastructure/ et ui/.
"""

import streamlit as st
import pandas as pd
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Imports architecture ───────────────────────────────────────────────────────
from ui.styles.theme import CSS
from ui.components.sidebar import render_sidebar, render_export
from ui.components.metrics_banner import render_metrics_banner
from ui.components.map_view import render_map_view
from ui.components.profile_view import render_profile_view
from ui.components.weather_view import render_weather_view
from ui.components.climbs_view import render_climbs_view
from ui.components.detail_view import render_detail_view
from ui.components.coach_view import render_coach_view

from core.services.route_service import (
    parser_gpx, calculer_parcours, enrichir_checkpoints_meteo,
    analyser_meteo_detaillee, calculer_score,
)
from core.services.climbing_service import (
    detecter_ascensions, estimer_temps_col, calculer_calories,
)
from infrastructure.open_meteo_client import (
    recuperer_fuseau, recuperer_soleil, recuperer_uv_pollen, recuperer_meteo_batch,
)
from infrastructure.osm_client import enrichir_cols, recuperer_points_eau
from config.settings import MAX_CHECKPOINTS_METEO


# ── Cache météo avec retry ─────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def memoire_meteo(frozen, is_past=False, date_str=None):
    return recuperer_meteo_batch(frozen, is_past=is_past, date_str=date_str)


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    st.set_page_config(page_title="Vélo & Météo", page_icon="🚴‍♂️", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)

    # ── Sidebar ────────────────────────────────────────────────────────────────
    params = render_sidebar()
    fichier        = params["fichier"]
    date_dep       = params["date_dep"]
    heure_dep      = params["heure_dep"]
    vitesse        = params["vitesse"]
    mode           = params["mode"]
    ref_val        = params["ref_val"]
    poids          = params["poids"]
    ftp_fc         = params["ftp_fc"]
    intervalle     = params["intervalle"]
    intervalle_sec = params["intervalle_sec"]
    noms_osm       = params["noms_osm"]
    gemini_key     = params["gemini_key"]
    ph_fuseau      = params["ph_fuseau"]
    ph_export      = params["ph_export"]

    # ── Page d'accueil ─────────────────────────────────────────────────────────
    if fichier is None:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#9ca3af">
          <div style="font-size:3rem;margin-bottom:12px">🗺️</div>
          <div style="font-size:1rem;font-weight:600;color:#374151;margin-bottom:6px">Importez un fichier GPX</div>
          <div style="font-size:0.83rem">Déposez votre trace dans le panneau de gauche pour démarrer l'analyse.</div>
        </div>""", unsafe_allow_html=True)
        return

    st.markdown('<div style="height: 1.5rem;"></div>', unsafe_allow_html=True)

    # ── Chargement GPX ─────────────────────────────────────────────────────────
    etapes = st.empty()
    with etapes.container():
        with st.spinner("📍 Lecture du fichier GPX…"):
            points_gpx = parser_gpx(fichier.read())
    if not points_gpx:
        st.error("❌ Fichier GPX vide ou corrompu.")
        return

    # ── Fuseau horaire ─────────────────────────────────────────────────────────
    with etapes.container():
        with st.spinner("🌍 Fuseau horaire…"):
            fuseau = recuperer_fuseau(points_gpx[0].latitude, points_gpx[0].longitude)
    ph_fuseau.success(f"🌍 **{fuseau}**")
    date_depart = datetime.combine(date_dep, heure_dep)

    # ── Soleil ─────────────────────────────────────────────────────────────────
    with etapes.container():
        with st.spinner("🌅 Lever/coucher du soleil…"):
            infos_soleil = recuperer_soleil(
                points_gpx[0].latitude, points_gpx[0].longitude,
                date_dep.strftime("%Y-%m-%d"))

    # ── UV & Pollen ────────────────────────────────────────────────────────────
    with etapes.container():
        with st.spinner("🌞 UV & Pollen…"):
            uv_pollen = recuperer_uv_pollen(
                points_gpx[0].latitude, points_gpx[0].longitude,
                date_dep.strftime("%Y-%m-%d"))

    # ── Calcul parcours (mis en cache) ─────────────────────────────────────────
    _key = f"parcours_{id(points_gpx)}_{vitesse}_{intervalle}_{date_depart}"
    if _key not in st.session_state:
        with etapes.container():
            with st.spinner("📐 Calcul du parcours…"):
                res = calculer_parcours(points_gpx, vitesse, date_depart, intervalle_sec)
        st.session_state[_key] = res
    else:
        res = st.session_state[_key]

    checkpoints = res["checkpoints"]
    profil_data = res["profil_data"]
    dist_tot    = res["dist_tot"]
    d_plus      = res["d_plus"]
    d_moins     = res["d_moins"]
    temps_s     = res["temps_s"]
    cap         = res["cap"]

    vit_moy_reelle = round((dist_tot / 1000) / (temps_s / 3600), 1) if temps_s > 0 else vitesse
    heure_arr      = date_depart + timedelta(seconds=temps_s)

    # Checkpoint d'arrivée
    pf = points_gpx[-1]
    checkpoints.append({
        "lat": pf.latitude, "lon": pf.longitude, "Cap": cap,
        "Heure": heure_arr.strftime("%d/%m %H:%M") + " 🏁",
        "Heure_API": heure_arr.replace(minute=0, second=0).strftime("%Y-%m-%dT%H:00"),
        "Km": round(dist_tot / 1000, 1),
        "Alt (m)": int(pf.elevation) if pf.elevation else 0,
    })
    df_profil = pd.DataFrame(profil_data)

    # ── Détection ascensions ───────────────────────────────────────────────────
    with etapes.container():
        with st.spinner("⛰️ Détection des ascensions…"):
            ascensions = detecter_ascensions(df_profil)

    if ascensions:
        dist_cum, pt_par_km = 0.0, {}
        for i in range(1, len(points_gpx)):
            p1, p2 = points_gpx[i-1], points_gpx[i]
            dist_cum += p1.distance_2d(p2) or 0.0
            pt_par_km[round(dist_cum / 1000, 3)] = p2

        def coords_au_km(km_cible):
            if not pt_par_km: return None, None
            km_proche = min(pt_par_km.keys(), key=lambda k: abs(k - km_cible))
            pt = pt_par_km[km_proche]
            return pt.latitude, pt.longitude

        for asc in ascensions:
            asc["_lat_sommet"], asc["_lon_sommet"] = coords_au_km(asc["_sommet_km"])
            asc["_lat_debut"],  asc["_lon_debut"]  = coords_au_km(asc["_debut_km"])

    # ── Noms OSM ──────────────────────────────────────────────────────────────
    if noms_osm and ascensions:
        with etapes.container():
            with st.spinner("🗺️ Noms des cols (OpenStreetMap)…"):
                ascensions = enrichir_cols(ascensions, points_gpx)
    for asc in ascensions:
        asc.setdefault("Nom", "—")
        asc.setdefault("Nom OSM alt", None)

    # ── Points d'eau ──────────────────────────────────────────────────────────
    with etapes.container():
        with st.spinner("💧 Recherche des points d'eau…"):
            coords_tuple = tuple((p.latitude, p.longitude) for p in points_gpx[::5])
            points_eau   = recuperer_points_eau(coords_tuple)

    # ── Météo ─────────────────────────────────────────────────────────────────
    with etapes.container():
        with st.spinner("📡 Récupération météo…"):
            cps_meteo = checkpoints[::max(1, len(checkpoints)//MAX_CHECKPOINTS_METEO)] \
                        if len(checkpoints) > MAX_CHECKPOINTS_METEO else checkpoints
            frozen    = tuple((cp["lat"], cp["lon"], cp["Heure_API"]) for cp in cps_meteo)
            is_past   = date_dep < __import__('datetime').date.today()
            rep_list  = memoire_meteo(frozen, is_past=is_past, date_str=date_dep.strftime("%Y-%m-%d"))

            # Interpolation si sous-échantillonnage
            if rep_list and len(cps_meteo) < len(checkpoints):
                idx_map  = {id(cps_meteo[i]): i for i in range(len(cps_meteo))}
                rep_full = []
                j = 0
                for cp in checkpoints:
                    if id(cp) in idx_map: j = idx_map[id(cp)]
                    rep_full.append(rep_list[j] if j < len(rep_list) else {})
                rep_list = rep_full

    etapes.empty()

    err_meteo = rep_list is None
    if err_meteo:
        st.warning("⚠️ Météo indisponible (429). Patientez 1-2 minutes et rechargez.")
        resultats = [{**cp, "Ciel":"—","temp_val":None,"Pluie":"—","pluie_pct":None,
                      "vent_val":None,"rafales_val":None,"Dir":"—","dir_deg":None,
                      "effet":"—","ressenti":None} for cp in checkpoints]
    else:
        resultats = enrichir_checkpoints_meteo(checkpoints, rep_list)

    # ── Score + métriques ─────────────────────────────────────────────────────
    calories      = calculer_calories(max(1, poids-10), temps_s, dist_tot, d_plus, vitesse)
    score         = calculer_score(resultats, ascensions, d_plus, vitesse, ref_val, mode, poids, dist_tot)
    analyse_meteo = analyser_meteo_detaillee(resultats, dist_tot)

    for asc in ascensions:
        temps_debut = (asc["_debut_km"] / vitesse) * 3600
        mins_col, vit_col = estimer_temps_col(
            asc["_sommet_km"] - asc["_debut_km"], asc["_pente_moy"], vitesse)
        heure_sommet = date_depart + timedelta(seconds=temps_debut) + timedelta(minutes=mins_col)
        asc["Temps col"]      = f"{mins_col} min ({vit_col} km/h)"
        asc["Arrivée sommet"] = heure_sommet.strftime("%H:%M")

    # ── Bandeau métriques ─────────────────────────────────────────────────────
    render_metrics_banner(score, dist_tot, d_plus, d_moins, temps_s,
                          vit_moy_reelle, heure_arr, calories)

    # ── Export sidebar ────────────────────────────────────────────────────────
    render_export(ph_export, points_gpx, resultats, ascensions, points_eau,
                  score, dist_tot, d_plus, d_moins, temps_s, date_depart,
                  heure_arr, vitesse, vit_moy_reelle, calories, df_profil,
                  ref_val, mode, poids, date_dep)

    # ── Onglets ───────────────────────────────────────────────────────────────
    tab_carte, tab_profil, tab_meteo, tab_cols, tab_detail, tab_analyse = st.tabs([
        "🗺️ Carte", "⛰️ Profil & Cols", "🌤️ Météo", "🏔️ Ascensions", "📋 Détail", "🤖 Coach IA"
    ])

    with tab_carte:
        render_map_view(points_gpx, resultats, ascensions, points_eau,
                        infos_soleil, date_depart, heure_arr)

    with tab_profil:
        render_profile_view(df_profil, ascensions, vitesse, ref_val, mode, poids)

    with tab_meteo:
        render_weather_view(resultats, analyse_meteo, uv_pollen, err_meteo)

    with tab_cols:
        render_climbs_view(ascensions, df_profil, vitesse, ref_val, ftp_fc, mode, poids, ftp_w=ref_val if mode == "⚡ Puissance" else ftp_fc)

    with tab_detail:
        render_detail_view(resultats, intervalle)

    with tab_analyse:
        render_coach_view(gemini_key, dist_tot, d_plus, temps_s, calories, score,
                          ascensions, analyse_meteo, resultats, heure_dep, heure_arr,
                          vit_moy_reelle, infos_soleil, date_dep, points_eau, uv_pollen)


if __name__ == "__main__":
    main()
