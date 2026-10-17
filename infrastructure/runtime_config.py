"""Configuration runtime pour Streamlit et les secrets de déploiement."""

from __future__ import annotations

import os

import streamlit as st


def get_gemini_api_key() -> str:
    """Retourne la clé Gemini depuis l'environnement ou les secrets Streamlit.

    La priorité à l'environnement facilite GitHub Actions et les hébergeurs.
    ``st.secrets`` couvre notamment Streamlit Community Cloud.
    """
    value = os.getenv("GEMINI_API_KEY", "").strip()
    if value:
        return value

    try:
        value = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:
        value = ""
    return value
