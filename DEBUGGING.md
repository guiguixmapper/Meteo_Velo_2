# 🐛 Déboggage - Erreur "Erreur lors du traitement du parcours"

## ✅ Problème Identifié & Corrigé

### Avant (❌ Mauvais)
```python
except Exception as e:
    logging.error(f"Erreur traitement données : {e}")
    return None  # Erreur silencieuse !
```

L'erreur était loggée en backend mais **pas affichée à l'utilisateur** dans Streamlit.

### Après (✅ Corrigé)
```python
except Exception as e:
    import traceback
    error_msg = f"Erreur traitement données : {str(e)}"
    logging.error(error_msg)
    logging.error(traceback.format_exc())
    
    # Afficher l'erreur VISIBLE à l'utilisateur
    progress_container.empty()
    st.error(f"❌ **Erreur lors du traitement du parcours:**\n\n{str(e)}\n\n**Stack trace:**\n```\n{traceback.format_exc()}\n```")
    return None
```

**Maintenant l'erreur exacte s'affiche à l'utilisateur !** 🎯

---

## 📋 Erreurs Possibles & Solutions

### 1. **"Module 'pandas' not found"**
```
❌ Erreur: No module named 'pandas'
✅ Solution: pip install pandas
```

### 2. **"Fichier GPX vide ou corrompu"**
```
❌ Le fichier GPX n'a pas de points
✅ Solution: 
  - Vérifier le fichier GPX dans un viewer externe
  - S'assurer qu'il contient des traces (tracks) avec des points
```

### 3. **"Erreur parsing GPX"**
```
❌ Fichier GPX malformé
✅ Solution:
  - Télécharger un nouveau fichier GPX valide
  - Utiliser un GPS tracker fiable (Garmin, Strava, etc)
```

### 4. **"Recherche en parallèle"** - Timeout API
```
❌ Une API externe (timezone, soleil, météo) a timeout
✅ Solution:
  - Vérifier la connexion internet
  - Attendre quelques secondes
  - Réessayer avec le même fichier
```

### 5. **"Calcul du parcours"** - Vitesse invalide
```
❌ ValidationError: vitesse_plat_kmh: Doit être > 0
✅ Solution:
  - Vérifier que vitesse > 0 km/h dans le sidebar
  - Default: 25 km/h
```

### 6. **"Détection ascensions"** - Problème pandas
```
❌ Erreur lors de la création du DataFrame
✅ Solution:
  - Vérifier que pandas est bien installé
  - Le tracé doit avoir au moins 10 points
```

### 7. **"Enrichissement OSM"** - API Overpass limité
```
❌ Timeout ou 429 (rate limit)
✅ Solution:
  - Désactiver "Enrichissement OSM" dans sidebar
  - Ou attendre quelques minutes
```

### 8. **"Récupération météo"** - Open-Meteo limit
```
❌ WeatherRateLimitError: Too many requests
✅ Solution:
  - Réduire le nombre de checkpoints
  - Attendre 1 minute
  - La météo n'est pas critique pour l'analyse
```

---

## 🧪 Comment Tester

### Étape 1: Lancer l'app
```bash
streamlit run app.py
```

### Étape 2: Upload un fichier GPX
- Cliquer sur le champ "📁 Importer GPX"
- Sélectionner un fichier `.gpx` valide
- ⏳ Attendre le traitement

### Étape 3: Voir l'erreur exacte
- Si erreur → Message détaillé s'affiche
- Copier le message pour déboguer

### Étape 4: Vérifier les logs console
```bash
# Dans le terminal où Streamlit tourne
# Vous verrez aussi les logs détaillés :
# ERROR:root:Erreur traitement données : [message d'erreur]
# [Full traceback]
```

---

## 🔍 Debugging Avancé

### Tester juste le parsing GPX
```python
from core.services.route_service import parser_gpx

with open("mon_tracé.gpx", "rb") as f:
    data = f.read()

try:
    points = parser_gpx(data)
    print(f"✅ Parsé: {len(points)} points")
except Exception as e:
    print(f"❌ Erreur: {e}")
```

### Tester le calcul de parcours
```python
from core.services.route_service import calculer_parcours
from datetime import datetime

try:
    result = calculer_parcours(
        points_gpx,
        vitesse_plat_kmh=25.0,
        date_depart=datetime.now(),
        intervalle_sec=300
    )
    print(f"✅ Distance: {result['dist_tot']/1000:.1f} km")
    print(f"✅ D+: {result['d_plus']:.0f} m")
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
```

### Vérifier l'environment
```bash
python -c "import pandas, gpxpy, streamlit; print('✅ All imports OK')"
```

---

## 📊 Fichiers Modifiés

1. **core/data_processor.py** - Exception handler amélioré
   - Affiche maintenant le traceback complet à l'utilisateur
   - Logging plus verbeux

2. **app.py** - Messages d'erreur simplifiés
   - Erreur détaillée maintenant affichée par DataProcessor
   - Ajout de l'import pandas au top

---

## ✅ Après la Correction

Relancer l'app :
```bash
streamlit run app.py
```

Si vous avez l'erreur "Erreur lors du traitement du parcours", vous verrez maintenant :
1. ✅ Message d'erreur détaillé
2. ✅ La ligne de code qui a échoué
3. ✅ Le type d'exception (GPXError, ValidationError, etc.)
4. ✅ Stack trace complet pour déboguer

---

## 💡 Notes

- Les exceptions custom (GPXError, ValidationError, etc.) sont définies dans `core/exceptions.py`
- Tous les try/except ont maintenant du logging approprié
- Les erreurs utilisateur (GPX vide, mauvais paramètres) sont distinguées des bugs système

**Le code est maintenant transparent sur les erreurs !** 🎯
