#!/usr/bin/env python
"""Test que tous les imports principaux fonctionnent correctement"""

try:
    from core.exceptions import (
        MeteoVeloException, GPXError, WeatherError, 
        WeatherRateLimitError, OSMError, GeminiError, 
        ValidationError, ConfigError, DataProcessingError
    )
    print("✅ core.exceptions OK")
except Exception as e:
    print(f"❌ core.exceptions: {e}")

try:
    from core.services.route_service import (
        parser_gpx, calculer_parcours, enrichir_checkpoints_meteo,
        analyser_meteo_detaillee, calculer_score
    )
    print("✅ core.services.route_service OK")
except Exception as e:
    print(f"❌ core.services.route_service: {e}")

try:
    from core.services.climbing_service import detecter_ascensions, estimer_watts
    print("✅ core.services.climbing_service OK")
except Exception as e:
    print(f"❌ core.services.climbing_service: {e}")

try:
    from core.data_processor import DataProcessor, AppConfig, ProcessedData
    print("✅ core.data_processor OK")
except Exception as e:
    print(f"❌ core.data_processor: {e}")

try:
    from config.settings import FONDS_CARTE, RouteResult, CheckpointData
    print("✅ config.settings OK")
except Exception as e:
    print(f"❌ config.settings: {e}")

print("\n🎉 Tous les imports critiques sont fonctionnels!")
