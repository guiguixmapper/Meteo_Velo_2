"""
ui/styles/theme.py
==================
Thème Strava — orange #FC4C02, compatible light ET dark mode Streamlit.
"""

CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
  }

  footer { visibility: hidden; }
  .block-container { padding-top: 2.5rem !important; padding-bottom: 2rem !important; }

  /* ── Palette Strava — variables adaptatives ── */
  :root {
    --strava:       #FC4C02;
    --strava-dark:  #E03D00;
    --strava-light: rgba(252,76,2,0.08);
    --radius: 12px;
    /* Couleurs adaptatives : héritent du thème Streamlit */
    --text-primary:   inherit;
    --text-muted:     rgba(128,128,128,0.7);
    --border-color:   rgba(128,128,128,0.18);
    --bg-card:        rgba(128,128,128,0.04);
    --bg-hover:       rgba(128,128,128,0.07);
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.08),0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.10),0 2px 4px rgba(0,0,0,0.06);
  }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] { padding-top: 0 !important; }
  [data-testid="stSidebar"] hr {
    margin: 0.5rem 0 !important;
    border-color: rgba(128,128,128,0.2) !important;
    opacity: 1 !important;
  }
  [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3 { font-size: 0.85rem !important; font-weight: 700 !important; }
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] p   { font-size: 0.82rem !important; }

  /* Section labels sidebar — orange Strava */
  .sb-section {
    font-size: 0.62rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 1px; color: #FC4C02 !important;
    margin: 14px 0 5px 0;
  }

  /* Export button */
  .export-btn a {
    display: block; text-align: center;
    background: #FC4C02; color: white !important;
    padding: 11px 16px; border-radius: 12px;
    text-decoration: none; font-weight: 800; font-size: 0.85rem;
    transition: all 0.15s ease;
    box-shadow: 0 2px 8px rgba(252,76,2,0.35);
  }
  .export-btn a:hover { background: #E03D00; transform: translateY(-1px); }

  /* ── Score banner ── */
  .score-banner {
    display: flex; align-items: stretch;
    border-radius: 12px; overflow: hidden;
    box-shadow: var(--shadow-md);
    margin-bottom: 8px;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
  }

  /* Bloc score — toujours orange, texte toujours blanc */
  .score-left {
    background: #FC4C02;
    color: white !important; padding: 10px 14px; min-width: 120px;
    display: flex; flex-direction: column; justify-content: center; flex-shrink: 0;
    position: relative; overflow: hidden;
  }
  .score-left::after {
    content: ""; position: absolute; right: -20px; top: -20px;
    width: 90px; height: 90px; border-radius: 50%;
    background: rgba(255,255,255,0.10);
  }
  .score-left * { color: white !important; }
  .score-left .score-num {
    font-size: 2rem; font-weight: 900; line-height: 1;
    letter-spacing: -1px; position: relative; z-index: 1;
  }
  .score-left .score-num span { font-size: 1.1rem; font-weight: 600; opacity: 0.8; }
  .score-left .score-lbl {
    font-size: 0.62rem; font-weight: 700; margin-top: 2px;
    opacity: 0.95; text-transform: uppercase; letter-spacing: 0.3px;
    position: relative; z-index: 1;
  }
  .score-left .score-badges { display: flex; gap: 3px; margin-top: 4px; flex-wrap: wrap; position: relative; z-index: 1; }
  .score-left .score-badge {
    background: rgba(255,255,255,0.22); border-radius: 20px;
    padding: 1px 6px; font-size: 0.60rem; font-weight: 600;
    border: 1px solid rgba(255,255,255,0.25);
  }

  /* Cellules métriques — couleurs adaptatives */
  .metric-grid { display: flex; flex: 1; overflow: hidden; }
  .metric-cell {
    flex: 1; min-width: 60px; text-align: center; padding: 8px 4px;
    border-right: 1px solid var(--border-color);
    display: flex; flex-direction: column; justify-content: center;
    transition: background 0.12s;
  }
  .metric-cell:last-child { border-right: none; }
  .metric-cell:hover { background: var(--bg-hover); }

  /* Valeurs — héritent la couleur du thème Streamlit (blanc en dark, noir en light) */
  .metric-cell .mv {
    font-size: 1.1rem; font-weight: 900;
    letter-spacing: -0.3px; line-height: 1;
    /* PAS de color fixe — hérite automatiquement */
  }
  .metric-cell .mu {
    font-size: 0.58rem; font-weight: 600; margin-top: 1px;
    color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.3px;
  }
  .metric-cell .ml { font-size: 0.6rem; margin-top: 3px; color: var(--text-muted); }

  /* Vitesse moyenne en orange Strava */
  .metric-cell .mv.orange { color: #FC4C02 !important; }

  /* ── Soleil pill ── */
  .soleil-row {
    display: inline-flex; gap: 20px; align-items: center; flex-wrap: wrap;
    background: rgba(252,76,2,0.06);
    border: 1px solid rgba(252,76,2,0.2);
    border-radius: 12px; padding: 10px 18px; margin: 8px 0 14px;
    box-shadow: var(--shadow-sm);
  }
  /* Texte adaptatif */
  .soleil-item .s-val { font-size: 0.9rem; font-weight: 800; }
  .soleil-item .s-lbl {
    font-size: 0.6rem; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.5px;
  }

  /* ── Tabs — onglet actif orange ── */
  [data-testid="stTabs"] [data-testid="stTab"] {
    font-size: 0.83rem !important; font-weight: 700 !important;
    padding: 8px 18px !important; background: transparent !important;
    opacity: 0.55 !important; transition: all 0.15s !important;
  }
  [data-testid="stTabs"] [data-testid="stTab"]:hover { opacity: 0.85 !important; }
  [data-testid="stTabs"] [aria-selected="true"] {
    opacity: 1 !important;
    color: #FC4C02 !important;
  }
  [data-testid="stTabsContent"] { padding-top: 16px !important; }

  /* ── Buttons ── */
  .stButton > button {
    border-radius: 12px !important; font-weight: 700 !important;
    font-size: 0.83rem !important; padding: 8px 18px !important;
    border: 2px solid var(--border-color) !important;
    background: var(--bg-card) !important;
    transition: all 0.15s ease !important;
    box-shadow: var(--shadow-sm) !important;
  }
  .stButton > button:hover {
    border-color: #FC4C02 !important;
    color: #FC4C02 !important;
    background: rgba(252,76,2,0.06) !important;
    transform: translateY(-1px) !important;
  }

  /* ── Expander ── */
  [data-testid="stExpander"] {
    border: 1px solid var(--border-color) !important;
    border-radius: 12px !important; overflow: hidden;
    box-shadow: var(--shadow-sm) !important;
  }
  [data-testid="stExpander"] summary {
    font-size: 0.83rem !important; font-weight: 700 !important;
    padding: 10px 14px !important;
    background: var(--bg-card) !important;
  }
  [data-testid="stExpander"] summary:hover {
    background: rgba(252,76,2,0.05) !important;
  }

  /* ── DataFrames ── */
  [data-testid="stDataFrame"] {
    border-radius: 12px !important; overflow: hidden;
    border: 1px solid var(--border-color) !important;
    box-shadow: var(--shadow-sm) !important;
  }

  /* ── Alerts ── */
  .stAlert { border-radius: 12px !important; font-size: 0.83rem !important; }

  /* ── Captions ── */
  .stCaption, [data-testid="stCaptionContainer"] {
    font-size: 0.73rem !important;
    color: var(--text-muted) !important;
  }

  /* ── Dividers ── */
  hr { border-color: var(--border-color) !important; }

  /* ── Slider accent Strava ── */
  /*[data-testid="stSlider"] > div > div > div { background: #FC4C02 !important; }*/
  
  /* ── Sidebar header border ── */
  .sb-header-border {
    border-bottom: 2px solid #FC4C02;
    padding-bottom: 12px; margin-bottom: 8px;
  }

  /* ── Strava card (composant réutilisable) ── */
  .strava-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px; padding: 16px 20px;
    box-shadow: var(--shadow-sm);
    transition: box-shadow 0.15s;
  }
  .strava-card:hover { box-shadow: var(--shadow-md); }
  .strava-card .card-label {
    font-size: 0.62rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.8px; color: var(--text-muted); margin-bottom: 4px;
  }
  .strava-card .card-value {
    font-size: 1.8rem; font-weight: 900; letter-spacing: -1px; line-height: 1;
    /* Adaptatif — hérite du thème */
  }
  .strava-card .card-unit  { font-size: 0.8rem; font-weight: 600; color: var(--text-muted); margin-left: 3px; }
  .strava-card .card-sub   { font-size: 0.72rem; color: var(--text-muted); margin-top: 4px; }

  @media (max-width: 768px) {
    .metric-cell .mv { font-size: 1.15rem; }
    .score-left { min-width: 110px; padding: 14px; }
    .score-left .score-num { font-size: 2.2rem; }
  }
</style>
"""
