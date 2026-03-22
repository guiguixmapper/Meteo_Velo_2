"""
core/models/route.py
====================
Dataclasses pour les données de parcours.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Checkpoint:
    """Point de contrôle sur le parcours avec données météo."""
    lat:       float
    lon:       float
    cap:       float
    heure:     str
    heure_api: str
    km:        float
    alt_m:     int
    # Météo (rempli après appel API)
    ciel:       str   = "—"
    temp_val:   float = None
    pluie:      str   = "—"
    pluie_pct:  int   = None
    vent_val:   float = None
    rafales_val: float = None
    dir_label:  str   = "—"
    dir_deg:    float = None
    effet:      str   = "—"
    ressenti:   int   = None


@dataclass
class Ascension:
    """Une ascension détectée sur le parcours."""
    categorie:   str
    depart_km:   float
    sommet_km:   float
    longueur:    str
    denivele:    str
    pente_moy:   str
    pente_max:   str
    alt_sommet:  str
    score_uci:   float
    # Clés internes
    _debut_km:   float = 0.0
    _sommet_km:  float = 0.0
    _pente_moy:  float = 0.0
    # OSM (optionnel)
    nom:         str   = "—"
    nom_osm_alt: int   = None
    # Coordonnées GPS
    lat_sommet:  float = None
    lon_sommet:  float = None
    lat_debut:   float = None
    lon_debut:   float = None
    # Effort estimé (calculé après)
    temps_col:      str = "—"
    arrivee_sommet: str = "—"
    puissance:      str = "—"
    effort_val:     str = "—"
    zone:           str = "—"
    effort:         str = "—"


@dataclass
class ParcoursStat:
    """Statistiques globales du parcours."""
    dist_tot:      float  # mètres
    d_plus:        float  # mètres
    d_moins:       float  # mètres
    temps_s:       float  # secondes
    vit_moy_reelle: float  # km/h
    heure_arr:     datetime
    calories:      int
