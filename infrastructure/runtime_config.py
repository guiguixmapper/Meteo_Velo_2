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


def render_overpass_control() -> None:
    """Affiche le bouton de relance manuelle des requêtes OSM/Overpass."""
    st.sidebar.markdown("### 📡 Données cartographiques")
    st.sidebar.caption(
        "Overpass est interrogé automatiquement lorsque l'enrichissement OSM est activé."
    )
    if st.sidebar.button(
        "🔄 Relancer les requêtes Overpass",
        width="stretch",
        help="Vide le cache OSM puis relance les requêtes au prochain calcul.",
    ):
        st.session_state["overpass_refresh_requested"] = True
        st.rerun()


def consume_overpass_refresh() -> bool:
    """Vide les caches OSM si l'utilisateur a demandé une relance."""
    requested = bool(st.session_state.pop("overpass_refresh_requested", False))
    if not requested:
        return False

    from infrastructure.osm_client import (
        _requete_osm_around,
        recuperer_points_eau,
    )

    _requete_osm_around.clear()
    recuperer_points_eau.clear()
    return True
