"""
core/models/route.py
====================
Dataclasses typées pour les données de parcours, météo et ascensions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Checkpoint:
    """
    Point de contrôle géolocalisé sur le parcours avec données météo enrichies.
    
    Attributes:
        lat: Latitude du point (degrés)
        lon: Longitude du point (degrés)
        cap: Cap magnétique (degrés 0-360)
        heure: Heure locale au format "JJ/MM HH:MM"
        heure_api: Heure pour requête API "YYYY-MM-DDTHH:00"
        km: Distance cumulée en km depuis le départ
        alt_m: Altitude en mètres
        
        # Météo (complétés lors d'appels API)
        ciel: Description météo (ex. "☀️ Clair")
        temp_val: Température en °C
        pluie: Icône de pluie
        pluie_pct: Probabilité de pluie en %
        vent_val: Vitesse du vent en km/h
        rafales_val: Vitesse des rafales en km/h
        dir_label: Direction du vent (N, NO, O, SO, S, SE, E, NE)
        dir_deg: Direction du vent en degrés
        effet: Effet du vent sur le cycliste (Arrière, Travers, Avant)
        ressenti: Température ressentie en °C
    """
    # Géolocalisation et temporalité
    lat: float
    lon: float
    cap: float
    heure: str
    heure_api: str
    km: float
    alt_m: int
    
    # Météo (rempli après appel API)
    ciel: str = "—"
    temp_val: Optional[float] = None
    pluie: str = "—"
    pluie_pct: Optional[int] = None
    vent_val: Optional[float] = None
    rafales_val: Optional[float] = None
    dir_label: str = "—"
    dir_deg: Optional[float] = None
    effet: str = "—"
    ressenti: Optional[int] = None


@dataclass
class Ascension:
    """
    Une ascension (col, côte) détectée sur le parcours avec catégorisation UCI.
    
    Attributes:
        # Catégorisation
        categorie: Catégorie UCI ("🔴 HC", "🟠 1ère Cat.", etc.)
        score_uci: Score UCI calculé = (D+ × pente moy.) / 100
        
        # Position et géométrie
        depart_km: Distance du départ en km
        sommet_km: Distance du sommet en km
        longueur: Longueur formatée (ex. "5.2 km")
        denivele: Dénivelé formaté (ex. "450 m")
        pente_moy: Pente moyenne formatée (ex. "8.6%")
        pente_max: Pente maximale formatée (ex. "12.3%")
        alt_sommet: Altitude du sommet (ex. "2108 m")
        
        # Données OSM (Open Street Map)
        nom: Nom du col (défaut: "—")
        nom_osm_alt: Altitude du col selon OSM
        
        # Coordonnées GPS
        lat_sommet: Latitude du sommet
        lon_sommet: Longitude du sommet
        lat_debut: Latitude du début de l'ascension
        lon_debut: Longitude du début de l'ascension
        
        # Effort estimé (calculé après)
        temps_col: Durée estimée (ex. "45 min")
        arrivee_sommet: Heure d'arrivée au sommet
        puissance: Puissance estimée (ex. "280 W")
        effort_val: Valeur d'effort (VAM, watts, etc.)
        zone: Zone d'entraînement (Z1-Z6)
        effort: Label d'effort formaté
    """
    # Catégorisation
    categorie: str
    score_uci: float
    
    # Position et géométrie
    depart_km: float
    sommet_km: float
    longueur: str
    denivele: str
    pente_moy: str
    pente_max: str
    alt_sommet: str
    
    # OSM (optionnel)
    nom: str = "—"
    nom_osm_alt: Optional[int] = None
    
    # Coordonnées GPS (optionnel)
    lat_sommet: Optional[float] = None
    lon_sommet: Optional[float] = None
    lat_debut: Optional[float] = None
    lon_debut: Optional[float] = None
    
    # Effort estimé (calculé après)
    temps_col: str = "—"
    arrivee_sommet: str = "—"
    puissance: str = "—"
    effort_val: str = "—"
    zone: str = "—"
    effort: str = "—"


@dataclass
class ParcoursStat:
    """
    Statistiques globales d'un parcours cycliste.
    
    Attributes:
        dist_tot: Distance totale en mètres
        d_plus: Dénivelé positif cumulé en mètres
        d_moins: Dénivelé négatif cumulé en mètres
        temps_s: Durée totale en secondes
        vit_moy_reelle: Vitesse moyenne réelle en km/h
        heure_arr: Heure d'arrivée estimée
        calories: Calories totales brûlées
    """
    dist_tot: float          # mètres
    d_plus: float           # mètres
    d_moins: float          # mètres
    temps_s: float          # secondes
    vit_moy_reelle: float   # km/h
    heure_arr: datetime
    calories: int
