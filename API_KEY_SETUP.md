# Configuration de la clé Gemini

La clé n'est pas enregistrée dans le dépôt. L'application lit `GEMINI_API_KEY` côté serveur.

## Streamlit Community Cloud (recommandé)

1. Ouvrir l'application dans Streamlit Cloud.
2. Aller dans **Settings → Secrets**.
3. Ajouter exactement :

```toml
GEMINI_API_KEY = "votre_cle_gemini"
```

4. Enregistrer puis redémarrer l'application.

Après cela, le champ de clé dans l'interface n'est plus nécessaire. La clé reste côté serveur et n'est pas affichée dans l'interface.

## GitHub Actions ou autre hébergeur

Créer un secret de dépôt nommé `GEMINI_API_KEY` dans **Settings → Secrets and variables → Actions**, puis l'injecter comme variable d'environnement au processus Streamlit :

```yaml
env:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

Ne jamais mettre la valeur réelle dans un fichier commité, une issue, un message de commit ou ce document.

## Développement local

Créer un fichier `.streamlit/secrets.toml` non versionné :

```toml
GEMINI_API_KEY = "votre_cle_gemini"
```

La clé Overpass n'est pas requise : les serveurs Overpass utilisés par l'application sont publics. Le bouton **🔄 Relancer les requêtes Overpass** vide le cache OSM et force une nouvelle requête.
