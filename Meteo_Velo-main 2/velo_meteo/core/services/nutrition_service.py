"""
core/services/nutrition_service.py
====================================
Calculs nutrition et hydratation purs.
"""

from config.settings import (
    EAU_FROID_L_H, EAU_TEMPE_L_H, EAU_CHAUD_L_H,
    CARBS_BASE_G_H, CARBS_HARD_G_H,
    BARRE_GLUCIDES_G, GEL_GLUCIDES_G,
)


def calculer_hydratation(duree_h: float, t_max: float | None) -> dict:
    """Calcule les besoins en eau selon la durée et la température."""
    if t_max is not None and t_max >= 25:
        eau_h     = EAU_CHAUD_L_H
        conseil   = "1 bidon/heure + électrolytes (chaleur)"
        alerte    = True
    elif t_max is not None and t_max >= 15:
        eau_h     = EAU_TEMPE_L_H
        conseil   = "700 ml/heure"
        alerte    = False
    else:
        eau_h     = EAU_FROID_L_H
        conseil   = "500 ml/heure"
        alerte    = False

    return dict(
        eau_h=eau_h,
        eau_total=round(eau_h * duree_h, 1),
        conseil=conseil,
        alerte_electrolytes=alerte,
    )


def calculer_glucides(duree_h: float, d_plus_m: float) -> dict:
    """Calcule les besoins en glucides."""
    carbs_h     = CARBS_HARD_G_H if (d_plus_m > 1500 or duree_h > 4) else CARBS_BASE_G_H
    carbs_total = int(carbs_h * duree_h)
    return dict(
        carbs_h=carbs_h,
        carbs_total=carbs_total,
        nb_barres=round(carbs_total / BARRE_GLUCIDES_G),
        nb_gels=round(carbs_total / GEL_GLUCIDES_G),
    )
