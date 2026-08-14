"""
core/services/climbing_service.py
==================================
Détection et catégorisation des ascensions — algorithme slope-first.
Estimation de l'effort physique, VAM, calories brûlées.
Logique métier pure, sans dépendance UI.
"""

from typing import Optional, Union
import math
import pandas as pd
from config.settings import (
    LISSAGE_F, FENETRE_PENTE_M, SEUIL_DEBUT, SEUIL_FIN,
    MIN_RUN_M, MAX_DESCENTE_FUSION_M, D_PLUS_MIN,
    DISTANCE_MIN_M, PENTE_MIN_CAT, SEUILS_UCI, COULEURS_CAT,
    ZONES_PUISSANCE, ZONES_FC, Zone,
)


# ==============================================================================
# ZONES D'ENTRAÎNEMENT
# ==============================================================================

def zones_actives(mode: str) -> list[Zone]:
    """
    Retourne la liste des zones d'entraînement selon le mode.
    
    Args:
        mode: "⚡ Puissance" ou "❤️ FC"
        
    Returns:
        Liste de tuples (ratio_min, ratio_max, num, label, color)
    """
    return ZONES_PUISSANCE if mode == "⚡ Puissance" else ZONES_FC


def get_zone(valeur: float, ref: float, zones: list[Zone]) -> tuple[int, str, str]:
    """
    Détermine la zone d'entraînement pour une valeur donnée.
    
    Args:
        valeur: Valeur mesurée (watts, FC, etc.)
        ref: Valeur de référence (FTP, FC max, etc.)
        zones: Liste des zones d'entraînement
        
    Returns:
        Tuple (numéro_zone, label_zone, couleur_hex)
    """
    if ref <= 0:
        return 1, "Z1 Récup", "#94a3b8"
    
    ratio = valeur / ref
    for ratio_min, ratio_max, num, label, color in zones:
        if ratio_min <= ratio < ratio_max:
            return num, label, color
    
    return 6, "Z6 Anaérobie", "#ef4444"


# ==============================================================================
# ESTIMATION DE L'EFFORT
# ==============================================================================

def estimer_watts(
    pente_pct: float,
    vitesse_plat_kmh: float,
    poids_kg: float = 75,
) -> int:
    """
    Estime la puissance requise en montée via formule biomécanique.
    
    Modèle physique :
        - Poids × gravité × sin(angle) × vitesse (composante gravitationnelle)
        - Poids × gravité × coefficient_roulement × vitesse (résistance au roulement)
    
    Args:
        pente_pct: Pente moyenne en %
        vitesse_plat_kmh: Vitesse estimée en plat (km/h)
        poids_kg: Poids du cycliste (défaut 75 kg)
        
    Returns:
        Puissance estimée en watts
    """
    gravity = 9.81
    # Facteur de ralentissement : 10% de pente → vitesse ÷ 1.1
    factor = 1.0 + pente_pct * 0.10
    climb_speed = max(5.0, vitesse_plat_kmh / factor)
    # Conversion km/h → m/s
    velocity_ms = climb_speed / 3.6
    # Angle en radians
    angle_rad = math.atan(pente_pct / 100)
    
    # Puissance = m × g × sin(θ) × v + m × g × Crr × v
    return max(0, int(
        poids_kg * gravity * math.sin(angle_rad) * velocity_ms +
        poids_kg * gravity * 0.004 * velocity_ms
    ))


def estimer_fc(
    watts: float,
    ftp: float,
    fc_max: float,
    fc_repos: float = 50,
) -> Optional[int]:
    """
    Estime la fréquence cardiaque à partir de la puissance.
    
    Formule :
        FC = FC_repos + (watts / (FTP / 0.85)) × (FC_max - FC_repos)
    
    Args:
        watts: Puissance estimée (W)
        ftp: Seuil fonctionnel de puissance (W)
        fc_max: Fréquence cardiaque maximale (bpm)
        fc_repos: Fréquence cardiaque de repos (défaut 50 bpm)
        
    Returns:
        FC estimée ou None si paramètres invalides
    """
    if ftp <= 0 or fc_max <= 0:
        return None
    
    ratio = min(watts / (ftp / 0.85), 0.97)
    fc = fc_repos + ratio * (fc_max - fc_repos)
    return int(min(fc_max - 3, max(fc_repos, fc)))


def calculer_vam(ftp_w: float, poids_kg: float) -> float:
    """
    Calcule la VAM (Vélocité Ascensionnelle Moyenne) en m/h depuis le FTP.
    
    Formule empirique calibrée sur données réelles (Alpe d'Huez, cols UCI) :
        VAM = (FTP_W / poids_kg) × 240 m/h
    
    Exemples :
        - 2.5 W/kg → 600 m/h  (débutant)
        - 3.0 W/kg → 720 m/h  (loisir)
        - 3.5 W/kg → 840 m/h  (cyclosportif)
        - 4.0 W/kg → 960 m/h  (bon niveau)
        - 5.0 W/kg → 1200 m/h (élite)
    
    Args:
        ftp_w: Seuil fonctionnel de puissance en watts
        poids_kg: Poids du cycliste en kg
        
    Returns:
        VAM estimée en m/h (bornes : 300-1800 m/h)
    """
    if poids_kg <= 0 or ftp_w <= 0:
        return 600.0  # Défaut : cycliste moyen
    
    ftp_wkg = ftp_w / poids_kg
    vam = ftp_wkg * 240
    # Bornes réalistes
    return float(round(max(300, min(1800, vam)), 0))


def niveau_cycliste(vam: float) -> str:
    """
    Retourne le label de niveau selon la VAM.
    
    Args:
        vam: VAM en m/h
        
    Returns:
        Label de niveau (Débutant à Élite)
    """
    if vam < 500:
        return "🟦 Débutant"
    if vam < 650:
        return "🟩 Loisir"
    if vam < 800:
        return "🟨 Cyclosportif"
    if vam < 1000:
        return "🟧 Bon niveau"
    if vam < 1200:
        return "🟥 Compétiteur"
    return "⭐ Élite"


def estimer_temps_col_vam(
    d_plus_m: float,
    dist_km: float,
    ftp_w: float,
    poids_kg: float,
) -> dict:
    """
    Estime le temps d'ascension via la VAM (modèle réaliste).
    
    Formule : temps_h = dénivelé_m / VAM_m_h
    
    Args:
        d_plus_m: Dénivelé positif en mètres
        dist_km: Distance horizontale en km
        ftp_w: Seuil fonctionnel de puissance (W)
        poids_kg: Poids du cycliste (kg)
        
    Returns:
        Dict avec :
            - mins (int): Durée en minutes
            - vam (int): VAM utilisée (m/h)
            - vit_moy (float): Vitesse moyenne en montée (km/h)
            - niveau (str): Label de niveau cycliste
    """
    vam = calculer_vam(ftp_w, poids_kg)
    # Temps en heures
    temps_h = d_plus_m / vam if vam > 0 else 0
    mins = int(temps_h * 60)
    # Vitesse moyenne
    vit_moy = round(dist_km / temps_h, 1) if temps_h > 0 else 0

    return dict(
        mins=max(1, mins),
        vam=int(vam),
        vit_moy=vit_moy,
        niveau=niveau_cycliste(vam),
    )


def estimer_temps_col(
    dist_km: float,
    pente_moy_pct: float,
    vitesse_plat_kmh: float,
) -> tuple[int, float]:
    """
    Estime le temps d'ascension via méthode simpliste (conservée pour compatibilité).
    
    Args:
        dist_km: Distance de l'ascension (km)
        pente_moy_pct: Pente moyenne (%)
        vitesse_plat_kmh: Vitesse en plat (km/h)
        
    Returns:
        Tuple (temps_minutes, vitesse_moyenne_kmh)
    """
    factor = 1.0 + pente_moy_pct * 0.10
    climb_speed = max(5.0, vitesse_plat_kmh / factor)
    temps_min = int((dist_km / climb_speed) * 60)
    return temps_min, round(climb_speed, 1)


def calculer_calories(
    poids_cycliste_kg: float,
    duree_sec: float,
    dist_m: float,
    d_plus_m: float,
    vitesse_kmh: float,
) -> int:
    """
    Estime les calories brûlées via formule MET (Metabolic Equivalent).
    
    MET dépend de la vitesse, ajusté par la pente globale du parcours.
    
    Args:
        poids_cycliste_kg: Poids du cycliste (kg)
        duree_sec: Durée de l'exercice (s)
        dist_m: Distance (m)
        d_plus_m: Dénivelé positif (m)
        vitesse_kmh: Vitesse moyenne (km/h)
        
    Returns:
        Calories estimées (kcal)
    """
    if poids_cycliste_kg <= 0 or duree_sec <= 0:
        return 0
    
    duree_h = duree_sec / 3600
    # Pente globale
    global_slope = (d_plus_m / dist_m * 100) if dist_m > 0 else 0
    
    # Sélection du MET de base selon vitesse
    if vitesse_kmh < 16:
        met = 6.0
    elif vitesse_kmh < 20:
        met = 8.0
    elif vitesse_kmh < 25:
        met = 10.0
    elif vitesse_kmh < 30:
        met = 12.0
    else:
        met = 14.0
    
    # Ajustement pente + cap à 18 MET max
    total_met = min(met + global_slope * 0.8, 18.0)
    return int(total_met * poids_cycliste_kg * duree_h)


# ==============================================================================
# CATÉGORISATION UCI
# ==============================================================================

def categoriser_uci(
    distance_m: float,
    d_plus: float,
) -> tuple[Optional[str], float]:
    """
    Catégorise une ascension selon normes UCI.
    
    Formule : Score UCI = (dénivelé × pente_moyenne) / 100
    
    Args:
        distance_m: Distance de l'ascension (m)
        d_plus: Dénivelé positif (m)
        
    Returns:
        Tuple (catégorie_label, score_uci) ou (None, 0.0) si sous seuils
    """
    if distance_m < DISTANCE_MIN_M or d_plus < D_PLUS_MIN:
        return None, 0.0
    
    pente_moy = (d_plus / distance_m) * 100
    if pente_moy < PENTE_MIN_CAT:
        return None, 0.0
    
    score = (d_plus * pente_moy) / 100
    # Recherche de la catégorie (du plus difficile au moins difficile)
    for label, threshold in SEUILS_UCI.items():
        if score >= threshold:
            return label, round(score, 1)
    
    return None, 0.0


# ==============================================================================
# FONCTIONS INTERNES DE DÉTECTION
# ==============================================================================

def _lisser(alts: list[float], f: int = LISSAGE_F) -> list[float]:
    """
    Lisse la série d'altitudes via moyenne glissante.
    
    Args:
        alts: Liste des altitudes (m)
        f: Fenêtre de lissage (nombre impair de points)
        
    Returns:
        Liste lissée
    """
    half = f // 2
    n = len(alts)
    result = []
    
    for i in range(n):
        start = max(0, i - half)
        end = min(n, i + half + 1)
        avg = sum(alts[start:end]) / (end - start)
        result.append(avg)
    
    return result


def _calc_pentes(
    dists: list[float],
    alts: list[float],
    fenetre_m: float = FENETRE_PENTE_M,
) -> list[float]:
    """
    Calcule la pente moyenne sur fenêtre mobile.
    
    Args:
        dists: Liste des distances cumulées (km)
        alts: Liste des altitudes (m)
        fenetre_m: Fenêtre de calcul (m)
        
    Returns:
        Liste des pentes (%)
    """
    n = len(dists)
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


def _detecter_runs(
    dists: list[float],
    alts: list[float],
    pentes: list[float],
) -> list[tuple[int, int]]:
    """
    Détecte les segments de montée continue (runs).
    
    Un run commence quand pente ≥ SEUIL_DEBUT et finit quand pente < SEUIL_DEBUT.
    
    Args:
        dists: Distances cumulées (km)
        alts: Altitudes (m)
        pentes: Pentes (%)
        
    Returns:
        Liste de tuples (index_debut, index_fin)
    """
    n = len(dists)
    runs = []
    debut = None
    
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
    
    # Vérifier le dernier run
    if debut is not None:
        dist_run = (dists[-1] - dists[debut]) * 1000
        if dist_run >= MIN_RUN_M:
            runs.append((debut, n - 1))
    
    return runs


def _fusionner_runs(
    runs: list[tuple[int, int]],
    dists: list[float],
    alts: list[float],
) -> list[tuple[int, int]]:
    """
    Fusionne deux runs proches s'ils sont séparés par une descente faible.
    
    Args:
        runs: Liste de runs (index_debut, index_fin)
        dists: Distances (km)
        alts: Altitudes (m)
        
    Returns:
        Liste de runs fusionnés
    """
    if not runs:
        return []
    
    fused = [list(runs[0])]
    
    for debut, fin in runs[1:]:
        prev_debut, prev_fin = fused[-1]
        # Altitude minimale entre fin du run précédent et début du run courant
        alt_valley = min(alts[prev_fin:debut + 1])
        # Descente pour rejoindre la vallée
        descent = alts[prev_fin] - alt_valley
        
        if descent < MAX_DESCENTE_FUSION_M:
            # Fusionner
            fused[-1][1] = fin
        else:
            # Garder séparé
            fused.append([debut, fin])
    
    return [tuple(r) for r in fused]


def _pente_max(
    dists: list[float],
    alts: list[float],
    i0: int,
    i1: int,
    fenetre_m: float = 100.0,
) -> float:
    """
    Calcule la pente maximale sur la section [i0, i1].
    
    Args:
        dists: Distances (km)
        alts: Altitudes (m)
        i0: Index de début
        i1: Index de fin
        fenetre_m: Fenêtre de calcul (m)
        
    Returns:
        Pente maximale (%)
    """
    pente_max_val = 0.0
    
    for i in range(i0 + 1, i1 + 1):
        for j in range(i - 1, i0 - 1, -1):
            dist_m = (dists[i] - dists[j]) * 1000
            if dist_m >= fenetre_m:
                pente = ((alts[i] - alts[j]) / dist_m) * 100
                if 0 < pente <= 40:
                    pente_max_val = max(pente_max_val, pente)
                break
    
    return round(pente_max_val, 1)


# ==============================================================================
# FONCTION PRINCIPALE
# ==============================================================================

def detecter_ascensions(df: pd.DataFrame) -> list[dict]:
    """
    Détecte et catégorise les ascensions dans un profil altimétrique.
    Utilise un algorithme slope-first avec lissage et fusion de runs.
    
    Args:
        df: DataFrame avec colonnes "Distance (km)" et "Altitude (m)"
        
    Returns:
        Liste d'ascensions formatées (compatible UI existante)
    """
    if df.empty or len(df) < 5:
        return []

    alts_raw = df["Altitude (m)"].tolist()
    dists = df["Distance (km)"].tolist()
    alts = _lisser(alts_raw)
    pentes = _calc_pentes(dists, alts)
    runs = _detecter_runs(dists, alts, pentes)
    runs = _fusionner_runs(runs, dists, alts)

    ascensions = []
    
    for i0, i1 in runs:
        # Géométrie
        dist_km = dists[i1] - dists[i0]
        d_plus = alts[i1] - alts[i0]
        
        if dist_km <= 0 or d_plus < D_PLUS_MIN:
            continue
        
        # Catégorisation UCI
        cat, score = categoriser_uci(dist_km * 1000, d_plus)
        if cat is None:
            continue
        
        # Pente moyenne
        pente_moy = (d_plus / (dist_km * 1000)) * 100
        
        ascensions.append({
            "Catégorie": cat,
            "Départ (km)": round(dists[i0], 1),
            "Sommet (km)": round(dists[i1], 1),
            "Longueur": f"{round(dist_km, 1)} km",
            "Dénivelé": f"{int(d_plus)} m",
            "Pente moy.": f"{round(pente_moy, 1)} %",
            "Pente max": f"{_pente_max(dists, alts_raw, i0, i1)} %",
            "Alt. sommet": f"{int(alts_raw[i1])} m",
            "Score UCI": score,
            "_debut_km": dists[i0],
            "_sommet_km": dists[i1],
            "_pente_moy": pente_moy,
        })

    # Tri par position
    ascensions.sort(key=lambda x: x["_debut_km"])
    return ascensions


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
