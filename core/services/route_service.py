"""
core/services/route_service.py
================================
Calculs de parcours : profil, checkpoints, score, analyse météo.
"""

import math
import gpxpy
import pandas as pd
from datetime import datetime, timedelta

import streamlit as st          # ← ajouté ici

from core.utils.geo import calculer_cap, direction_vent_relative, wind_chill
from core.services.climbing_service import estimer_watts, get_zone, zones_actives


def parser_gpx(data: bytes) -> list:
    """Parse un fichier GPX et retourne la liste des points."""
    try:
        gpx = gpxpy.parse(data)
        return [p for t in gpx.tracks for s in t.segments for p in s.points]
    except Exception:
        return []


def calculer_parcours(points_gpx: list, vitesse_plat_kmh: float,
                      date_depart: datetime, intervalle_sec: int) -> dict:
    """
    Calcule les statistiques du parcours et génère les checkpoints.
    Retourne un dict avec dist_tot, d_plus, d_moins, temps_s, checkpoints, profil_data.
    """
    checkpoints, profil_data = [], []
    dist_tot = d_plus = d_moins = temps_s = prochain = cap = 0.0
    vms = (vitesse_plat_kmh * 1000) / 3600

    for i in range(1, len(points_gpx)):
        p1, p2 = points_gpx[i-1], points_gpx[i]
        d  = p1.distance_2d(p2) or 0.0
        dp = 0.0
        if p1.elevation is not None and p2.elevation is not None:
            dif = p2.elevation - p1.elevation
            if dif > 0: dp = dif; d_plus += dif
            else: d_moins += abs(dif)
        dist_tot += d
        temps_s  += (d + dp * 10) / vms
        cap = calculer_cap(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
        profil_data.append({
            "Distance (km)": round(dist_tot / 1000, 3),
            "Altitude (m)":  p2.elevation if p2.elevation is not None else None,
        })

        if temps_s >= prochain:
            checkpoints.append({
                "lat":     p2.latitude,
                "lon":     p2.longitude,
                "cap":     cap,
                "Heure":   (date_depart + timedelta(seconds=temps_s)).strftime("%H:%M"),
                "Km":      round(dist_tot / 1000, 1),
                "Alt (m)": int(p2.elevation) if p2.elevation is not None else None,
            })
            prochain += intervalle_sec

    vit_moy_reelle = (dist_tot / 1000) / (temps_s / 3600) if temps_s > 0 else 0
    heure_arr = date_depart + timedelta(seconds=temps_s)

    return {
        "dist_tot":       dist_tot,
        "d_plus":         d_plus,
        "d_moins":        d_moins,
        "temps_s":        temps_s,
        "vit_moy_reelle": round(vit_moy_reelle, 1),
        "heure_arr":      heure_arr,
        "checkpoints":    checkpoints,
        "profil_data":    pd.DataFrame(profil_data),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def memoire_meteo(frozen, is_past=False, date_str=None):
    return recuperer_meteo_batch(frozen, is_past=is_past, date_str=date_str)


def enrichir_checkpoints_meteo(checkpoints: list, date_depart: datetime) -> list:
    """Enrichit les checkpoints avec les données météo Open-Meteo."""
    if not checkpoints:
        return []

    frozen = tuple((cp["lat"], cp["lon"], cp["Heure"]) for cp in checkpoints)
    resultats = memoire_meteo(frozen)

    for cp, meteo in zip(checkpoints, resultats):
        cp.update(meteo)
        if cp.get("vent_val") is not None and cp.get("dir_deg") is not None:
            cp["effet"] = direction_vent_relative(cp["cap"], cp["dir_deg"])
        if cp.get("temp_val") is not None and cp.get("vent_val") is not None:
            cp["ressenti"] = wind_chill(cp["temp_val"], cp["vent_val"])

    return checkpoints


def analyser_meteo_detaillee(resultats: list) -> dict:
    """Analyse globale de la météo sur le parcours."""
    if not resultats:
        return {}

    vents = [r.get("vent_val", 0) for r in resultats if r.get("vent_val") is not None]
    faces = sum(1 for r in resultats if "Face" in r.get("effet", ""))
    dos   = sum(1 for r in resultats if "Dos" in r.get("effet", ""))
    cotes = sum(1 for r in resultats if "Côté" in r.get("effet", ""))

    total = max(1, len([r for r in resultats if r.get("vent_val") is not None]))
    pct_face = round(faces / total * 100) if total else 0
    pct_dos  = round(dos   / total * 100) if total else 0
    pct_cote = round(cotes / total * 100) if total else 0

    pluie_sign = [r for r in resultats if r.get("pluie_pct", 0) > 50]
    premier_pluie = pluie_sign[0] if pluie_sign else None

    return {
        "vent_moy":     round(sum(vents)/len(vents), 1) if vents else 0,
        "pct_face":     pct_face,
        "pct_dos":      pct_dos,
        "pct_cote":     pct_cote,
        "segments_face": [],  # à implémenter si besoin
        "pct_pluie":    round(len(pluie_sign)/len(resultats)*100) if resultats else 0,
        "premier_pluie": premier_pluie,
    }


def calculer_score(dist_tot: float, d_plus: float, resultats: list) -> dict:
    """Calcule le score global de la sortie (0–10)."""
    dist_km = dist_tot / 1000
    # Coût route (distance + dénivelé)
    cout_route = (dist_km / 100.0) + (d_plus / 2000.0)

    # Pénalité Météo
    total_aero = total_roulement = total_thermique = 0.0
    nb_cp = max(1, len(resultats))

    for cp in resultats:
        v = cp.get("vent_val", 0)
        p = cp.get("pluie_pct", 0)
        t = cp.get("temp_val", 20)
        effet = cp.get("effet", "")

        total_thermique += abs(t - 20) / 10.0
        total_roulement += (p / 100.0) * 3.0

        if "Face" in effet:
            total_aero += (v ** 2) / 300.0
        elif "Côté" in effet:
            total_aero += (v ** 2) / 600.0
        elif "Dos" in effet:
            total_aero -= (v ** 2) / 400.0  # bonus

    cout_meteo = (total_aero + total_roulement + total_thermique) / nb_cp

    score_brut = 10.0 - cout_route - cout_meteo
    score_final = max(0.0, min(10.0, score_brut))

    if score_final >= 8.5:
        label = "CONDITIONS IDÉALES"
    elif score_final >= 7.0:
        label = "TRÈS BONNE SORTIE"
    elif score_final >= 5.0:
        label = "SORTIE RUGUEUSE"
    elif score_final >= 3.0:
        label = "CONDITIONS DIFFICILES"
    else:
        label = "ENFER ABSOLU"

    return {
        "total": round(score_final, 1),
        "label": label,
        "cout_route": round(cout_route, 1),
        "cout_meteo": round(cout_meteo, 1)
    }
