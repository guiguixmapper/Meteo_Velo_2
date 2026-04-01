from .climbing_service import (
    detecter_ascensions, categoriser_uci, estimer_watts, estimer_fc,
    estimer_temps_col, calculer_calories, get_zone, zones_actives,
)
from .nutrition_service import calculer_hydratation, calculer_glucides
# route_service importé à la demande (dépend de gpxpy)
