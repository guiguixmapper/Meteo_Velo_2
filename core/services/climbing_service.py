"""
core/services/climbing_service.py
==================================
Détection et catégorisation des ascensions — algorithme slope-first.
Logique métier pure, sans dépendance UI.
"""

import math
import pandas as pd
from config.settings import (
    LISSAGE_F, FENETRE_PENTE_M, SEUIL_DEBUT, SEUIL_FIN,
    MIN_RUN_M, MAX_DESCENTE_FUSION_M, D_PLUS_MIN,
    DISTANCE_MIN_M, PENTE_MIN_CAT, SEUILS_UCI, COULEURS_CAT,
    ZONES_PUISSANCE, ZONES_FC,
)


# ==============================================================================
# ZONES
# ==============================================================================

def zones_actives(mode: str) -> list:
    return ZONES_PUISSANCE if mode == "⚡ Puissance" else ZONES_FC


def get_zone(valeur: float, ref: float, zones: list) -> tuple:
    if ref <= 0:
        return 1, "Z1 Récup", "#94a3b8"
    ratio = valeur / ref
    for bas, haut, num, lbl, coul in zones:
        if bas <= ratio < haut:
            return num, lbl, coul
    return 6, "Z6 Anaérobie", "#ef4444"


# ==============================================================================
# ESTIMATION EFFORT
# ==============================================================================

def estimer_watts(pente_pct: float, vitesse_plat_kmh: float, poids_kg: float = 75) -> int:
    g              = 9.81
    facteur        = 1.0 + pente_pct * 0.10
    vitesse_montee = max(5.0, vitesse_plat_kmh / facteur)
    vm             = vitesse_montee / 3.6
    angle          = math.atan(pente_pct / 100)
    return max(0, int(
        poids_kg * g * math.sin(angle) * vm +
        poids_kg * g * 0.004 * vm
    ))


def estimer_fc(watts: float, ftp: float, fc_max: float, fc_repos: float = 50) -> int | None:
    if ftp <= 0 or fc_max <= 0:
        return None
    ratio = min(watts / (ftp / 0.85), 0.97)
    fc    = fc_repos + ratio * (fc_max - fc_repos)
    return int(min(fc_max - 3, max(fc_repos, fc)))


def calculer_vam(ftp_w: float, poids_kg: float) -> float:
    """
    Calcule la VAM (Vélocité Ascensionale Moyenne) en m/h depuis le FTP.

    Formule empirique calibrée sur des données réelles cyclistes :
        VAM = FTP_wkg × 170 + 50
    
    Exemples :
        2.5 W/kg → 475 m/h  (débutant)
        3.0 W/kg → 560 m/h  (loisir)
        3.5 W/kg → 645 m/h  (cyclosportif)
        4.0 W/kg → 730 m/h  (bon niveau)
        4.5 W/kg → 815 m/h  (compétiteur)
        5.0 W/kg → 900 m/h  (élite)
    """
    if poids_kg <= 0 or ftp_w <= 0:
        return 600.0  # valeur par défaut cycliste moyen
    ftp_wkg = ftp_w / poids_kg
    # Formule calibrée sur données réelles (Alpe d'Huez, cols UCI) :
    # VAM = W/kg × 240
    # Exemples : 3 W/kg → 720 m/h (~89min AdH), 4 W/kg → 960 m/h (~67min AdH)
    vam = ftp_wkg * 240
    return round(max(300, min(1800, vam)), 0)  # bornes réalistes


def niveau_cycliste(vam: float) -> str:
    """Retourne le label de niveau selon la VAM."""
    if vam < 500:  return "🟦 Débutant"
    if vam < 650:  return "🟩 Loisir"
    if vam < 800:  return "🟨 Cyclosportif"
    if vam < 1000: return "🟧 Bon niveau"
    if vam < 1200: return "🟥 Compétiteur"
    return               "⭐ Élite"


def estimer_temps_col_vam(d_plus_m: float, dist_km: float,
                          ftp_w: float, poids_kg: float) -> dict:
    """
    Estime le temps d'ascension via la VAM (modèle réaliste).

    Returns dict avec :
        - mins      : temps en minutes
        - vam       : VAM utilisée (m/h)
        - vit_moy   : vitesse moyenne en montée (km/h)
        - niveau    : label niveau cycliste
        - vs_simple : delta vs l'ancienne méthode simpliste (minutes)
    """
    vam = calculer_vam(ftp_w, poids_kg)
    # Temps = D+ / VAM en heures → minutes
    temps_h   = d_plus_m / vam
    mins      = int(temps_h * 60)
    # Vitesse moyenne = distance / temps
    vit_moy   = round(dist_km / temps_h, 1) if temps_h > 0 else 0

    return dict(
        mins=max(1, mins),
        vam=int(vam),
        vit_moy=vit_moy,
        niveau=niveau_cycliste(vam),
    )


def estimer_temps_col(dist_km: float, pente_moy_pct: float, vitesse_plat_kmh: float) -> tuple:
    """Méthode simpliste conservée pour compatibilité (utilisée pour l'heure d'arrivée globale)."""
    facteur        = 1.0 + pente_moy_pct * 0.10
    vitesse_montee = max(5.0, vitesse_plat_kmh / facteur)
    return int((dist_km / vitesse_montee) * 60), round(vitesse_montee, 1)


def calculer_calories(poids_cycliste_kg: float, duree_sec: float,
                      dist_m: float, d_plus_m: float, vitesse_kmh: float) -> int:
    if poids_cycliste_kg <= 0 or duree_sec <= 0:
        return 0
    duree_h       = duree_sec / 3600
    pente_globale = (d_plus_m / dist_m * 100) if dist_m > 0 else 0
    if vitesse_kmh < 16:   met = 6.0
    elif vitesse_kmh < 20: met = 8.0
    elif vitesse_kmh < 25: met = 10.0
    elif vitesse_kmh < 30: met = 12.0
    else:                  met = 14.0
    return int(min(met + pente_globale * 0.8, 18.0) * poids_cycliste_kg * duree_h)


# ==============================================================================
# CATÉGORISATION UCI
# ==============================================================================

def categoriser_uci(distance_m: float, d_plus: float) -> tuple:
    if distance_m < DISTANCE_MIN_M or d_plus < D_PLUS_MIN:
        return None, 0.0
    pente_moy = (d_plus / distance_m) * 100
    if pente_moy < PENTE_MIN_CAT:
        return None, 0.0
    score = (d_plus * pente_moy) / 100
    for label, seuil in SEUILS_UCI.items():
        if score >= seuil:
            return label, round(score, 1)
    return None, 0.0


# ==============================================================================
# DÉTECTION INTERNE
# ==============================================================================

def _lisser(alts: list, f: int = LISSAGE_F) -> list:
    demi, n, r = f // 2, len(alts), []
    for i in range(n):
        s, e = max(0, i - demi), min(n, i + demi + 1)
        r.append(sum(alts[s:e]) / (e - s))
    return r


def _calc_pentes(dists: list, alts: list, fenetre_m: float = FENETRE_PENTE_M) -> list:
    n      = len(dists)
    pentes = [0.0] * n
    for i in range(1, n):
        for j in range(i - 1, -1, -1):
            dist_m = (dists[i] - dists[j]) * 1000
            if dist_m >= fenetre_m:
                pentes[i] = (alts[i] - alts[j]) / dist_m * 100
                break
            if j == 0:
                dist_m = (dists[i] - dists[0]) * 1000
                if dist_m > 0:
                    pentes[i] = (alts[i] - alts[0]) / dist_m * 100
    return pentes


def _detecter_runs(dists: list, alts: list, pentes: list) -> list:
    n, runs, debut = len(dists), [], None
    for i in range(n):
        if pentes[i] >= SEUIL_DEBUT:
            if debut is None:
                debut = i
        else:
            if debut is not None:
                dist_run = (dists[i - 1] - dists[debut]) * 1000
                if dist_run >= MIN_RUN_M:
                    runs.append((debut, i - 1))
                debut = None
    if debut is not None:
        dist_run = (dists[-1] - dists[debut]) * 1000
        if dist_run >= MIN_RUN_M:
            runs.append((debut, n - 1))
    return runs


def _fusionner_runs(runs: list, dists: list, alts: list) -> list:
    if not runs:
        return []
    fusionnes = [list(runs[0])]
    for debut, fin in runs[1:]:
        prev_debut, prev_fin = fusionnes[-1]
        alt_vallee = min(alts[prev_fin:debut + 1])
        descente   = alts[prev_fin] - alt_vallee
        if descente < MAX_DESCENTE_FUSION_M:
            fusionnes[-1][1] = fin
        else:
            fusionnes.append([debut, fin])
    return [tuple(r) for r in fusionnes]


def _pente_max(dists: list, alts: list, i0: int, i1: int, fenetre_m: float = 100.0) -> float:
    pm = 0.0
    for i in range(i0 + 1, i1 + 1):
        for j in range(i - 1, i0 - 1, -1):
            dist_m = (dists[i] - dists[j]) * 1000
            if dist_m >= fenetre_m:
                p = ((alts[i] - alts[j]) / dist_m) * 100
                if 0 < p <= 40:
                    pm = max(pm, p)
                break
    return round(pm, 1)


# ==============================================================================
# FONCTION PRINCIPALE
# ==============================================================================

def detecter_ascensions(df: pd.DataFrame) -> list:
    """
    Détecte et catégorise les ascensions dans un profil altimétrique.
    Retourne une liste de dicts compatibles avec l'UI existante.
    """
    if df.empty or len(df) < 5:
        return []

    alts_raw = df["Altitude (m)"].tolist()
    dists    = df["Distance (km)"].tolist()
    alts     = _lisser(alts_raw)
    pentes   = _calc_pentes(dists, alts)
    runs     = _detecter_runs(dists, alts, pentes)
    runs     = _fusionner_runs(runs, dists, alts)

    ascensions = []
    for (i0, i1) in runs:
        dk = dists[i1] - dists[i0]
        dp = alts[i1] - alts[i0]
        if dk <= 0 or dp < D_PLUS_MIN:
            continue
        cat, score = categoriser_uci(dk * 1000, dp)
        if cat is None:
            continue
        pm = (dp / (dk * 1000)) * 100
        ascensions.append({
            "Catégorie":   cat,
            "Départ (km)": round(dists[i0], 1),
            "Sommet (km)": round(dists[i1], 1),
            "Longueur":    f"{round(dk, 1)} km",
            "Dénivelé":    f"{int(dp)} m",
            "Pente moy.":  f"{round(pm, 1)} %",
            "Pente max":   f"{_pente_max(dists, alts_raw, i0, i1)} %",
            "Alt. sommet": f"{int(alts_raw[i1])} m",
            "Score UCI":   score,
            "_debut_km":   dists[i0],
            "_sommet_km":  dists[i1],
            "_pente_moy":  pm,
        })

    ascensions.sort(key=lambda x: x["_debut_km"])
    return ascensions
