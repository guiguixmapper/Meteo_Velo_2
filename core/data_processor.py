"""
core/data_processor.py
=======================
Traitement orchestré des données de parcours.
Sépare la logique métier de l'interface Streamlit.
"""

from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

# Services métier
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
from config.settings import MAX_CHECKPOINTS_METEO, RouteResult


@dataclass
class AppConfig:
    """Configuration de l'application avec tous les paramètres utilisateur."""
    # Fichier et dates
    fichier: Optional[bytes]
    date_dep: datetime.date
    heure_dep: datetime.time
    
    # Paramètres de calcul
    vitesse_kmh: float
    intervalle_sec: int
    
    # Profil cycliste
    poids_kg: float
    ref_val: Optional[float]  # FTP ou FC max
    mode: str  # "⚡ Puissance" ou "❤️ FC"
    ftp_fc: Optional[float]
    
    # Enrichissements
    noms_osm: bool
    gemini_key: Optional[str]
    
    # UI
    placeholder_fuseau: object
    placeholder_export: object


@dataclass
class ProcessedData:
    """Résultat du traitement complet des données."""
    # Données géométriques
    points_gpx: list
    checkpoints: list
    profil_data: list
    distance_total_m: float
    d_plus: float
    d_moins: float
    temps_total_s: float
    date_depart: datetime
    heure_arrivee: datetime
    
    # Données météo
    weather_results: list
    weather_analysis: Optional[dict]
    error_weather: bool
    
    # Ascensions
    climbs: list
    
    # Contexte géographique
    water_points: list
    timezone: str
    sunrise_sunset: dict
    uv_pollen: dict
    
    # Métriques calculées
    calories: int
    rideability_score: dict
    
    # Vitesses/temps
    avg_speed_kmh: float
    

# Cache Streamlit pour la météo
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_weather_cached(frozen: tuple, is_past: bool = False, date_str: str = None):
    """Cache des appels API météo."""
    return recuperer_meteo_batch(frozen, is_past=is_past, date_str=date_str)


class DataProcessor:
    """Orchestrateur du traitement des données."""
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def process(self, progress_container) -> Optional[ProcessedData]:
        """
        Traite l'ensemble des données du parcours.
        
        Args:
            progress_container: Conteneur Streamlit pour afficher la progression
            
        Returns:
            ProcessedData ou None en cas d'erreur
        """
        try:
            # 1. Chargement GPX
            points_gpx = self._load_gpx(progress_container)
            if not points_gpx:
                return None
            
            # 2. Récupération données externes (parallèle)
            lat, lon = points_gpx[0].latitude, points_gpx[0].longitude
            timezone, sunrise_sunset, uv_pollen, water_points = self._fetch_external_data(
                lat, lon,
                self.config.date_dep,
                points_gpx,
                progress_container
            )
            self.config.placeholder_fuseau.success(f"🌍 **{timezone}**")
            
            # 3. Calcul du parcours
            route_data = self._calculate_route(points_gpx, progress_container)
            if not route_data:
                return None
            
            # 4. Détection ascensions
            climbs = self._detect_climbs(route_data["profil_data"], points_gpx, 
                                        progress_container)
            
            # 5. Enrichissement OSM (noms des cols)
            if self.config.noms_osm and climbs:
                climbs = self._enrich_osm_names(climbs, progress_container)
            
            # 6. Récupération météo
            weather_results, error_weather = self._fetch_weather(
                route_data["checkpoints"],
                self.config.date_dep,
                progress_container
            )
            
            # 7. Calculs finaux
            date_depart = datetime.combine(self.config.date_dep, self.config.heure_dep)
            
            # Ajout checkpoint d'arrivée
            last_point = points_gpx[-1]
            heure_arrivee = date_depart + timedelta(seconds=route_data["temps_s"])
            route_data["checkpoints"].append({
                "lat": last_point.latitude,
                "lon": last_point.longitude,
                "Cap": route_data["cap"],
                "Heure": heure_arrivee.strftime("%d/%m %H:%M") + " 🏁",
                "Heure_API": heure_arrivee.replace(minute=0, second=0).strftime("%Y-%m-%dT%H:00"),
                "Km": round(route_data["dist_tot"] / 1000, 1),
                "Alt (m)": int(last_point.elevation) if last_point.elevation else 0,
            })
            
            avg_speed = round(
                (route_data["dist_tot"] / 1000) / (route_data["temps_s"] / 3600), 1
            ) if route_data["temps_s"] > 0 else self.config.vitesse_kmh
            
            calories = calculer_calories(
                max(1, self.config.poids_kg - 10),
                route_data["temps_s"],
                route_data["dist_tot"],
                route_data["d_plus"],
                self.config.vitesse_kmh
            )
            
            # Score et analyse météo
            if not error_weather and weather_results:
                weather_analysis = analyser_meteo_detaillee(weather_results, route_data["dist_tot"])
                score = calculer_score(
                    weather_results, climbs,
                    route_data["d_plus"],
                    self.config.vitesse_kmh,
                    self.config.ref_val,
                    self.config.mode,
                    self.config.poids_kg,
                    route_data["dist_tot"]
                )
            else:
                weather_analysis = None
                score = {
                    "total": 5.0,
                    "label": "DONNÉES INDISPONIBLES",
                    "cout_route": 0.0,
                    "cout_meteo": 0.0
                }
            
            return ProcessedData(
                points_gpx=points_gpx,
                checkpoints=route_data["checkpoints"],
                profil_data=route_data["profil_data"],
                distance_total_m=route_data["dist_tot"],
                d_plus=route_data["d_plus"],
                d_moins=route_data["d_moins"],
                temps_total_s=route_data["temps_s"],
                date_depart=date_depart,
                heure_arrivee=heure_arrivee,
                weather_results=weather_results or [],
                weather_analysis=weather_analysis,
                error_weather=error_weather,
                climbs=climbs,
                water_points=water_points,
                timezone=timezone,
                sunrise_sunset=sunrise_sunset,
                uv_pollen=uv_pollen,
                calories=calories,
                rideability_score=score,
                avg_speed_kmh=avg_speed,
            )
            
        except Exception as e:
            import logging
            import traceback
            error_msg = f"Erreur traitement données : {str(e)}"
            logging.error(error_msg)
            logging.error(traceback.format_exc())
            
            # Afficher l'erreur à l'utilisateur
            progress_container.empty()
            st.error(f"❌ **Erreur lors du traitement du parcours:**\n\n{str(e)}\n\n**Stack trace:**\n```\n{traceback.format_exc()}\n```")
            return None
    
    def _load_gpx(self, progress_container) -> Optional[list]:
        """Charge et parse le fichier GPX."""
        if self.config.fichier is None:
            return None
        
        with progress_container.container():
            with st.spinner("📍 Lecture du fichier GPX…"):
                points = parser_gpx(self.config.fichier)
        
        if not points:
            st.error("❌ Fichier GPX vide ou corrompu.")
            return None
        
        return points
    
    def _fetch_external_data(self, lat: float, lon: float, date_dep, points_gpx: list,
                            progress_container) -> tuple:
        """Récupère données externes en parallèle."""
        date_str = date_dep.strftime("%Y-%m-%d")
        coords_tuple = tuple((p.latitude, p.longitude) for p in points_gpx[::5])
        
        with progress_container.container():
            with st.spinner("🌐 Recherche en parallèle : Météo, Soleil, UV, Points d'eau…"):
                with ThreadPoolExecutor(max_workers=4) as executor:
                    future_tz = executor.submit(recuperer_fuseau, lat, lon)
                    future_sun = executor.submit(recuperer_soleil, lat, lon, date_str)
                    future_uv = executor.submit(recuperer_uv_pollen, lat, lon, date_str)
                    future_water = executor.submit(recuperer_points_eau, coords_tuple)
                    
                    timezone = future_tz.result()
                    sunrise_sunset = future_sun.result()
                    uv_pollen = future_uv.result()
                    water_points = future_water.result()
        
        return timezone, sunrise_sunset, uv_pollen, water_points
    
    def _calculate_route(self, points_gpx: list, progress_container) -> Optional[RouteResult]:
        """Calcule le parcours."""
        # Utiliser cache Streamlit avec clé unique
        cache_key = f"parcours_{id(points_gpx)}_{self.config.vitesse_kmh}_{self.config.intervalle_sec}"
        
        if cache_key not in st.session_state:
            with progress_container.container():
                with st.spinner("📐 Calcul du parcours…"):
                    result = calculer_parcours(
                        points_gpx,
                        self.config.vitesse_kmh,
                        datetime.combine(self.config.date_dep, self.config.heure_dep),
                        self.config.intervalle_sec
                    )
            st.session_state[cache_key] = result
        
        return st.session_state[cache_key]
    
    def _detect_climbs(self, profil_data: list, points_gpx: list,
                      progress_container) -> list:
        """Détecte les ascensions."""
        df_profil = pd.DataFrame(profil_data)
        
        with progress_container.container():
            with st.spinner("⛰️ Détection des ascensions…"):
                climbs = detecter_ascensions(df_profil)
        
        # Ajouter coordonnées GPS des ascensions
        if climbs and points_gpx:
            dist_cum = 0.0
            km_to_point = {}
            
            for i in range(1, len(points_gpx)):
                p1, p2 = points_gpx[i - 1], points_gpx[i]
                dist_cum += p1.distance_2d(p2) or 0.0
                km_to_point[round(dist_cum / 1000, 3)] = p2
            
            for climb in climbs:
                # Trouver point le plus proche
                def find_nearest_coords(km_target):
                    if not km_to_point:
                        return None, None
                    nearest_km = min(km_to_point.keys(), key=lambda k: abs(k - km_target))
                    pt = km_to_point[nearest_km]
                    return pt.latitude, pt.longitude
                
                climb["_lat_sommet"], climb["_lon_sommet"] = find_nearest_coords(climb["_sommet_km"])
                climb["_lat_debut"], climb["_lon_debut"] = find_nearest_coords(climb["_debut_km"])
        
        return climbs
    
    def _enrich_osm_names(self, climbs: list, progress_container) -> list:
        """Enrichit les noms des cols via OSM."""
        with progress_container.container():
            with st.spinner("🗺️ Noms des cols (OpenStreetMap)…"):
                climbs = enrichir_cols(climbs, [])  # TODO: passer points_gpx
        
        for climb in climbs:
            climb.setdefault("Nom", "—")
            climb.setdefault("Nom OSM alt", None)
        
        return climbs
    
    def _fetch_weather(self, checkpoints: list, date_dep,
                      progress_container) -> tuple[list, bool]:
        """Récupère les données météo."""
        with progress_container.container():
            with st.spinner("📡 Récupération météo…"):
                # Sous-échantillonnage si trop de checkpoints
                if len(checkpoints) > MAX_CHECKPOINTS_METEO:
                    step = len(checkpoints) // MAX_CHECKPOINTS_METEO
                    cps_sample = checkpoints[::step]
                else:
                    cps_sample = checkpoints
                
                frozen = tuple(
                    (cp["lat"], cp["lon"], cp["Heure_API"])
                    for cp in cps_sample
                )
                is_past = date_dep < __import__('datetime').date.today()
                rep_list = fetch_weather_cached(
                    frozen,
                    is_past=is_past,
                    date_str=date_dep.strftime("%Y-%m-%d")
                )
        
        error_weather = rep_list is None
        if error_weather:
            st.warning("⚠️ Météo indisponible (429). Patientez 1-2 minutes et rechargez.")
            weather_results = [{**cp, "Ciel":"—","temp_val":None,"Pluie":"—","pluie_pct":None,
                               "vent_val":None,"rafales_val":None,"Dir":"—","dir_deg":None,
                               "effet":"—","ressenti":None}
                              for cp in checkpoints]
        else:
            weather_results = enrichir_checkpoints_meteo(checkpoints, rep_list)
        
        return weather_results, error_weather
