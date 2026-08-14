# 🗺️ Overpass API - Guide de Dépannage

## Qu'est-ce que Overpass?

**Overpass API** est un service de données OpenStreetMap qui fournit :
- 📍 Noms des cols et sommets
- 💧 Points d'eau potable
- 🏔️ Données géographiques détaillées

---

## ⚠️ Erreur Courante

```
WARNING:infrastructure.osm_client:Points d'eau — 
https://overpass-api.de/api/interpreter : 
HTTPSConnectionPool(...): Connection refused
```

### Ce que ça signifie
- ❌ Le serveur Overpass ne répond pas
- ❌ **Ce n'est PAS un bug de notre code**
- ✅ L'app continue à fonctionner sans les données OSM

### Pourquoi ça arrive

| Raison | Symptôme | Solution |
|--------|----------|----------|
| **Serveur surchargé** | `429 (Rate Limit)` ou `503 (Overloaded)` | Attendre 5-10 min |
| **Maintenance** | `Connection refused` ou timeout | Attendre que ce soit terminé |
| **Problème réseau** | `Timeout après 20s` | Vérifier la connexion internet |
| **Serveur down** | Tous les serveurs échouent | Overpass down - attendre |

---

## 🚀 Solutions

### Solution 1: C'est Temporaire - Réessayez (Recommandé)
```
1. Attendez 1-2 minutes
2. Relancez l'app: streamlit run app.py
3. UploadCheck un nouveau GPX ou rafraîchissez la page
```

### Solution 2: Désactiver Enrichissement OSM
Si Overpass est trop instable :
1. Dans le **Sidebar** → Décocher `✓ Enrichissement OSM`
2. L'app fonctionnera sans les noms de cols
3. Les calculs de parcours/météo restent normaux

### Solution 3: Attendre Que Overpass Récupère
- Overpass redémarre ~toutes les 1-2 heures pendant la maint
- Outils de monitoring: https://overpass-api.de/status
- Si 🟩 Green → OK
- Si 🟥 Red → Attendez

---

## 📊 Ce Qui Fonctionne Quand OSM Est Down

✅ **Fonctionnels** :
- Analyse de parcours (distance, dénivelé, temps)
- Détection des ascensions
- Météo hourly
- Profil altimétrique
- Coach IA
- Export des données

❌ **Non-fonctionnels** :
- Noms des cols (affiche "—")
- Points d'eau sur la carte
- Enrichissement automatique des ascensions

---

## 🔍 Diagnostiquer

### Vérifier que c'est Overpass

Regarder les **logs Streamlit** (console) :

```
✅ Normal (pas d'erreur Overpass):
   [Pas de WARNING osm_client]

❌ Overpass surchargé:
   WARNING:infrastructure.osm_client:Points d'eau — ... : 429
   WARNING:infrastructure.osm_client:Points d'eau — ... : 503

❌ Overpass down:
   WARNING:infrastructure.osm_client:Points d'eau — ... : Connection refused
   WARNING:infrastructure.osm_client:Points d'eau — ... : Timeout après 20s

❌ Tous les serveurs indisponibles:
   WARNING:infrastructure.osm_client:Tous les serveurs Overpass indisponibles après retries
```

### Script de Test Overpass

```bash
# Tester la connexion directement
curl -X POST "https://overpass-api.de/api/interpreter" \
  -d "data=[out:json];node[name];out 10;"

# Résultat:
# - 200 OK → API fonctionne
# - 429 → Rate limit (réessayez dans 1 min)
# - 503 → Serveur surchargé
# - Connection refused → Serveur down
```

---

## 📌 Messages d'Erreur & Interprétation

### 1. "Points d'eau indisponibles"
```
⚠️ Points d'eau indisponibles (serveur Overpass injoignable)
```
→ **API Overpass temporairement down** → Réessayez après 5 min

### 2. "API Overpass rate-limitée"
```
⚠️ Points d'eau: API Overpass rate-limitée. Réessayez dans 1 min.
```
→ **Trop de requêtes en peu de temps** → Attendre 1-2 min avant réessai

### 3. "OSM indisponible"
```
⚠️ OSM indisponible — noms des cols potentiellement manquants.
```
→ **Overpass a échoué après 4 tentatives** → Attendez plus longtemps

### 4. "(Serveur indisponible)" dans les logs
```
Points d'eau — ... : Connexion refusée (serveur indisponible)
```
→ **Overpass.de ne répond pas** → Peut-être maintenance ou ban IP

---

## 🛠️ Solutions Avancées

### Pour Développeurs

**Cache Streamlit**:
```python
# Les données OSM sont cachées 24h par défaut
# Forcer un refresh du cache:
streamlit run app.py --logger.level=debug
```

**Bypass Overpass** (local testing):
```python
# Dans ui/components/profile_climbs_view.py
# Commenter l'appel enrichir_cols()
# Les ascensions auront des noms "—" mais ça teste le reste
```

**Configuration Overpass Personnalisée**:
```python
# config/settings.py
OVERPASS_URLS = [
    # Ajouter plus de serveurs Overpass alternatifs
    "https://z.overpass-api.de/api/interpreter",
]
```

---

## 📊 Statistiques Overpass

- 🟩 **Uptime**: ~99% (normal)
- 🔴 **Downtime**: 1-2 fois par mois pour maint (30 min - 2h)
- ⏱️ **Rate Limit**: ~2000 requêtes/jour/IP
- 🕒 **Timeout default**: 25 secondes

---

## 💡 Bonnes Pratiques

1. **Désactiver OSM** si vous n'en avez pas besoin
   → Économise temps et requêtes API

2. **Réutiliser les tracés**
   → Cache local 24h = pas de re-requête

3. **Batch requests**
   → Grouper les uploads au lieu de 1 par 1
   → Réduit la charge Overpass

4. **Vérifier le statut** avant de debugger
   → https://overpass-api.de/status

---

## 📞 Support

Si le problème persiste :
1. Vérifier : https://overpass-api.de/status
2. Attendre 1h (cycle de maint Overpass)
3. Réessayer sans enrichissement OSM
4. Ouvrir issue sur GitHub avec:
   - Heure exacte de l'erreur
   - Message d'erreur complet (logs)
   - Fichier GPX utilisé

---

## ✅ TL;DR

**Erreur Overpass** = Pas critique ✅
- App fonctionne sans noms cols + points d'eau
- Attendez 5-10 minutes
- Réessayez
- Ou désactivez OSM dans sidebar
