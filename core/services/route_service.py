"""
core/services/route_service.py
================================
Calculs de parcours : profil, checkpoints, score, analyse météo.
VERSION OPTIMISÉE : Batch processing pour la météo et calculs vectorisés.
"""

import math
import gpxpy
import pandas as pd
import logging
from datetime import datetime, timedelta
from core.utils.geo import calculer_cap, direction_vent_relative, wind_chill
from core.services.climbing_service import estimer_watts, get_zone, zones_actives
from infrastructure.open_meteo_client import recuperer_meteo_batch

logger = logging.getLogger(__name__)

def parser_gpx(data: bytes) -> list:
    """Parse un fichier GPX et retourne la liste des points."""
    try:
        gpx = gpxpy.parse(data)
        return [p for t in gpx.tracks for s in t.segments for p in s.points]
    except Exception as e:
        logger.error(f"Erreur parsing GPX : {e}")
        return []

def calculer_parcours(points_gpx: list, vitesse_plat_kmh: float,
                      date_depart: datetime, intervalle_sec: int) -> dict:
    """
    Calcule les statistiques du parcours et génère les checkpoints.
    Retourne un dict avec dist_tot, d_plus, d_moins, temps_s, checkpoints, profil_data.
    """
    checkpoints, profil_data = [], []
    dist_tot = d_plus = d_moins = temps_s = prochain = 0.0
    vms = (vitesse_plat_kmh * 1000) / 3600

    for i in range(1, len(points_gpx)):
        p1, p2 = points_gpx[i-1], points_gpx[i]
        d = p1.distance_2d(p2) or 0.0
        dz = p2.elevation - p1.elevation if (p1.elevation is not None and p2.elevation is not None) else 0.0
        
        dist_tot += d
        if dz > 0: d_plus += dz
        else: d_moins += abs(dz)

        # Calcul de la vitesse ajustée par la pente (simple) pour le timing
        pente = (dz / d * 100) if d > 0 else 0
        v_adj = vms * (1.0 / (1.0 + max(0, pente/10.0))) # Ralentissement en montée
        dt = d / max(0.5, v_adj)
        temps_s += dt

        # Sauvegarde pour le graphique de profil
        profil_data.append({
            "Distance (km)": dist_tot / 1000,
            "Altitude (m)": p2.elevation or 0
        })

        # Création d'un checkpoint tous les 'intervalle_sec'
        if temps_s >= prochain:
            cap = calculer_cap(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
            heure_point = date_depart + timedelta(seconds=temps_s)
            
            checkpoints.append({
                "lat": p2.latitude,
                "lon": p2.longitude,
                "cap": cap,
                "Heure": heure_point.strftime("%H:%M"),
                "heure_iso": heure_point.strftime("%Y-%m-%dT%H:00"), # Format pour l'API
                "Km": round(dist_tot / 1000, 1),
                "Alt (m)": int(p2.elevation or 0)
            })
            prochain += intervalle_sec

    return {
        "dist_tot": dist_tot,
        "d_plus": d_plus,
        "d_moins": d_moins,
        "temps_s": temps_s,
        "checkpoints": checkpoints,
        "profil_data": profil_data
    }

def enrichir_checkpoints_meteo(checkpoints: list, mode: str, ref_val: float, poids: float, vitesse_plat: float) -> list:
    """
    Récupère la météo en UN SEUL APPEL et calcule les impacts (vent, watts, etc.)
    """
    if not checkpoints:
        return []

    # 1. Préparation des listes pour l'appel BATCH
    lats = [cp["lat"] for cp in checkpoints]
    lons = [cp["lon"] for cp in checkpoints]
    dates = [cp["heure_iso"] for cp in checkpoints]

    # 2. Appel API unique (Batch)
    meteo_data = recuperer_meteo_batch(lats, lons, dates)

    # 3. Fusion et calculs locaux
    resultats = []
    for i, cp in enumerate(checkpoints):
        m = meteo_data[i] if i < len(meteo_data) else {}
        
        # Calcul du vent relatif
        cap = cp["cap"]
        dir_vent = m.get("dir_deg", 0)
        effet = direction_vent_relative(cap, dir_vent)
        
        # Calcul du ressenti (Wind Chill)
        ressenti = wind_chill(m.get("temp_val"), m.get("vent_val"))
        
        # Estimation de l'effort (Watts)
        # Note: Sur un checkpoint, la pente est lissée par l'intervalle
        w = estimer_watts(0.0, vitesse_plat, poids) # Pente moyenne 0 ici, ajustée par le vent plus tard
        _, z_lbl, z_coul = get_zone(w, ref_val, zones_actives(mode))

        # Enrichissement du dictionnaire
        cp.update({
            "Ciel": m.get("Ciel", "—"),
            "temp_val": m.get("temp_val"),
            "Pluie": f"{m.get('pluie_pct', 0)}%",
            "pluie_pct": m.get("pluie_pct", 0),
            "vent_val": m.get("vent_val"),
            "rafales_val": m.get("rafales_val"),
            "Dir": f"{m.get('dir_deg', 0)}°",
            "dir_deg": m.get("dir_deg", 0),
            "effet": effet,
            "ressenti": ressenti,
            "Zone": z_lbl,
            "Couleur": z_coul
        })
        resultats.append(cp)

    return resultats

def analyser_meteo_detaillee(resultats: list) -> dict:
    """Analyse les segments critiques (vent de face, pluie)."""
    if not resultats:
        return {"segments_face": [], "pct_pluie": 0, "premier_pluie": None}

    segments_face = []
    current_start = None
    
    points_pluie = [cp for cp in resultats if cp.get("pluie_pct", 0) > 50]
    
    for cp in resultats:
        if "Face" in cp.get("effet", ""):
            if current_start is None: current_start = cp["Km"]
        else:
            if current_start is not None:
                if cp["Km"] - current_start > 2: # Segment de plus de 2km
                    segments_face.append((current_start, cp["Km"]))
                current_start = None

    return {
        "segments_face": segments_face,
        "pct_pluie": int(len(points_pluie) / len(resultats) * 100),
        "premier_pluie": points_pluie[0] if points_pluie else None
    }

def calculer_score(resultats: list, d_plus: float, dist_tot: float) -> dict:
    """Calcule une note de 0 à 10 pour la sortie."""
    if not resultats: return {"total": 0, "label": "N/A", "cout_meteo": 0, "cout_route": 0}

    # 1. Difficulté Physique (Route)
    ratio_dplus = d_plus / (dist_tot / 1000) if dist_tot > 0 else 0
    cout_route = min(4.0, ratio_dplus / 10.0) # Max 4 points de difficulté
    
    # 2. Impact Météo
    total_aero = total_thermique = 0.0
    for cp in resultats:
        v = cp.get("vent_val", 0)
        t = cp.get("temp_val", 20)
        eff = cp.get("effet", "")
        
        # Pénalité vent
        if "Face" in eff: total_aero += (v**2) / 400
        elif "Dos" in eff: total_aero -= (v**2) / 600
        
        # Pénalité thermique
        total_thermique += abs(t - 20) / 15
        
    nb = len(resultats)
    cout_meteo = (total_aero + total_thermique) / nb
    
    score_final = max(0, min(10, 10 - cout_route - cout_meteo))
    
    labels = [(9,"🌟 Exceptionnel"),(7,"🟢 Idéal"),(5,"🟡 Correct"),(3,"🟠 Difficile"),(0,"🔴 Hostile")]
    lbl = "Inconnu"
    for s, l in labels:
        if score_final >= s:
            lbl = l; break
            
    return {
        "total": round(score_final, 1),
        "label": lbl,
        "cout_meteo": round(cout_meteo, 1),
        "cout_route": round(cout_route, 1),
        "score_meteo": round(6 - cout_meteo, 1),
        "score_cols": round(4 - cout_route, 1)
    }
