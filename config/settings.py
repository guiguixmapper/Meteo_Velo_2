"""
config/settings.py
==================
Toutes les constantes de l'application en un seul endroit.
"""

# ==============================================================================
# DÉTECTION DES ASCENSIONS
# ==============================================================================

LISSAGE_F             = 5      # points — fenêtre de lissage (impair)
FENETRE_PENTE_M       = 300    # m — fenêtre de calcul de la pente glissante
SEUIL_DEBUT           = 2.0    # % — seuil pour démarrer une montée
SEUIL_FIN             = 1.0    # % — seuil pour terminer une montée
MIN_RUN_M             = 300    # m — longueur minimale d'un run
MAX_DESCENTE_FUSION_M = 50     # m D− max pour fusionner deux runs
D_PLUS_MIN            = 30     # m — dénivelé minimum pour retenir une montée
DISTANCE_MIN_M        = 500    # m — longueur minimale pour retenir une montée
PENTE_MIN_CAT         = 1.0    # % — pente moyenne minimale pour catégoriser

SEUILS_UCI = {
    "🔴 HC":         80,
    "🟠 1ère Cat.":  40,
    "🟡 2ème Cat.":  20,
    "🟢 3ème Cat.":   8,
    "🔵 4ème Cat.":   2,
    "⚪ NC":          0,
}

COULEURS_CAT = {
    "🔴 HC":        "#ef4444",
    "🟠 1ère Cat.": "#f97316",
    "🟡 2ème Cat.": "#eab308",
    "🟢 3ème Cat.": "#22c55e",
    "🔵 4ème Cat.": "#3b82f6",
    "⚪ NC":        "#94a3b8",
}

LEGENDE_UCI = (
    "**Catégorisation UCI** — Score = (D+ × pente moy.) / 100 · "
    "⚪ NC ≥0 · 🔵 4ème ≥2 · 🟢 3ème ≥8 · 🟡 2ème ≥20 · 🟠 1ère ≥40 · 🔴 HC ≥80"
)

SENSIBILITE_LABELS = {
    1: "🔵 Strict — grands cols seulement",
    2: "🟢 Conservateur",
    3: "🟡 Équilibré (défaut)",
    4: "🟠 Sensible",
    5: "🔴 Maximum — toutes les côtes",
}

SENSIBILITE_PARAMS = {
    1: (4.0, 2.0,  20),
    2: (3.0, 1.5,  35),
    3: (2.0, 1.0,  50),
    4: (1.5, 0.5,  70),
    5: (0.5, 0.0, 100),
}

# ==============================================================================
# ZONES D'ENTRAÎNEMENT
# ==============================================================================

ZONES_PUISSANCE = [
    (0.00, 0.55, 1, "Z1 Récup",     "#94a3b8"),
    (0.55, 0.75, 2, "Z2 Endurance", "#3b82f6"),
    (0.75, 0.90, 3, "Z3 Tempo",     "#22c55e"),
    (0.90, 1.05, 4, "Z4 Seuil",     "#eab308"),
    (1.05, 1.20, 5, "Z5 VO2max",    "#f97316"),
    (1.20, 999., 6, "Z6 Anaérobie", "#ef4444"),
]

ZONES_FC = [
    (0.00, 0.60, 1, "Z1 Récup",     "#94a3b8"),
    (0.60, 0.70, 2, "Z2 Endurance", "#3b82f6"),
    (0.70, 0.80, 3, "Z3 Tempo",     "#22c55e"),
    (0.80, 0.90, 4, "Z4 Seuil",     "#eab308"),
    (0.90, 0.95, 5, "Z5 VO2max",    "#f97316"),
    (0.95, 999., 6, "Z6 Anaérobie", "#ef4444"),
]

# ==============================================================================
# OSM / OVERPASS
# ==============================================================================

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

RAYON_SOMMET_M  = 800
RAYON_EAU_M     = 1500
TIMEOUT_OSM_S   = 25
MAX_RETRIES_OSM = 4
RETRY_DELAYS    = [2, 5, 10]

OSM_TYPES_PRIORITE = {
    "mountain_pass": 0,
    "saddle":        1,
    "peak":          2,
    "volcano":       3,
}

# ==============================================================================
# MÉTÉO
# ==============================================================================

MAX_CHECKPOINTS_METEO = 50   # limite pour éviter les 429 Open-Meteo
CACHE_METEO_TTL       = 3600  # 1 heure
CACHE_OSM_TTL         = 86400 # 24 heures
RETRY_METEO_DELAYS    = [2, 5, 12]

# ==============================================================================
# NUTRITION
# ==============================================================================

EAU_FROID_L_H   = 0.5   # L/h si temp < 15°C
EAU_TEMPE_L_H   = 0.7   # L/h si 15°C ≤ temp < 25°C
EAU_CHAUD_L_H   = 1.0   # L/h si temp ≥ 25°C
CARBS_BASE_G_H  = 60    # g/h standard
CARBS_HARD_G_H  = 70    # g/h si D+ > 1500m ou durée > 4h
BARRE_GLUCIDES_G = 40   # glucides par barre
GEL_GLUCIDES_G   = 25   # glucides par gel

# ==============================================================================
# UI / DESIGN
# ==============================================================================

COULEUR_TEAL      = "#0d9488"
COULEUR_TEAL_DARK = "#0f766e"

FONDS_CARTE = {
    "🗺️ CartoDB Positron (épuré)": ("CartoDB positron", None),
    "🌍 OpenStreetMap (classique)": ("OpenStreetMap", None),
    "🏔️ OpenTopoMap (relief)": (
        "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        "Map data © OpenStreetMap contributors, SRTM | Map style © OpenTopoMap (CC-BY-SA)",
    ),
}
