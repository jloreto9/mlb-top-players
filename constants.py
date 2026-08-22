"""
constants.py
------------
Mapeo de equipos, ligas, columnas de display, métricas Statcast y configuraciones de Fantasy Baseball.
"""

# ── Equipo → Liga (Abreviaturas, Nombres y Ciudades) ─────────────────────────
TEAM_LEAGUE: dict[str, str] = {
    # AL East
    "BAL": "AL", "BALTIMORE": "AL", "BALTIMORE ORIOLES": "AL",
    "BOS": "AL", "BOSTON": "AL", "BOSTON RED SOX": "AL",
    "NYY": "AL", "NEW YORK YANKEES": "AL",
    "TB": "AL", "TBR": "AL", "TAMPA BAY": "AL", "TAMPA BAY RAYS": "AL",
    "TOR": "AL", "TORONTO": "AL", "TORONTO BLUE JAYS": "AL",
    
    # AL Central
    "CHW": "AL", "CWS": "AL", "CHICAGO WHITE SOX": "AL",
    "CLE": "AL", "CLEVELAND": "AL", "CLEVELAND GUARDIANS": "AL", "CLEVELAND INDIANS": "AL",
    "DET": "AL", "DETROIT": "AL", "DETROIT TIGERS": "AL",
    "KC": "AL", "KCR": "AL", "KANSAS CITY": "AL", "KANSAS CITY ROYALS": "AL",
    "MIN": "AL", "MINNESOTA": "AL", "MINNESOTA TWINS": "AL",
    
    # AL West
    "HOU": "AL", "HOUSTON": "AL", "HOUSTON ASTROS": "AL",
    "LAA": "AL", "LOS ANGELES ANGELS": "AL", "ANAHEIM": "AL",
    "OAK": "AL", "ATH": "AL", "ATHLETICS": "AL", "OAKLAND": "AL", "OAKLAND ATHLETICS": "AL", "SAC": "AL",
    "SEA": "AL", "SEATTLE": "AL", "SEATTLE MARINERS": "AL",
    "TEX": "AL", "TEXAS": "AL", "TEXAS RANGERS": "AL",
    
    # NL East
    "ATL": "NL", "ATLANTA": "NL", "ATLANTA BRAVES": "NL",
    "MIA": "NL", "MIAMI": "NL", "MIAMI MARLINS": "NL", "FLORIDA": "NL",
    "NYM": "NL", "NEW YORK METS": "NL",
    "PHI": "NL", "PHILADELPHIA": "NL", "PHILADELPHIA PHILLIES": "NL",
    "WSH": "NL", "WSN": "NL", "WASHINGTON": "NL", "WASHINGTON NATIONALS": "NL",
    
    # NL Central
    "CHC": "NL", "CHICAGO CUBS": "NL",
    "CIN": "NL", "CINCINNATI": "NL", "CINCINNATI REDS": "NL",
    "MIL": "NL", "MILWAUKEE": "NL", "MILWAUKEE BREWERS": "NL",
    "PIT": "NL", "PITTSBURGH": "NL", "PITTSBURGH PIRATES": "NL",
    "STL": "NL", "ST. LOUIS": "NL", "ST. LOUIS CARDINALS": "NL",
    
    # NL West
    "ARI": "NL", "AZ": "NL", "ARIZONA": "NL", "ARIZONA DIAMONDBACKS": "NL",
    "COL": "NL", "COLORADO": "NL", "COLORADO ROCKIES": "NL",
    "LAD": "NL", "LOS ANGELES DODGERS": "NL",
    "SD": "NL", "SDP": "NL", "SAN DIEGO": "NL", "SAN DIEGO PADRES": "NL",
    "SF": "NL", "SFG": "NL", "SAN FRANCISCO": "NL", "SAN FRANCISCO GIANTS": "NL",

    # Ciudades ambiguas (default razonable para BRef / Savant)
    "NEW YORK": "AL",
    "LOS ANGELES": "NL",
    "CHICAGO": "AL",
}


def resolve_team_league(team_str: str | None) -> str:
    """Resuelve la liga de un equipo o cadena compuesta (ej: 'Athletics,Cincinnati' -> 'NL')."""
    if team_str is None:
        return "UNK"
    s = str(team_str).strip()
    if not s or s.lower() in ("nan", "none", "unk", "tot"):
        return "UNK"
    if s.upper() in TEAM_LEAGUE:
        return TEAM_LEAGUE[s.upper()]
    # Si tiene comas (jugador traspasado), evaluar el último equipo
    if "," in s:
        last_team = s.split(",")[-1].strip()
        if last_team.upper() in TEAM_LEAGUE:
            return TEAM_LEAGUE[last_team.upper()]
    # Buscar tokens
    for token in reversed(s.replace(",", " ").split()):
        if token.upper() in TEAM_LEAGUE:
            return TEAM_LEAGUE[token.upper()]
    return "MLB"

# ── Nombres completos de equipos MLB (Abreviatura -> Nombre) ────────────────
MLB_TEAMS: dict[str, str] = {
    "BAL": "Baltimore Orioles",
    "BOS": "Boston Red Sox",
    "NYY": "New York Yankees",
    "TB":  "Tampa Bay Rays",
    "TBR": "Tampa Bay Rays",
    "TOR": "Toronto Blue Jays",
    "CHW": "Chicago White Sox",
    "CWS": "Chicago White Sox",
    "CLE": "Cleveland Guardians",
    "DET": "Detroit Tigers",
    "KC":  "Kansas City Royals",
    "KCR": "Kansas City Royals",
    "MIN": "Minnesota Twins",
    "HOU": "Houston Astros",
    "LAA": "Los Angeles Angels",
    "OAK": "Oakland Athletics",
    "ATH": "Athletics",
    "SEA": "Seattle Mariners",
    "TEX": "Texas Rangers",
    "ATL": "Atlanta Braves",
    "MIA": "Miami Marlins",
    "NYM": "New York Mets",
    "PHI": "Philadelphia Phillies",
    "WSH": "Washington Nationals",
    "WSN": "Washington Nationals",
    "CHC": "Chicago Cubs",
    "CIN": "Cincinnati Reds",
    "MIL": "Milwaukee Brewers",
    "PIT": "Pittsburgh Pirates",
    "STL": "St. Louis Cardinals",
    "ARI": "Arizona Diamondbacks",
    "AZ":  "Arizona Diamondbacks",
    "COL": "Colorado Rockies",
    "LAD": "Los Angeles Dodgers",
    "LA":  "Los Angeles Dodgers",
    "SD":  "San Diego Padres",
    "SDP": "San Diego Padres",
    "SF":  "San Francisco Giants",
    "SFG": "San Francisco Giants",
}

# ── Factores de Parque aproximados (100 = Neutral, >100 = Bateador, <100 = Pitcher) ─
PARK_FACTORS: dict[str, float] = {
    "COL": 112, "CIN": 107, "BOS": 105, "PHI": 104, "LAA": 103,
    "WSH": 102, "KC": 102,  "KCR": 102, "TEX": 102, "BAL": 101,
    "MIL": 101, "ATL": 101, "TOR": 101, "CHC": 101, "ARI": 101,
    "HOU": 100, "NYM": 100, "MIN": 100, "LAD": 99,  "CLE": 99,
    "DET": 98,  "CHW": 98,  "CWS": 98,  "MIA": 97,  "TB": 97,
    "TBR": 97,  "SF": 96,   "SFG": 96,  "SD": 96,   "SDP": 96,
    "OAK": 95,  "ATH": 95,  "NYY": 99,  "SEA": 94,  "PIT": 98,
    "STL": 98,
}

# ── Columnas individuales — Bateadores Estándar ─────────────────────────────
BAT_COLS = [
    "Name", "Team", "Pos", "G", "PA", "HR", "R", "RBI", "SB",
    "AVG", "OBP", "SLG", "OPS", "ISO", "BABIP",
    "BB%", "K%",
    "wOBA", "wRC+", "WAR",
]

# ── Columnas individuales — Bateadores Fantasy ──────────────────────────────
BAT_FANTASY_COLS = [
    "Name", "Team", "Pos", "G", "PA", "R", "HR", "RBI", "SB", "AVG", "OBP",
    "z_R", "z_HR", "z_RBI", "z_SB", "z_AVG", "z_Total", "Fantasy_Rank", "Fantasy_Pts",
]

# ── Columnas individuales — Statcast Bateo ──────────────────────────────────
STATCAST_BAT_COLS = [
    "Name", "Team", "Pos", "PA", "AVG", "xBA", "diff_BA",
    "SLG", "xSLG", "diff_SLG", "wOBA", "xwOBA", "diff_wOBA",
    "EV", "maxEV", "HardHit%", "Barrel%", "SweetSpot%",
]

# ── Columnas individuales — Pitchers Estándar ───────────────────────────────
PIT_COLS = [
    "Name", "Team", "Pos", "W", "L", "G", "GS", "IP",
    "ERA", "ERA-", "FIP", "FIP-", "xFIP", "xFIP-", "WHIP",
    "K/9", "BB/9", "K%", "BB%", "K-BB%",
    "BABIP", "LOB%", "HR/9", "WAR",
]

# ── Columnas individuales — Pitchers Fantasy ────────────────────────────────
PIT_FANTASY_COLS = [
    "Name", "Team", "Pos", "W", "SV", "HLD", "SO", "ERA", "WHIP", "IP",
    "z_W", "z_SV", "z_SO", "z_ERA", "z_WHIP", "z_Total", "Fantasy_Rank", "Fantasy_Pts",
]

# ── Columnas individuales — Statcast Pitching ───────────────────────────────
STATCAST_PIT_COLS = [
    "Name", "Team", "Pos", "IP", "ERA", "xERA", "diff_ERA",
    "FIP", "xFIP", "SIERA", "K%", "BB%", "K-BB%",
    "CSW%", "Stuff+", "Location+", "Pitching+",
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
TFIELD_COLS = [
    "Team", "G", "Inn", "PO", "A", "E", "DP",
    "FP%", "DRS", "OAA", "UZR", "UZR/150", "Def", "WAR",
]

# ── Métricas donde MENOR = mejor ──────────────────────────────────────────
LOWER_IS_BETTER = {
    "ERA", "ERA-", "FIP", "FIP-", "xFIP", "xFIP-", "xERA", "SIERA", "botERA",
    "WHIP", "BB/9", "HR/9", "BB%", "BABIP", "L", "BS", "diff_ERA",
    "E",    # errores: menos es mejor
}

# ── Configuración de Puntuación Fantasy (Puntos por defecto) ───────────────
FANTASY_SCORING_PRESETS = {
    "ESPN Standard": {
        "batting": {
            "1B": 1.0, "2B": 2.0, "3B": 3.0, "HR": 4.0,
            "R": 1.0, "RBI": 1.0, "BB": 1.0, "HBP": 1.0,
            "SB": 1.0, "CS": -1.0, "SO": -1.0,
        },
        "pitching": {
            "IP": 3.0, "W": 5.0, "L": -5.0, "SV": 5.0,
            "SO": 1.0, "H": -1.0, "ER": -2.0, "BB": -1.0, "HBP": -1.0,
            "CG": 3.0, "ShO": 5.0,
        }
    },
    "Yahoo Standard": {
        "batting": {
            "1B": 2.6, "2B": 5.2, "3B": 7.8, "HR": 10.4,
            "R": 1.9, "RBI": 1.9, "BB": 2.6, "HBP": 2.6,
            "SB": 4.2, "CS": -2.8, "SO": 0.0,
        },
        "pitching": {
            "IP": 7.4, "W": 8.0, "L": -4.0, "SV": 10.0,
            "SO": 2.0, "H": -2.6, "ER": -3.0, "BB": -2.6, "HBP": -2.6,
            "CG": 0.0, "ShO": 0.0,
        }
    },
    "FanTrax / Custom Classic": {
        "batting": {
            "1B": 1.0, "2B": 2.0, "3B": 3.0, "HR": 4.0,
            "R": 1.0, "RBI": 1.0, "BB": 1.0, "HBP": 1.0,
            "SB": 2.0, "CS": -1.0, "SO": -0.5,
        },
        "pitching": {
            "IP": 3.0, "W": 5.0, "L": -3.0, "SV": 5.0, "HLD": 3.0,
            "SO": 1.0, "H": -1.0, "ER": -2.0, "BB": -1.0, "HBP": -1.0,
            "CG": 2.5, "ShO": 2.5,
        }
    }
}

