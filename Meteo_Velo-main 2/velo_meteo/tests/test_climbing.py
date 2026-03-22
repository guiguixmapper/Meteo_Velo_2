"""
tests/test_climbing.py
=======================
Tests unitaires pour la détection des ascensions.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import pandas as pd
from core.services.climbing_service import (
    detecter_ascensions, categoriser_uci, estimer_watts,
    estimer_temps_col, calculer_calories, _lisser, _calc_pentes,
)


# ==============================================================================
# CATÉGORISATION UCI
# ==============================================================================

def test_categoriser_uci_hc():
    cat, score = categoriser_uci(20000, 1600)  # 20km à 8% → score 128
    assert cat == "🔴 HC"
    assert score >= 80

def test_categoriser_uci_4eme():
    cat, score = categoriser_uci(3000, 90)  # 3km à 3%
    assert cat == "🔵 4ème Cat."

def test_categoriser_uci_trop_court():
    cat, score = categoriser_uci(300, 50)   # trop court
    assert cat is None
    assert score == 0.0

def test_categoriser_uci_trop_plat():
    cat, score = categoriser_uci(5000, 10)  # 5km à 0.2% → trop plat
    assert cat is None


# ==============================================================================
# LISSAGE
# ==============================================================================

def test_lisser_longueur():
    alts = [100, 110, 105, 120, 115, 130, 125]
    lissees = _lisser(alts, f=3)
    assert len(lissees) == len(alts)

def test_lisser_valeurs():
    alts = [100, 100, 200, 100, 100]
    lissees = _lisser(alts, f=3)
    # Le pic central doit être lissé à la baisse
    assert lissees[2] < 200


# ==============================================================================
# ESTIMATION WATTS
# ==============================================================================

def test_estimer_watts_plat():
    w = estimer_watts(0.0, 25, 75)
    assert w >= 0

def test_estimer_watts_montee():
    w_montee = estimer_watts(8.0, 25, 75)
    w_plat   = estimer_watts(0.5, 25, 75)
    assert w_montee > w_plat

def test_estimer_watts_poids():
    w_lourd  = estimer_watts(5.0, 25, 90)
    w_leger  = estimer_watts(5.0, 25, 60)
    assert w_lourd > w_leger


# ==============================================================================
# TEMPS COL
# ==============================================================================

def test_estimer_temps_col_basique():
    mins, vit = estimer_temps_col(10.0, 7.0, 25)
    assert mins > 0
    assert vit > 0
    assert vit < 25  # plus lent qu'en plat

def test_estimer_temps_col_pente_forte():
    mins_8, _ = estimer_temps_col(5.0, 8.0, 25)
    mins_4, _ = estimer_temps_col(5.0, 4.0, 25)
    assert mins_8 > mins_4  # pente forte = plus long


# ==============================================================================
# CALORIES
# ==============================================================================

def test_calculer_calories_positif():
    cal = calculer_calories(65, 7200, 50000, 800, 20)
    assert cal > 0

def test_calculer_calories_zero():
    assert calculer_calories(0, 3600, 30000, 500, 20) == 0
    assert calculer_calories(65, 0,    30000, 500, 20) == 0


# ==============================================================================
# DÉTECTION ASCENSIONS
# ==============================================================================

def test_detecter_ascensions_vide():
    df = pd.DataFrame(columns=["Distance (km)", "Altitude (m)"])
    assert detecter_ascensions(df) == []

def test_detecter_ascensions_plat():
    df = pd.DataFrame({
        "Distance (km)": [i * 0.1 for i in range(50)],
        "Altitude (m)":  [100.0] * 50,
    })
    assert detecter_ascensions(df) == []

def test_detecter_ascensions_montee():
    dists = [i * 0.1 for i in range(100)]
    alts  = [100 + i * 4 for i in range(100)]  # montée régulière 4m/100m = 4%
    df = pd.DataFrame({"Distance (km)": dists, "Altitude (m)": alts})
    ascensions = detecter_ascensions(df)
    assert len(ascensions) >= 1
    assert ascensions[0]["_debut_km"] < ascensions[0]["_sommet_km"]

def test_detecter_ascensions_champs_requis():
    dists = [i * 0.15 for i in range(100)]
    alts  = [200 + i * 5 for i in range(100)]
    df = pd.DataFrame({"Distance (km)": dists, "Altitude (m)": alts})
    ascensions = detecter_ascensions(df)
    if ascensions:
        asc = ascensions[0]
        for champ in ["Catégorie", "Départ (km)", "Sommet (km)", "Longueur",
                      "Dénivelé", "Pente moy.", "_debut_km", "_sommet_km", "_pente_moy"]:
            assert champ in asc, f"Champ manquant : {champ}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
