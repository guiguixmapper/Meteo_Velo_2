"""
ui/components/export.py
========================
Génération du carnet de route HTML/PDF.
"""

import base64
import re
from datetime import datetime
from ui.components.profile_view import creer_figure_profil, creer_figure_col


def generer_html_resume(score, ascensions, resultats, dist_tot, d_plus, d_moins,
                        temps_s, heure_depart, heure_arr, vitesse_plat, vit_moy_reelle,
                        calories, carte, df_profil, ref_val, mode, poids, briefing_ia=None) -> bytes:

    dh = int(temps_s // 3600); dm = int((temps_s % 3600) // 60)

    cols_html = ""
    for a in ascensions:
        nom = a.get("Nom", "—")
        cols_html += (
            f"<tr><td>{a['Catégorie']}</td><td>{nom if nom != '—' else ''}</td>"
            f"<td>{a['Départ (km)']} km</td><td>{a['Longueur']}</td><td>{a['Dénivelé']}</td>"
            f"<td>{a['Pente moy.']}</td><td>{a.get('Temps col','—')}</td>"
            f"<td>{a.get('Arrivée sommet','—')}</td></tr>"
        )

    meteo_html = ""
    for cp in [c for c in resultats if c.get("temp_val") is not None]:
        t = cp.get('temp_val')
        meteo_html += (
            f"<tr><td>{cp['Heure']}</td><td>{cp['Km']} km</td>"
            f"<td>{cp.get('Ciel','—')}</td><td>{f'{t}°C' if t else '—'}</td>"
            f"<td>{cp.get('Pluie','—')}</td><td>{cp.get('vent_val','—')} km/h</td>"
            f"<td>{cp.get('effet','—')}</td></tr>"
        )

    b64_map    = base64.b64encode(carte.get_root().render().encode('utf-8')).decode('utf-8')
    iframe_map = (f'<iframe src="data:text/html;base64,{b64_map}" '
                  f'style="width:100%;height:800px;border:1px solid #e2e8f0;border-radius:8px;"></iframe>')

    fig_profil  = creer_figure_profil(df_profil, ascensions, vitesse_plat, ref_val, mode, poids)
    html_profil = fig_profil.to_html(full_html=False, include_plotlyjs='cdn')

    html_profils_cols = ""
    if ascensions:
        html_profils_cols = "<h2>🔍 Profils des montées</h2>"
        for asc in ascensions:
            fig_col = creer_figure_col(df_profil, asc)
            if fig_col:
                html_profils_cols += fig_col.to_html(full_html=False, include_plotlyjs=False)

    html_briefing = ""
    if briefing_ia:
        texte = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', briefing_ia).replace('\n', '<br>')
        html_briefing = f'<h2>🎙️ Le Briefing du Coach IA</h2><div class="ia-box">{texte}</div>'

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Roadbook Velo</title>
<style>
  body{{font-family:Arial,sans-serif;padding:32px;color:#1e293b;max-width:1200px;margin:auto}}
  h1{{color:#0f766e;border-bottom:3px solid #0f766e;padding-bottom:8px;margin-top:0}}
  h2{{color:#0f766e;margin-top:35px}}
  .score{{background:#0f766e;color:white;border-radius:10px;padding:14px 20px;
          font-size:1.1rem;font-weight:700;margin:12px 0;display:inline-block}}
  .grid{{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0}}
  .card{{background:#f1f5f9;border-radius:8px;padding:12px 18px;text-align:center;flex:1;min-width:120px}}
  .card .v{{font-size:1.4rem;font-weight:700;color:#0f766e}}
  .card .l{{font-size:.72rem;color:#64748b;margin-top:3px}}
  .ia-box{{background:#f8fafc;padding:25px;border-radius:12px;border-left:6px solid #22c55e;
           color:#1e293b;font-size:1.05rem;line-height:1.6;margin-top:15px}}
  table{{width:100%;border-collapse:collapse;margin-top:10px;font-size:.83rem}}
  th{{background:#0f766e;color:white;padding:8px;text-align:left}}
  td{{padding:6px 8px;border-bottom:1px solid #e2e8f0}}
  tr:nth-child(even) td{{background:#f8fafc}}
  .btn-print{{background:#0d9488;color:white;border:none;padding:12px 24px;
              font-size:1.1rem;border-radius:8px;cursor:pointer;font-weight:bold;
              float:right;box-shadow:0 4px 6px rgba(0,0,0,0.1)}}
  @media print{{
    .btn-print{{display:none!important}}
    body{{padding:0;max-width:100%}}
    .score,.card,th,.ia-box{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
  }}
</style></head><body>
<button onclick="window.print()" class="btn-print">📄 Enregistrer en PDF</button>
<h1>🚴‍♂️ Carnet de route détaillé</h1>
<p>Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} · Départ : {heure_depart.strftime('%d/%m/%Y %H:%M')}</p>
<div class="score">{score['label']} — {score['total']}/10 &nbsp;|&nbsp;
  🌤️ {score['score_meteo']}/6 &nbsp;|&nbsp; 🏔️ {score['score_cols']}/4</div>
<div class="grid">
  <div class="card"><div class="v">{round(dist_tot/1000,1)} km</div><div class="l">📏 Distance</div></div>
  <div class="card"><div class="v">{int(d_plus)} m</div><div class="l">⬆️ D+</div></div>
  <div class="card"><div class="v">{int(d_moins)} m</div><div class="l">⬇️ D−</div></div>
  <div class="card"><div class="v">{dh}h{dm:02d}m</div><div class="l">⏱️ Durée</div></div>
  <div class="card"><div class="v">{heure_arr.strftime('%H:%M')}</div><div class="l">🏁 Arrivée</div></div>
  <div class="card"><div class="v" style="color:#059669">{vit_moy_reelle} km/h</div><div class="l">🚴 Moy. réelle</div></div>
  <div class="card"><div class="v">{calories} kcal</div><div class="l">🔥 Calories</div></div>
</div>
<h2>🗺️ Carte du parcours</h2>{iframe_map}
<h2>⛰️ Profil global</h2>{html_profil}
<h2>🏔️ Ascensions</h2>
{"<p>Aucune difficulté catégorisée.</p>" if not ascensions else
 "<table><tr><th>Cat.</th><th>Nom</th><th>Départ</th><th>Long.</th><th>D+</th>"
 "<th>Pente</th><th>Temps</th><th>Arrivée</th></tr>" + cols_html + "</table>"}
{html_profils_cols}
<h2>🌤️ Météo</h2>
{"<p>Données indisponibles.</p>" if not meteo_html else
 "<table><tr><th>Heure</th><th>Km</th><th>Ciel</th><th>Temp</th>"
 "<th>Pluie</th><th>Vent</th><th>Effet</th></tr>" + meteo_html + "</table>"}
{html_briefing}
</body></html>""".encode("utf-8")
