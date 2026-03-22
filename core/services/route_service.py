"""
core/services/route_service.py
Version robuste : aucune donnée météo manquante ne peut faire planter l'app
"""

import gpxpy
from datetime import datetime, timedelta
from core.utils.geo import calculer_cap, direction_vent_relative


# ─────────────────────────────────────────────────────────────
# GPX
# ─────────────────────────────────────────────────────────────

def parser_gpx(data: bytes):
    try:
        gpx = gpxpy.parse(data)
        return [p for t in gpx.tracks for s in t.segments for p in s.points]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────
# PARCOURS
# ─────────────────────────────────────────────────────────────

def calculer_parcours(points, vitesse_kmh, date_depart, intervalle_sec):
    checkpoints = []
    profil = []

    dist = d_plus = d_moins = temps = 0.0
    vms = vitesse_kmh * 1000 / 3600
    prochain = 0
    cap = 0

    for i in range(1, len(points)):
        p1, p2 = points[i - 1], points[i]
        d = p1.distance_2d(p2) or 0
        alt1 = p1.elevation or 0
        alt2 = p2.elevation or 0
        diff = alt2 - alt1

        if diff > 0:
            d_plus += diff
        else:
            d_moins += abs(diff)

        dist += d
        temps += (d + max(0, diff) * 10) / vms

        profil.append({
            "Distance (km)": round(dist / 1000, 3),
            "Altitude (m)": alt2
        })

        if temps >= prochain:
            h = date_depart + timedelta(seconds=temps)
            cap = calculer_cap(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
            checkpoints.append({
                "lat": p2.latitude,
                "lon": p2.longitude,
                "Cap": cap,
                "Heure": h.strftime("%d/%m %H:%M"),
                "Heure_API": h.replace(minute=0, second=0).strftime("%Y-%m-%dT%H:00"),
                "Km": round(dist / 1000, 1),
                "Alt (m)": int(alt2)
            })
            prochain += intervalle_sec

    return {
        "dist_tot": dist,
        "d_plus": d_plus,
        "d_moins": d_moins,
        "temps_s": temps,
        "cap": cap,
        "checkpoints": checkpoints,
        "profil_data": profil
    }


# ─────────────────────────────────────────────────────────────
# MÉTÉO
# ─────────────────────────────────────────────────────────────

def enrichir_checkpoints_meteo(checkpoints, meteo):
    from infrastructure.open_meteo_client import extraire_meteo

    res = []
    for i, cp in enumerate(checkpoints):
        m = extraire_meteo(meteo[i] if i < len(meteo) else {}, cp["Heure_API"])
        if m.get("dir_deg") is not None:
            m["effet"] = direction_vent_relative(cp["Cap"], m["dir_deg"])
        cp.update(m)
        res.append(cp)
    return res


def analyser_meteo_detaillee(resultats, dist_tot):
    valides = [c for c in resultats if c.get("temp_val") is not None]
    if not valides:
        return None

    pluie = [c for c in valides if (c.get("pluie_pct") or 0) >= 50]
    pct_pluie = round(len(pluie) / len(valides) * 100)

    vent = {"Face": 0, "Dos": 0, "Côté": 0}
    for c in valides:
        e = c.get("effet", "")
        if "Face" in e:
            vent["Face"] += 1
        elif "Dos" in e:
            vent["Dos"] += 1
        elif "Côté" in e:
            vent["Côté"] += 1

    total = len(valides)
    return {
        "pct_pluie": pct_pluie,
        "pct_face": round(vent["Face"] / total * 100),
        "pct_dos": round(vent["Dos"] / total * 100),
        "pct_cote": round(vent["Côté"] / total * 100),
        "n_valides": total
    }


# ─────────────────────────────────────────────────────────────
# SCORE — DÉFINITIVEMENT SÉCURISÉ
# ─────────────────────────────────────────────────────────────

def calculer_score(resultats, ascensions, d_plus, vitesse, ref_val, mode, poids, dist_tot):
    dist_km = dist_tot / 1000
    cout_route = (dist_km / 200) + (d_plus / 2000)

    aero = pluie = temp = 0.0
    n = max(1, len(resultats))

    for c in resultats:
        v = c.get("vent_val") if c.get("vent_val") is not None else 0
        p = c.get("pluie_pct") if c.get("pluie_pct") is not None else 0
        t = c.get("temp_val") if c.get("temp_val") is not None else 20
        e = c.get("effet", "")

        temp += abs(t - 20) / 10
        pluie += (p / 100) * 3

        if "Face" in e:
            aero += (v ** 2) / 300
        elif "Côté" in e:
            aero += (v ** 2) / 600
        elif "Dos" in e:
            aero -= (v ** 2) / 400

    score = 10 - cout_route - (aero + pluie + temp) / n
    score = max(0, min(10, score))

    label = (
        "CONDITIONS IDÉALES" if score >= 8.5 else
        "TRÈS BONNE SORTIE" if score >= 7 else
        "SORTIE RUGUEUSE" if score >= 5 else
        "CONDITIONS DIFFICILES" if score >= 3 else
        "ENFER ABSOLU"
    )

    return {
        "total": round(score, 1),
        "label": label,
        "cout_route": round(cout_route, 1),
        "cout_meteo": round((aero + pluie + temp) / n, 1)
    }
