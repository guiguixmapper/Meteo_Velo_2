"""
core/services/route_service.py
================================
Calculs de parcours : profil, checkpoints, score, analyse météo.
"""

import math
import gpxpy
import pandas as pd
from datetime import datetime, timedelta
from core.utils.geo import calculer_cap, direction_vent_relative
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
            "Altitude (m)":  p2.elevation or 0,
        })
        if temps_s >= prochain:
            hp = date_depart + timedelta(seconds=temps_s)
            checkpoints.append({
                "lat":      p2.latitude,
                "lon":      p2.longitude,
                "Cap":      cap,
                "Heure":    hp.strftime("%d/%m %H:%M"),
                "Heure_API": hp.replace(minute=0, second=0).strftime("%Y-%m-%dT%H:00"),
                "Km":       round(dist_tot / 1000, 1),
                "Alt (m)":  int(p2.elevation) if p2.elevation else 0,
            })
            prochain += intervalle_sec

    return dict(
        dist_tot=dist_tot, d_plus=d_plus, d_moins=d_moins,
        temps_s=temps_s, cap=cap,
        checkpoints=checkpoints, profil_data=profil_data,
    )


def enrichir_checkpoints_meteo(checkpoints: list, rep_list: list) -> list:
    """Fusionne les checkpoints avec les données météo extraites."""
    from infrastructure.open_meteo_client import extraire_meteo
    resultats = []
    for i, cp in enumerate(checkpoints):
        m = extraire_meteo(rep_list[i] if i < len(rep_list) else {}, cp["Heure_API"])
        if m["dir_deg"] is not None:
            m["effet"] = direction_vent_relative(cp["Cap"], m["dir_deg"])
        cp.update(m)
        resultats.append(cp)
    return resultats


def analyser_meteo_detaillee(resultats: list, dist_tot: float) -> dict | None:
    valides = [cp for cp in resultats if cp.get("temp_val") is not None]
    if not valides:
        return None

    cps_pluie   = [cp for cp in valides if (cp.get("pluie_pct") or 0) >= 50]
    pct_pluie   = len(cps_pluie) / len(valides) * 100
    premier_pluie = next((cp for cp in valides if (cp.get("pluie_pct") or 0) >= 50), None)

    compteur = {"⬇️ Face": 0, "⬆️ Dos": 0, "↙️ Côté (D)": 0, "↘️ Côté (G)": 0, "—": 0}
    for cp in valides:
        compteur[cp.get("effet", "—")] = compteur.get(cp.get("effet", "—"), 0) + 1

    total_v   = len(valides)
    pct_face  = round(compteur["⬇️ Face"] / total_v * 100)
    pct_dos   = round(compteur["⬆️ Dos"]  / total_v * 100)
    pct_cote  = round((compteur["↙️ Côté (D)"] + compteur["↘️ Côté (G)"]) / total_v * 100)

    segments_face, en_face, debut_face = [], False, None
    for cp in valides:
        if cp.get("effet") == "⬇️ Face":
            if not en_face: en_face = True; debut_face = cp["Km"]
        else:
            if en_face: segments_face.append((debut_face, cp["Km"])); en_face = False
    if en_face:
        segments_face.append((debut_face, valides[-1]["Km"]))

    return dict(
        pct_pluie=round(pct_pluie), premier_pluie=premier_pluie,
        pct_face=pct_face, pct_dos=pct_dos, pct_cote=pct_cote,
        segments_face=segments_face, n_valides=total_v,
    )


def calculer_score(resultats: list, ascensions: list, d_plus: float,
                   vitesse: float, ref_val: float, mode: str, poids: float) -> dict:
    valides = [cp for cp in resultats if cp.get("temp_val") is not None]

    if valides:
        tm = sum(cp["temp_val"] for cp in valides) / len(valides)
        if   15 <= tm <= 22: s_temp = 2.0
        elif 10 <= tm <= 27: s_temp = 1.5
        elif  5 <= tm <= 32: s_temp = 0.8
        elif  0 <= tm:       s_temp = 0.3
        else:                s_temp = 0.0

        POIDS_EFFET = {"⬇️ Face": 1.5, "↙️ Côté (D)": 0.7, "↘️ Côté (G)": 0.7, "⬆️ Dos": -0.3, "—": 0.5}
        ve_moy  = sum((cp.get("vent_val") or 0) * POIDS_EFFET.get(cp.get("effet", "—"), 0.5) for cp in valides) / len(valides)
        if   ve_moy <= 8:  s_vent = 2.0
        elif ve_moy <= 18: s_vent = 1.5
        elif ve_moy <= 30: s_vent = 0.8
        elif ve_moy <= 45: s_vent = 0.3
        else:              s_vent = 0.0

        pm      = sum(cp.get("pluie_pct") or 0 for cp in valides) / len(valides)
        s_pluie = round(max(0.0, 2.0 * (1 - pm / 100)), 2)
        sm      = s_temp + s_vent + s_pluie
    else:
        sm = 3.0

    dist_km = sum(cp.get("Km", 0) for cp in resultats[-1:])
    s_dist  = 0.5 if dist_km < 30 else 0.7 if dist_km < 80 else 0.9 if dist_km < 150 else 1.0
    s_dplus = 0.5 if d_plus < 300 else 0.7 if d_plus < 1000 else 0.9 if d_plus < 2500 else 1.0
    s_parcours = s_dist + s_dplus

    if ascensions and ref_val > 0:
        wm  = sum(estimer_watts(a["_pente_moy"], vitesse, poids) for a in ascensions) / len(ascensions)
        pct = wm / ref_val if mode == "⚡ Puissance" else 0.85
        if   pct <= 0.50: s_effort = 0.8
        elif pct <= 0.70: s_effort = 1.2
        elif pct <= 0.90: s_effort = 2.0
        elif pct <= 1.05: s_effort = 1.5
        else:             s_effort = 0.8
    else:
        s_effort = 1.0

    sc    = max(2.0, s_parcours + s_effort)
    total = round(min(10.0, max(0.0, sm + sc)), 1)
    lbl   = ("🔴 Déconseillé"           if total < 3.5 else
             "🟠 Conditions difficiles"  if total < 5.0 else
             "🟡 Conditions correctes"   if total < 6.5 else
             "🟢 Bonne sortie"           if total < 8.0 else
             "⭐ Conditions idéales")

    return dict(total=total, label=lbl,
                score_meteo=round(max(0.0, sm), 1),
                score_cols=round(sc, 1),
                score_effort=round(s_effort, 1))
