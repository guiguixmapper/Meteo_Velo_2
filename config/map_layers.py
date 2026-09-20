"""Fonds de carte IGN et fonds de secours pour Folium."""

from __future__ import annotations

IGN_WMTS_BASE = "https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0"
IGN_ATTRIBUTION = "© IGN / Géoplateforme"

FONDS_CARTE = {
    "🗺️ Plan IGN (Standard)": (
        f"{IGN_WMTS_BASE}&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2"
        "&STYLE=normal&FORMAT=image/png&TILEMATRIXSET=PM"
        "&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}",
        IGN_ATTRIBUTION,
    ),
    "🏔️ IGN Topo 1:25 000 (SCAN 25)": (
        f"{IGN_WMTS_BASE}&LAYER=GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN25TOUR"
        "&STYLE=normal&FORMAT=image/jpeg&TILEMATRIXSET=PM"
        "&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}",
        IGN_ATTRIBUTION,
    ),
    "📸 Photos aériennes IGN": (
        f"{IGN_WMTS_BASE}&LAYER=ORTHOIMAGERY.ORTHOPHOTOS"
        "&STYLE=normal&FORMAT=image/jpeg&TILEMATRIXSET=PM"
        "&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}",
        IGN_ATTRIBUTION,
    ),
    "🗺️ CartoDB Positron (épuré)": ("CartoDB positron", None),
    "🌍 OpenStreetMap (classique)": ("OpenStreetMap", None),
    "🏔️ OpenTopoMap (relief)": (
        "https://{s}.tile.opentopemap.org/{z}/{x}/{y}.png",
        "Map data © OpenStreetMap contributors, SRTM | Map style © OpenTopoMap (CC-BY-SA)",
    ),
}
