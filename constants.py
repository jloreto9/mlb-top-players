"""
constants.py
------------
Mapeo equipo → liga y columnas de display.
Todos los nombres de columna corresponden exactamente a lo que
retorna pybaseball desde FanGraphs (team_batting / team_pitching / team_fielding).

Notas de nomenclatura FanGraphs:
  wRC+   → mayor es mejor  (100 = promedio liga)
  ERA-   → menor es mejor  (100 = promedio liga)  ← FG usa "-" no "+"
  FIP-   → menor es mejor
  xFIP-  → menor es mejor
  Def    → mayor es mejor  (runs defensivos sobre promedio)
  UZR    → mayor es mejor  (ultimate zone rating)
"""

# ── Equipo → Liga ──────────────────────────────────────────────────────────
TEAM_LEAGUE: dict[str, str] = {
    # AL East
    "BAL": "AL", "BOS": "AL", "NYY": "AL",
    "TB":  "AL", "TBR": "AL", "TOR": "AL",
    # AL Central
    "CHW": "AL", "CWS": "AL", "CLE": "AL",
    "DET": "AL", "KC":  "AL", "KCR": "AL", "MIN": "AL",
    # AL West
    "HOU": "AL", "LAA": "AL", "OAK": "AL", "SEA": "AL", "TEX": "AL",
    # NL East
    "ATL": "NL", "MIA": "NL", "NYM": "NL", "PHI": "NL",
    "WSH": "NL", "WSN": "NL",
    # NL Central
    "CHC": "NL", "CIN": "NL", "MIL": "NL", "PIT": "NL", "STL": "NL",
    # NL West
    "ARI": "NL", "AZ":  "NL", "COL": "NL",
    "LAD": "NL", "LA":  "NL",
    "SD":  "NL", "SDP": "NL",
    "SF":  "NL", "SFG": "NL",
}

# ── Columnas individuales — Bateadores ─────────────────────────────────────
# Columnas exactas de pybaseball.batting_stats()
BAT_COLS = [
    "Name", "Team", "G", "PA", "HR", "R", "RBI", "SB",
    "AVG", "OBP", "SLG", "OPS", "ISO", "BABIP",
    "BB%", "K%",
    "wOBA", "wRC+", "WAR",
]

# ── Columnas individuales — Pitchers ───────────────────────────────────────
# Columnas exactas de pybaseball.pitching_stats()
# FanGraphs usa ERA-, FIP-, xFIP- (escala inversa: 100 = promedio, <100 = mejor)
PIT_COLS = [
    "Name", "Team", "W", "L", "G", "GS", "IP",
    "ERA", "ERA-", "FIP", "FIP-", "xFIP", "xFIP-", "WHIP",
    "K/9", "BB/9", "K%", "BB%", "K-BB%",
    "BABIP", "LOB%", "HR/9", "WAR",
]

# ── Colectivas — Bateo por equipo ──────────────────────────────────────────
TBAT_COLS = [
    "Team", "G", "PA", "HR", "R", "RBI", "SB",
    "AVG", "OBP", "SLG", "OPS",
    "wOBA", "wRC+",
    "BB%", "K%", "BABIP", "ISO", "WAR",
]

# ── Colectivas — Pitcheo por equipo ───────────────────────────────────────
TPIT_COLS = [
    "Team", "W", "L", "ERA", "ERA-", "IP",
    "FIP", "FIP-", "xFIP", "xFIP-", "WHIP",
    "K/9", "BB/9", "K%", "BB%", "K-BB%",
    "BABIP", "LOB%", "HR/9", "WAR",
]

# ── Colectivas — Fildeo por equipo ────────────────────────────────────────
# Columnas exactas de pybaseball.team_fielding()
TFIELD_COLS = [
    "Team", "G", "Inn", "PO", "A", "E", "DP",
    "FP%", "DRS", "OAA", "UZR", "UZR/150", "Def", "WAR",
]

# ── Métricas donde MENOR = mejor ──────────────────────────────────────────
LOWER_IS_BETTER = {
    "ERA", "ERA-", "FIP", "FIP-", "xFIP", "xFIP-",
    "WHIP", "BB/9", "HR/9", "BB%", "BABIP",
    "E",    # errores: menos es mejor
}
