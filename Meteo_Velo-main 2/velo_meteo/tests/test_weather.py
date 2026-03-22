"""
tests/test_weather.py
======================
Tests unitaires pour les calculs météo (fonctions pures uniquement).
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from core.utils.geo import wind_chill, label_wind_chill, direction_vent_relative, calculer_cap
from infrastructure.open_meteo_client import obtenir_icone_meteo, label_uv, label_pollen, extraire_meteo


# ==============================================================================
# WIND CHILL
# ==============================================================================

def test_wind_chill_froid():
    r = wind_chill(-5, 30)
    assert r is not None
    assert r < -5  # ressenti plus froid que la temp réelle

def test_wind_chill_chaud():
    assert wind_chill(15, 20) is None  # pas de wind chill si temp > 10°C

def test_wind_chill_vent_faible():
    assert wind_chill(5, 3) is None   # vent trop faible


# ==============================================================================
# LABEL WIND CHILL
# ==============================================================================

def test_label_wind_chill_none():
    assert label_wind_chill(None) == "—"

def test_label_wind_chill_froid():
    lbl = label_wind_chill(-15)
    assert "🟠" in lbl
    assert "-15" in lbl

def test_label_wind_chill_frais():
    lbl = label_wind_chill(5)
    assert "🔵" in lbl


# ==============================================================================
# DIRECTION VENT
# ==============================================================================

def test_vent_face():
    # Cap Nord (0°), vent du Nord (0°) → de face
    assert direction_vent_relative(0, 0) == "⬇️ Face"

def test_vent_dos():
    # Cap Nord (0°), vent du Sud (180°) → dans le dos
    assert direction_vent_relative(0, 180) == "⬆️ Dos"

def test_vent_cote():
    # Cap Nord (0°), vent de l'Est (90°) → côté
    result = direction_vent_relative(0, 90)
    assert "Côté" in result


# ==============================================================================
# ICÔNES MÉTÉO
# ==============================================================================

def test_icone_clair():
    assert "Clair" in obtenir_icone_meteo(0)

def test_icone_pluie():
    assert "Pluie" in obtenir_icone_meteo(61)

def test_icone_inconnu():
    assert "Inconnu" in obtenir_icone_meteo(999)


# ==============================================================================
# UV
# ==============================================================================

def test_uv_faible():
    emoji, label, coul = label_uv(1.5)
    assert "Faible" in label
    assert emoji == "🟢"

def test_uv_extreme():
    emoji, label, coul = label_uv(12)
    assert "Extrême" in label
    assert emoji == "🟣"

def test_uv_none():
    emoji, label, coul = label_uv(None)
    assert emoji == "—"


# ==============================================================================
# POLLEN
# ==============================================================================

def test_pollen_faible():
    assert label_pollen(5, "Graminées") is None

def test_pollen_modere():
    lbl = label_pollen(30, "🌾 Graminées")
    assert lbl is not None
    assert "Modéré" in lbl

def test_pollen_eleve():
    lbl = label_pollen(150, "🌳 Bouleau")
    assert "Élevé" in lbl


# ==============================================================================
# EXTRACTION MÉTÉO
# ==============================================================================

def _make_api_response(temp=15.0, vent=10.0, pluie=20, code=0):
    return {
        "hourly": {
            "time":                       ["2026-03-19T10:00"],
            "temperature_2m":             [temp],
            "wind_speed_10m":             [vent],
            "wind_gusts_10m":             [vent * 1.5],
            "wind_direction_10m":         [180],
            "precipitation_probability":  [pluie],
            "weathercode":                [code],
        }
    }

def test_extraire_meteo_basique():
    data = _make_api_response(15.0, 10.0, 20, 0)
    m = extraire_meteo(data, "2026-03-19T10:00")
    assert m["temp_val"] == 15.0
    assert m["vent_val"] == 10.0
    assert m["pluie_pct"] == 20
    assert "Clair" in m["Ciel"]

def test_extraire_meteo_heure_absente():
    data = _make_api_response()
    m = extraire_meteo(data, "2026-03-19T11:00")
    assert m["temp_val"] is None

def test_extraire_meteo_vide():
    m = extraire_meteo({}, "2026-03-19T10:00")
    assert m["temp_val"] is None


# ==============================================================================
# CAP
# ==============================================================================

def test_cap_nord():
    # Deux points sur le même méridien, le second plus au nord
    cap = calculer_cap(48.0, 2.0, 49.0, 2.0)
    assert abs(cap) < 5 or abs(cap - 360) < 5   # ~0° = Nord

def test_cap_est():
    cap = calculer_cap(48.0, 2.0, 48.0, 3.0)
    assert 85 < cap < 95   # ~90° = Est


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
