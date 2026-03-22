"""
tests/test_nutrition.py
========================
Tests unitaires pour les calculs nutrition.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from core.services.nutrition_service import calculer_hydratation, calculer_glucides
from config.settings import EAU_FROID_L_H, EAU_TEMPE_L_H, EAU_CHAUD_L_H, CARBS_BASE_G_H, CARBS_HARD_G_H


# ==============================================================================
# HYDRATATION
# ==============================================================================

def test_hydratation_froid():
    r = calculer_hydratation(3.0, 10.0)
    assert r["eau_h"]    == EAU_FROID_L_H
    assert r["eau_total"] == round(EAU_FROID_L_H * 3.0, 1)
    assert not r["alerte_electrolytes"]

def test_hydratation_tempe():
    r = calculer_hydratation(4.0, 20.0)
    assert r["eau_h"] == EAU_TEMPE_L_H
    assert not r["alerte_electrolytes"]

def test_hydratation_chaud():
    r = calculer_hydratation(5.0, 30.0)
    assert r["eau_h"] == EAU_CHAUD_L_H
    assert r["alerte_electrolytes"]
    assert "électrolytes" in r["conseil"].lower()

def test_hydratation_sans_temp():
    r = calculer_hydratation(3.0, None)
    assert r["eau_h"] == EAU_FROID_L_H   # par défaut froid si None

def test_hydratation_total_croissant():
    r1 = calculer_hydratation(2.0, 20.0)
    r2 = calculer_hydratation(4.0, 20.0)
    assert r2["eau_total"] > r1["eau_total"]


# ==============================================================================
# GLUCIDES
# ==============================================================================

def test_glucides_base():
    r = calculer_glucides(3.0, 500)   # D+ faible, durée < 4h
    assert r["carbs_h"] == CARBS_BASE_G_H
    assert r["carbs_total"] == int(CARBS_BASE_G_H * 3.0)

def test_glucides_hard_dplus():
    r = calculer_glucides(3.0, 2000)  # D+ > 1500m
    assert r["carbs_h"] == CARBS_HARD_G_H

def test_glucides_hard_duree():
    r = calculer_glucides(5.0, 500)   # durée > 4h
    assert r["carbs_h"] == CARBS_HARD_G_H

def test_glucides_barres_coherent():
    r = calculer_glucides(4.0, 500)
    # nb_barres = carbs_total / 40, arrondi
    assert r["nb_barres"] == round(r["carbs_total"] / 40)

def test_glucides_gels_coherent():
    r = calculer_glucides(4.0, 500)
    assert r["nb_gels"] == round(r["carbs_total"] / 25)

def test_glucides_croissant():
    r1 = calculer_glucides(2.0, 500)
    r2 = calculer_glucides(6.0, 500)
    assert r2["carbs_total"] > r1["carbs_total"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
