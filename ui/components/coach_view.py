"""
ui/components/coach_view.py
============================
Onglet Coach IA — génération et affichage du briefing Gemini.
"""

import streamlit as st
from datetime import date
from infrastructure.gemini_client import generer_briefing


def render_coach_view(gemini_key, dist_tot, d_plus, temps_s, calories, score,
                      ascensions, analyse_meteo, resultats, heure_dep, heure_arr,
                      vit_moy_reelle, infos_soleil, date_dep, points_eau, uv_pollen):

    st.subheader("🎙️ Le Briefing du Pote de Sortie")
    st.markdown("Analyse personnalisée par Gemini : météo, gestion de l'effort, équipement et ravitaillement.")

    if not gemini_key:
        st.info("👈 **Pour activer l'analyse**, entrez votre clé API Gemini dans les Options avancées.")
        return

    if "briefing_ia" not in st.session_state:
        st.session_state.briefing_ia = None

    if st.button("💬 Générer ou Actualiser le briefing", width='stretch'):
        with st.spinner("Analyse en cours..."):
            try:
                jours_fr = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
                mois_fr  = ["", "janvier", "février", "mars", "avril", "mai", "juin",
                             "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
                delta = (date_dep - date.today()).days
                if delta == 0:
                    contexte_date = "Aujourd'hui"
                elif delta == 1:
                    contexte_date = "Demain"
                else:
                    contexte_date = f"le {jours_fr[date_dep.weekday()]} {date_dep.day} {mois_fr[date_dep.month]} {date_dep.year}"

                briefing = generer_briefing(
                    api_key=gemini_key,
                    dist_tot=dist_tot, d_plus=d_plus, temps_s=temps_s,
                    calories=calories, score=score, ascensions=ascensions,
                    analyse_meteo=analyse_meteo, resultats=resultats,
                    heure_depart=heure_dep.strftime('%H:%M'),
                    heure_arrivee=heure_arr.strftime('%H:%M'),
                    vitesse_moyenne=vit_moy_reelle,
                    infos_soleil=infos_soleil, contexte_date=contexte_date,
                    nb_points_eau=len(points_eau), uv_pollen=uv_pollen,
                )
                if briefing:
                    st.session_state.briefing_ia = briefing
            except Exception as e:
                st.error(f"❌ Erreur Gemini : {e}")

    if st.session_state.briefing_ia:
        st.success("✅ Briefing prêt !")
        st.markdown(f"""
        <div style="background-color:#f8fafc; padding:25px; border-radius:12px;
                    border-left:6px solid #22c55e; color:#1e293b;
                    font-size:1.05rem; line-height:1.6;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            {st.session_state.briefing_ia}
        </div>""", unsafe_allow_html=True)
