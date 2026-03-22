"""
core/utils/geo.py
=================
Calculs géographiques purs — aucune dépendance UI.
"""

import math


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en mètres entre deux points GPS."""
    R  = 6371000
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a  = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calculer_cap(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Cap en degrés (0-360) entre deux points GPS."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def direction_vent_relative(cap: float, dir_vent: float) -> str:
    """Effet ressenti du vent selon le cap du cycliste."""
    diff = (dir_vent - cap) % 360
    if diff <= 45 or diff >= 315:  return "⬇️ Face"
    elif 135 <= diff <= 225:       return "⬆️ Dos"
    elif 45 < diff < 135:          return "↙️ Côté (D)"
    else:                          return "↘️ Côté (G)"


def wind_chill(temp_c: float, vent_kmh: float) -> int | None:
    """Indice de refroidissement éolien (formule NOAA)."""
    if temp_c is None or vent_kmh is None:
        return None
    if temp_c > 10 or vent_kmh <= 4.8:
        return None
    return round(
        13.12 + 0.6215 * temp_c
        - 11.37 * (vent_kmh ** 0.16)
        + 0.3965 * temp_c * (vent_kmh ** 0.16)
    )


def label_wind_chill(ressenti: int | None) -> str:
    """Label coloré selon l'indice de ressenti."""
    if ressenti is None:  return "—"
    if ressenti <= -40:   return f"🟣 {ressenti}°C (Danger extrême)"
    if ressenti <= -27:   return f"🔴 {ressenti}°C (Très dangereux)"
    if ressenti <= -10:   return f"🟠 {ressenti}°C (Dangereux)"
    if ressenti <= 0:     return f"🟡 {ressenti}°C (Froid intense)"
    return                       f"🔵 {ressenti}°C (Frais)"
