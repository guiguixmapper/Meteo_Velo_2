"""
infrastructure/gemini_client.py
=================================
Appels Google Gemini pour le briefing coach.
"""

import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)


def generer_briefing(
    api_key:         str,
    dist_tot:        float,
    d_plus:          float,
    temps_s:         float,
    calories:        int,
    score:           dict,
    ascensions:      list,
    analyse_meteo:   dict,
    resultats:       list,
    heure_depart:    str,
    heure_arrivee:   str,
    vitesse_moyenne: float,
    infos_soleil:    dict,
    contexte_date:   str,
    nb_points_eau:   int  = 0,
    uv_pollen:       dict = None,
) -> str | None:
    if not api_key:
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        # Préparer les données
        from core.services.nutrition_service import calculer_hydratation, calculer_glucides

        dist_km  = round(dist_tot / 1000, 1)
        d_plus_m = int(d_plus)
        duree_h  = round(temps_s / 3600, 2)
        dh       = int(duree_h)
        dm       = int((duree_h % 1) * 60)

        lever_str   = infos_soleil["lever"].strftime("%H:%M")   if infos_soleil else "inconnue"
        coucher_str = infos_soleil["coucher"].strftime("%H:%M") if infos_soleil else "inconnue"

        cols_str = ("\n".join([
            f"  • {a.get('Nom','—')} ({a['Catégorie']}) — "
            f"Km {a['Départ (km)']}→{a['Sommet (km)']}, "
            f"{a['Longueur']}, D+ {a['Dénivelé']}, "
            f"pente moy. {a['Pente moy.']}, max {a['Pente max']}, "
            f"sommet {a.get('Alt. sommet','?')}, "
            f"arrivée sommet vers {a.get('Arrivée sommet','?')}"
            for a in ascensions
        ]) if ascensions else "  Aucune ascension catégorisée — parcours principalement roulant.")

        valides = [cp for cp in resultats if cp.get("temp_val") is not None]
        if valides:
            t_min = min(cp["temp_val"] for cp in valides)
            t_max = max(cp["temp_val"] for cp in valides)
            t_moy = round(sum(cp["temp_val"] for cp in valides) / len(valides), 1)
            temp_txt = f"{t_min}°C min / {t_moy}°C moy / {t_max}°C max"
            ressentis = [cp["ressenti"] for cp in valides if cp.get("ressenti") is not None]
            ressenti_txt = (f"Wind chill : {min(ressentis)}°C à {max(ressentis)}°C"
                            if ressentis else "Pas de wind chill significatif")
        else:
            t_min = t_max = t_moy = None
            temp_txt = ressenti_txt = "Données indisponibles"

        if analyse_meteo:
            vent_txt = (f"{analyse_meteo['pct_face']}% face / "
                        f"{analyse_meteo['pct_dos']}% dos / "
                        f"{analyse_meteo['pct_cote']}% côté")
            segs = analyse_meteo.get("segments_face", [])
            if segs:
                vent_txt += " — segments face : " + ", ".join(f"Km {s[0]}→{s[1]}" for s in segs)
            if analyse_meteo.get("premier_pluie"):
                cp_p = analyse_meteo["premier_pluie"]
                pluie_txt = f"RISQUE à {cp_p['Heure']} (Km {cp_p['Km']}, {cp_p.get('pluie_pct','?')}%)"
            else:
                pluie_txt = "Aucun risque >50% prévu"
        else:
            vent_txt = pluie_txt = "Indisponible"

        vents    = [cp.get("vent_val") for cp in valides if cp.get("vent_val") is not None]
        vent_max = max(vents) if vents else 0

        uv_txt    = uv_pollen.get("uv_label", "Inconnu")    if uv_pollen else "Indisponible"
        pollen_txt = ", ".join(uv_pollen.get("pollens", [])) if uv_pollen else "Indisponible"
        if uv_pollen and not uv_pollen.get("pollens"):
            pollen_txt = "Aucune alerte"

        eau_txt = (f"{nb_points_eau} point(s) d'eau sur le tracé (OSM)"
                   if nb_points_eau > 0 else "Aucun point d'eau identifié — prévoir toute l'autonomie")

        hydra  = calculer_hydratation(duree_h, t_max)
        glucides = calculer_glucides(duree_h, d_plus_m)
        eau_total    = hydra["eau_total"]
        eau_conseil  = hydra["conseil"]
        carbs_h      = glucides["carbs_h"]
        carbs_total  = glucides["carbs_total"]
        nb_barres    = glucides["nb_barres"]
        nb_gels      = glucides["nb_gels"]

        prompt = f"""
Tu es à la fois un ami de longue date, un grand frère de route et un coach cycliste qui a tout vécu — les cols sous la neige, les crampes à 10 km du sommet, les coups de chaud en plaine. Tu connais la souffrance et le plaisir du vélo de l'intérieur. Tu tutoies le coureur, tu lui parles comme à quelqu'un que tu aimes et que tu respectes. Tu es chaleureux, humain, parfois cash, jamais condescendant. Tu as de l'humour mais tu sais être sérieux quand ça compte. Pas de langue de bois, pas de formules vides — chaque mot que tu écris, c'est ce que tu dirais vraiment à quelqu'un avant qu'il parte seul sur la route.

Règles absolues :
- Sois précis et chiffré — chaque conseil s'appuie sur une donnée concrète
- N'utilise que les données fournies, ne les répète jamais dans deux sections
- Le vent DOIT apparaître dans le plan de course : cite les segments exacts de vent de face/dos et leur impact tactique
- Commence directement par ## 📋 Résumé, sans phrase d'intro ni salutation générique

═══════════════════════════════════════════════
DONNÉES DE LA SORTIE
═══════════════════════════════════════════════
Date         : {contexte_date}
Distance     : {dist_km} km  |  D+ : {d_plus_m} m
Durée est.   : {dh}h{dm:02d}  |  Départ : {heure_depart}  |  Arrivée : {heure_arrivee}
Vitesse moy. : {vitesse_moyenne} km/h  |  Calories : {calories} kcal
Score        : {score['label']} ({score['total']}/10)

ASCENSIONS
{cols_str}

MÉTÉO
Températures : {temp_txt}
Ressenti     : {ressenti_txt}
Vent         : {vent_txt}  (max {vent_max} km/h)
Pluie        : {pluie_txt}
UV           : {uv_txt}
Pollen       : {pollen_txt}
Lever/Coucher: {lever_str} / {coucher_str}

LOGISTIQUE
Points d'eau : {eau_txt}
Eau calculée : {eau_total} L ({eau_conseil})
Glucides     : {carbs_total} g ({carbs_h}g/h) → {nb_barres} barres (40g) ou {nb_gels} gels (25g)

═══════════════════════════════════════════════
BRIEFING — RESPECTE EXACTEMENT CETTE STRUCTURE
═══════════════════════════════════════════════

## 📋 Résumé
3 phrases max. Accrocheur, pas bateau. Distance, D+, durée, départ/arrivée, niveau réel.
Si les noms de cols permettent d'identifier un massif ou une région, cite-le avec le ton d'un local.
Donne le ton de la sortie en une phrase qui claque.

---

## 🌤️ Météo & Équipement

**Conditions du jour**
Synthèse température en 2 phrases.

**Vent**
Section dédiée — obligatoire même si vent faible.
Données : {vent_txt} (rafales max {vent_max} km/h).
Le coureur est SEUL : vent de face → position aéro, baisser les coudes, ne pas se battre.
Vent de dos → récupérer ou relancer. Vent de côté → vigilance trajectoire en descente.
Verdict global : contrainte majeure ou facteur mineur ce jour ?

**Tenue**
Précis : chaque pièce vestimentaire pour t_min={t_min}°C au départ.
Coupe-vent si descentes à haute altitude.

**Alertes**
- Pluie : {pluie_txt}. Conduite à tenir concrète.
- UV {uv_txt} : crème SPF adapté si UV ≥ 3, renouvellement toutes les 2h.
- Pollen {pollen_txt} : conseils pratiques si alerte.
- Éclairage : si départ avant {lever_str} ou arrivée après {coucher_str}.
- Wind chill {ressenti_txt} : alerte si <5°C.
Note : intègre ces données naturellement, ne les recopie pas entre guillemets.

---

## ⚡ Plan de course

Phases chronologiques avec km et heures estimées.
Pour chaque phase : effort, raison (vent/pente/chaleur/fatigue), conseil tactique.
Pour chaque ascension : heure d'attaque, stratégie montée, gestion descente.
Le coureur est SEUL — pas de suggestion de roue ou d'abri derrière quelqu'un.
Données vent : {vent_txt}
Identifie 2 moments pour "appuyer" et 2 moments pour "lever le pied".
Une phrase d'ambiance par phase.

---

## 🍌 Ravitaillement

**Eau** : {eau_total} L — {eau_conseil}
{"⚠️ Électrolytes obligatoires (chaleur)." if t_max is not None and t_max >= 25 else ""}
{eau_txt}
Si points d'eau disponibles : stratégie remplissage aux km précis.

**Énergie** : {carbs_total} g sur {dh}h{dm:02d}
Option A : {nb_barres} barres (40g gl.)
Option B : {nb_gels} gels (25g) + 1-2 bananes
Conseil : solide 1ère moitié, gel/liquide 2ème moitié.
Rythme : 1 prise toutes les 30 min dès la 1ère heure.

---

## ✅ Les 3 priorités de cette sortie

Exactement 3 points liés aux données fournies.
Format : **[Thème]** — action concrète et chiffrée, pourquoi en demi-phrase.
Direct, presque brutal — c'est ce qu'un bon DS dirait vraiment.
"""
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        logger.error(f"Erreur Gemini : {e}")
        raise e
