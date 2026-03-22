# Meteo_Velo
Météo sur le parcous de vélo gpx


ton-repo/
├── app.py
├── requirements.txt
├── config/
│   ├── __init__.py
│   └── settings.py
├── core/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── route.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── climbing_service.py
│   │   ├── nutrition_service.py
│   │   └── route_service.py
│   └── utils/
│       ├── __init__.py
│       └── geo.py
├── infrastructure/
│   ├── __init__.py
│   ├── gemini_client.py
│   ├── open_meteo_client.py
│   └── osm_client.py
├── ui/
│   ├── __init__.py
│   ├── map_builder.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── climbs_view.py
│   │   ├── coach_view.py
│   │   ├── detail_view.py
│   │   ├── export.py
│   │   ├── map_view.py
│   │   ├── metrics_banner.py
│   │   ├── profile_view.py
│   │   ├── sidebar.py
│   │   └── weather_view.py
│   └── styles/
│       ├── __init__.py
│       └── theme.py
└── tests/
    ├── __init__.py
    ├── test_climbing.py
    ├── test_nutrition.py
    └── test_weather.py
