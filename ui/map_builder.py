"""
ui/map_builder.py
==================
Carte Folium interactive — version allégée pour chargement rapide.
"""

import folium
from config.settings import COULEURS_CAT


# ==============================================================================
# HELPERS ICÔNES SIMPLIFIÉS
# ==============================================================================

def _rond(emoji: str, bg: str, size: int = 30, font: int = 14) -> str:
    return (
        f'<div style="background:{bg};color:white;border-radius:50%;'
        f'width:{size}px;height:{size}px;display:flex;align-items:center;'
        f'justify-content:center;font-size:{font}px;border:2px solid white;'
        f'box-shadow:0 2px 6px rgba(0,0,0,0.35);line-height:1;">{emoji}</div>'
    )


def _couleur_temp(t: float) -> str:
    if t < 5:   return "#5E5CE6"
    if t < 15:  return "#007AFF"
    if t < 22:  return "#34C759"
    if t < 30:  return "#FF9500"
    return              "#FF3B30"


def _couleur_eau(type_eau: str) -> str:
    return {"fontaine": "#0ea5e9", "source": "#06b6d4", "borne": "#3b82f6"}.get(type_eau, "#32ADE6")


EMOJI_EAU = {"fontaine": "💧", "source": "💧", "borne": "💧", "eau": "💧"}


# ==============================================================================
# FONCTION PRINCIPALE – VERSION OPTIMISÉE
# ==============================================================================

def creer_carte(points_gpx, resultats, ascensions, points_eau, tiles, attr):
    if not points_gpx:
        return folium.Map(location=[46.5, 2.5], zoom_start=6)

    # Centre sur le milieu du parcours
    centre_lat = sum(p.latitude for p in points_gpx) / len(points_gpx)
    centre_lon = sum(p.longitude for p in points_gpx) / len(points_gpx)

    carte = folium.Map(
        location=[centre_lat, centre_lon],
        zoom_start=11,
        tiles=tiles,
        attr=attr,
        prefer_canvas=True   # ← gain perf canvas
    )

    fg_trace = folium.FeatureGroup(name="🚴 Tracé", show=True)
    fg_cols  = folium.FeatureGroup(name="🏔️ Cols",  show=True)
    fg_eau   = folium.FeatureGroup(name="💧 Eau",   show=True)
    fg_meteo = folium.FeatureGroup(name="🌤️ Météo (checkpoints)", show=False)

    # ── Tracé principal ultra-simplifié ──────────────────────────────────────
    # On garde TOUS les points pour la précision, mais UN seul PolyLine
    trace_coords = [[p.latitude, p.longitude] for p in points_gpx]
    folium.PolyLine(
        trace_coords,
        color="#3B82F6",       # bleu classique
        weight=5,
        opacity=0.9,
        tooltip="Tracé GPX"
    ).add_to(fg_trace)

    # ── Tracé coloré par pente (downsamplé fortement) ────────────────────────
    STEP = 5               # 1 point sur 5 → grosse économie
    points_light = points_gpx[::STEP]

    current_color = None
    current_segment = []

    for i in range(1, len(points_light)):
        p1, p2 = points_light[i-1], points_light[i]
        d = p1.distance_2d(p2) or 0
        if d == 0:
            continue
        slope = ((p2.elevation - p1.elevation) / d * 100) if p1.elevation and p2.elevation else 0

        color = "#34C759" if slope <= 3 else \
                "#FFCC00" if slope <= 7 else \
                "#FF9500" if slope <= 10 else "#FF3B30"

        if color != current_color and current_segment:
            folium.PolyLine(
                current_segment,
                color=current_color,
                weight=5,
                opacity=0.75
            ).add_to(fg_trace)
            current_segment = []

        current_color = color
        current_segment.append([p2.latitude, p2.longitude])

    if current_segment:
        folium.PolyLine(current_segment, color=current_color, weight=5, opacity=0.75).add_to(fg_trace)

    # ── Cols ─────────────────────────────────────────────────────────────────
    for asc in ascensions:
        lat_s = asc.get("_lat_sommet")
        lon_s = asc.get("_lon_sommet")
        if lat_s is None or lon_s is None:
            continue
        cat   = asc["Catégorie"]
        nom   = asc.get("Nom", "—")
        coul  = COULEURS_CAT.get(cat, "#94a3b8")
        label = nom if nom != "—" else cat.split()[0]
        folium.Marker(
            [lat_s, lon_s],
            tooltip=f"▲ {label} — {asc['Alt. sommet']}",
            icon=folium.DivIcon(html=_rond("▲", coul, size=28, font=12),
                                icon_size=(28,28), icon_anchor=(14,14)),
        ).add_to(fg_cols)

    # ── Points d'eau ─────────────────────────────────────────────────────────
    for pt in points_eau:
        type_eau = pt.get("type", "eau")
        coul     = _couleur_eau(type_eau)
        emoji    = EMOJI_EAU.get(type_eau, "💧")
        nom      = pt.get("nom", "Point d'eau")
        folium.Marker(
            [pt["lat"], pt["lon"]],
            tooltip=f"{emoji} {nom}",
            icon=folium.DivIcon(html=_rond(emoji, coul, size=26, font=13),
                                icon_size=(26,26), icon_anchor=(13,13)),
        ).add_to(fg_eau)

    # ── Checkpoints météo (simplifiés) ───────────────────────────────────────
    for cp in resultats[:30]:  # limite à 30 pour ne pas alourdir
        t = cp.get("temp_val")
        if t is None:
            continue
        coul = _couleur_temp(t)
        folium.Marker(
            [cp["lat"], cp["lon"]],
            tooltip=f"{cp['Heure']} – {t}°",
            icon=folium.DivIcon(html=_rond(f"{int(t)}", coul, size=24, font=11),
                                icon_size=(24,24), icon_anchor=(12,12)),
        ).add_to(fg_meteo)

    # Ajout des layers
    for fg in [fg_trace, fg_cols, fg_eau, fg_meteo]:
        fg.add_to(carte)

    folium.LayerControl(collapsed=False, position="topright").add_to(carte)

    return carte
