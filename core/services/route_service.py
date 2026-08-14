"""
core/services/route_service.py
================================
Calculs de parcours : profil, checkpoints, enrichissement météo, analyses.
Contient la logique métier pour le traitement des traces GPX et les calculs de roulabilité.
"""

from typing import Optional
import math
import gpxpy
import pandas as pd
from datetime import datetime, timedelta
import logging

from core.utils.geo import calculer_cap, direction_vent_relative
from core.services.climbing_service import estimer_watts, get_zone, zones_actives
from core.exceptions import GPXError, ValidationError, DataProcessingError
from config.settings import RouteResult, CheckpointData, ProfilePoint

logger = logging.getLogger(__name__)


def parser_gpx(data: bytes) -> list:
    """
    Parse un fichier GPX et retourne la liste des points géolocalisés.
    
    Args:
        data: Contenu binaire du fichier GPX
        
    Returns:
        Liste des points GPX. Chaque point contient latitude, longitude, elevation.
        
    Raises:
        GPXError: Si le fichier est invalide ou vide
    """
    if not data:
        raise GPXError("Fichier GPX vide")
    
    try:
        gpx = gpxpy.parse(data)
        points = [p for t in gpx.tracks for s in t.segments for p in s.points]
        
        if not points:
            raise GPXError("Aucun point GPX trouvé dans le fichier")
        
        return points
    
    except gpxpy.GPXException as e:
        raise GPXError(f"Erreur parsing GPX : {str(e)}") from e
    except Exception as e:
        raise GPXError(f"Erreur inattendue lors du parsing GPX : {str(e)}") from e


def calculer_parcours(
    points_gpx: list,
    vitesse_plat_kmh: float,
    date_depart: datetime,
    intervalle_sec: int,
) -> RouteResult:
    """
    Calcule les statistiques globales du parcours et génère les checkpoints réguliers.
    
    Args:
        points_gpx: Liste des points GPS du tracé
        vitesse_plat_kmh: Vitesse moyenne en plat (km/h) pour l'estimation de temps
        date_depart: Heure de départ
        intervalle_sec: Intervalle en secondes entre chaque checkpoint
        
    Returns:
        Dict contenant statistiques et checkpoints
        
    Raises:
        ValidationError: Si les paramètres sont invalides
        DataProcessingError: Si le calcul échoue
    """
    # Validation
    if not points_gpx:
        raise ValidationError("points_gpx", "Liste vide")
    if vitesse_plat_kmh <= 0:
        raise ValidationError("vitesse_plat_kmh", "Doit être > 0")
    if intervalle_sec <= 0:
        raise ValidationError("intervalle_sec", "Doit être > 0")
    
    try:
        checkpoints: list[CheckpointData] = []
        profil_data: list[ProfilePoint] = []
        dist_tot = d_plus = d_moins = temps_s = prochain = cap = 0.0
        # Conversion : vitesse (km/h) → vitesse (m/s)
        velocity_ms = (vitesse_plat_kmh * 1000) / 3600

        for i in range(1, len(points_gpx)):
            p1, p2 = points_gpx[i - 1], points_gpx[i]
            
            # Distance 2D entre les deux points
            distance_m = p1.distance_2d(p2) or 0.0
            elevation_gain = 0.0
            
            # Calcul du dénivelé (temps incluent pénalité pour montée)
            if p1.elevation is not None and p2.elevation is not None:
                diff = p2.elevation - p1.elevation
                if diff > 0:
                    elevation_gain = diff
                    d_plus += diff
                else:
                    d_moins += abs(diff)
            
            dist_tot += distance_m
            # Temps incluant pénalité pour dénivelé positif (×10 = effet de la montée)
            temps_s += (distance_m + elevation_gain * 10) / velocity_ms
            
            # Calcul du cap (direction) pour le prochain point
            cap = calculer_cap(
                p1.latitude, p1.longitude,
                p2.latitude, p2.longitude
            )
            
            # Enregistrement du profil altimétrique
            profil_data.append({
                "Distance (km)": round(dist_tot / 1000, 3),
                "Altitude (m)": p2.elevation or 0,
            })
            
            # Création d'un checkpoint tous les `intervalle_sec`
            if temps_s >= prochain:
                heure_point = date_depart + timedelta(seconds=temps_s)
                checkpoints.append({
                    "lat": p2.latitude,
                    "lon": p2.longitude,
                    "Cap": cap,
                    "Heure": heure_point.strftime("%d/%m %H:%M"),
                    "Heure_API": heure_point.replace(minute=0, second=0).strftime(
                        "%Y-%m-%dT%H:00"
                    ),
                    "Km": round(dist_tot / 1000, 1),
                    "Alt (m)": int(p2.elevation) if p2.elevation else 0,
                })
                prochain += intervalle_sec

        return dict(
            dist_tot=dist_tot,
            d_plus=d_plus,
            d_moins=d_moins,
            temps_s=temps_s,
            cap=cap,
            checkpoints=checkpoints,
            profil_data=profil_data,
        )
    
    except Exception as e:
        raise DataProcessingError("calculer_parcours", e)


def enrichir_checkpoints_meteo(
    checkpoints: list[CheckpointData],
    rep_list: list,
) -> list[CheckpointData]:
    """
    Fusionne les checkpoints avec les données météo extraites des réponses API.
    Ajoute également l'effet du vent relative au cap du cycliste.
    
    Args:
        checkpoints: Checkpoints géolocalisés (sans météo)
        rep_list: Réponses API Open-Meteo pour chaque point
        
    Returns:
        Liste de checkpoints enrichis avec données météo et effet du vent
        
    Raises:
        ValidationError: Si les listes ont des tailles incompatibles
    """
    if not checkpoints:
        return []
    
    try:
        from infrastructure.open_meteo_client import extraire_meteo
        
        resultats = []
        for i, checkpoint in enumerate(checkpoints):
            # Extraction météo pour ce checkpoint
            weather_data = extraire_meteo(
                rep_list[i] if i < len(rep_list) else {},
                checkpoint["Heure_API"]
            )
            
            # Calcul de l'effet du vent (face/dos/côté)
            if weather_data["dir_deg"] is not None:
                weather_data["effet"] = direction_vent_relative(
                    checkpoint["Cap"],
                    weather_data["dir_deg"]
                )
            
            checkpoint.update(weather_data)
            resultats.append(checkpoint)
        
        return resultats
    
    except Exception as e:
        logger.error(f"Erreur enrichissement météo : {e}")
        # Retourner checkpoints sans météo plutôt que d'échouer
        return checkpoints


def analyser_meteo_detaillee(
    resultats: list[CheckpointData],
    dist_tot: float,
) -> Optional[dict]:
    """
    Analyse complète de la météo sur le parcours.
    Calcule les pourcentages de pluie, répartition des effets de vent, etc.
    
    Args:
        resultats: Checkpoints enrichis avec données météo
        dist_tot: Distance totale en mètres
        
    Returns:
        Dict avec stats météo (pct_pluie, premier_pluie, pct_face, pct_dos, pct_cote,
        segments_face, n_valides) ou None si pas assez de données
    """
    # Filtrer les checkpoints avec données météo valides
    valid_checkpoints = [
        cp for cp in resultats
        if cp.get("temp_val") is not None
    ]
    
    if not valid_checkpoints:
        return None

    # Analyse pluie
    rainy_checkpoints = [
        cp for cp in valid_checkpoints
        if (cp.get("pluie_pct") or 0) >= 50
    ]
    rain_percentage = len(rainy_checkpoints) / len(valid_checkpoints) * 100
    first_rain = next(
        (cp for cp in valid_checkpoints if (cp.get("pluie_pct") or 0) >= 50),
        None
    )

    # Analyse effets vent
    wind_effect_count = {
        "⬇️ Face": 0,
        "⬆️ Dos": 0,
        "↙️ Côté (D)": 0,
        "↘️ Côté (G)": 0,
        "—": 0
    }
    for cp in valid_checkpoints:
        effect = cp.get("effet", "—")
        wind_effect_count[effect] = wind_effect_count.get(effect, 0) + 1

    total_valid = len(valid_checkpoints)
    pct_face = round(wind_effect_count["⬇️ Face"] / total_valid * 100)
    pct_dos = round(wind_effect_count["⬆️ Dos"] / total_valid * 100)
    pct_side = round(
        (wind_effect_count["↙️ Côté (D)"] + wind_effect_count["↘️ Côté (G)"])
        / total_valid * 100
    )

    # Identification des segments face au vent
    face_segments = []
    in_face = False
    face_start = None
    
    for cp in valid_checkpoints:
        if cp.get("effet") == "⬇️ Face":
            if not in_face:
                in_face = True
                face_start = cp["Km"]
        else:
            if in_face:
                face_segments.append((face_start, cp["Km"]))
                in_face = False
    
    if in_face:
        face_segments.append((face_start, valid_checkpoints[-1]["Km"]))

    return dict(
        pct_pluie=round(rain_percentage),
        premier_pluie=first_rain,
        pct_face=pct_face,
        pct_dos=pct_dos,
        pct_cote=pct_side,
        segments_face=face_segments,
        n_valides=total_valid,
    )


def calculer_score(
    resultats: list[CheckpointData],
    ascensions: list,
    d_plus: float,
    vitesse: float,
    ref_val: Optional[float],
    mode: str,
    poids: float,
    dist_tot: float,
) -> dict:
    """
    Calcule l'Indice de Roulabilité sur 10.
    
    Départ à 10 points. Les facteurs adverses enlèvent des points :
    - Route : distance et dénivelé
    - Météo : vent, pluie, température
    
    Args:
        resultats: Checkpoints enrichis avec météo
        ascensions: Liste des ascensions détectées
        d_plus: Dénivelé positif en mètres
        vitesse: Vitesse en plat (km/h)
        ref_val: Valeur de référence FTP/FC
        mode: Mode de calcul (Puissance ou FC)
        poids: Poids du cycliste (kg)
        dist_tot: Distance totale (m)
        
    Returns:
        Dict avec:
            - total (float): Score final 0-10
            - label (str): Description du score
            - cout_route (float): Pénalité route
            - cout_meteo (float): Pénalité météo
    """
    dist_km = dist_tot / 1000.0
    
    # 1. Pénalité de la route (TRÈS NÉGLIGEABLE)
    # ~1 point pour 500km OU 5000m de D+
    route_penalty = (dist_km / 500.0) + (d_plus / 5000.0)
    
    # 2. Pénalité Météo
    total_aerodynamic = 0.0
    total_rolling = 0.0
    total_thermal = 0.0
    nb_checkpoints = max(1, len(resultats))
    
    for cp in resultats:
        wind_speed = cp.get("vent_val", 0)
        rain_pct = cp.get("pluie_pct", 0)
        temp = cp.get("temp_val", 20)
        wind_effect = cp.get("effet", "")
        
        # Thermique : Idéal = 20°C. Ex: 10°C = -1 point
        total_thermal += abs(temp - 20) / 10.0
        
        # Pluie : 100% = -3 points
        total_rolling += (rain_pct / 100.0) * 3.0
        
        # Vent : Pénalité quadratique selon effet
        if "Face" in wind_effect:
            total_aerodynamic += (wind_speed ** 2) / 300.0
        elif "Côté" in wind_effect:
            total_aerodynamic += (wind_speed ** 2) / 600.0
        elif "Dos" in wind_effect:
            # Bonus vent de dos
            total_aerodynamic -= (wind_speed ** 2) / 400.0
            
    # Moyennes par checkpoint
    avg_aero_penalty = total_aerodynamic / nb_checkpoints
    avg_rolling_penalty = total_rolling / nb_checkpoints
    avg_thermal_penalty = total_thermal / nb_checkpoints
    
    weather_penalty = avg_aero_penalty + avg_rolling_penalty + avg_thermal_penalty
    
    # 3. Score Final
    raw_score = 10.0 - route_penalty - weather_penalty
    final_score = max(0.0, min(10.0, raw_score))
    
    # Détermination du label
    if final_score >= 8.5:
        label = "CONDITIONS IDÉALES"
    elif final_score >= 7.0:
        label = "TRÈS BONNE SORTIE"
    elif final_score >= 5.0:
        label = "SORTIE RUGUEUSE"
    elif final_score >= 3.0:
        label = "CONDITIONS DIFFICILES"
    else:
        label = "ENFER ABSOLU"

    return {
        "total": round(final_score, 1),
        "label": label,
        "cout_route": round(route_penalty, 1),
        "cout_meteo": round(weather_penalty, 1),
    }
