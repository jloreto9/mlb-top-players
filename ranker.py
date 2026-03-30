"""
ranker.py
---------
Asigna liga (AL / NL) a cada jugador y genera rankings Top N
por liga para bateadores y pitchers.

La asignación de liga se hace cruzando el equipo más frecuente
del jugador con un diccionario estático de equipos MLB → liga.
"""

import pandas as pd

# ---------------------------------------------------------------------------
# Mapa equipo → liga (2024)
# ---------------------------------------------------------------------------

TEAM_LEAGUE: dict[str, str] = {
    # American League
    "BAL": "AL", "BOS": "AL", "NYY": "AL", "TBR": "AL", "TOR": "AL",  # AL East
    "CWS": "AL", "CLE": "AL", "DET": "AL", "KCR": "AL", "MIN": "AL",  # AL Central
    "HOU": "AL", "LAA": "AL", "OAK": "AL", "SEA": "AL", "TEX": "AL",  # AL West
    # National League
    "ATL": "NL", "MIA": "NL", "NYM": "NL", "PHI": "NL", "WSN": "NL",  # NL East
    "CHC": "NL", "CIN": "NL", "MIL": "NL", "PIT": "NL", "STL": "NL",  # NL Central
    "ARI": "NL", "COL": "NL", "LAD": "NL", "SDP": "NL", "SFG": "NL",  # NL West
}

# Abreviaturas alternativas que Statcast puede usar
TEAM_ALIASES: dict[str, str] = {
    "TB" : "TBR", "KC" : "KCR", "SD" : "SDP", "SF" : "SFG",
    "WAS": "WSN", "WSH": "WSN", "CHW": "CWS", "AZ" : "ARI",
    "LA" : "LAD",
}


def _resolve_team(raw: str) -> str:
    """Normaliza abreviatura de equipo."""
    t = str(raw).upper().strip()
    return TEAM_ALIASES.get(t, t)


def assign_league(df: pd.DataFrame, team_col: str = "league_raw") -> pd.DataFrame:
    """
    Agrega columna 'league' (AL / NL / UNK) basada en el equipo local más frecuente.

    Nota: league_raw viene de home_team en Statcast, que puede ser el equipo
    local del juego, no necesariamente el del jugador. Para rangos cortos esto
    introduce ruido; para temporada completa es muy preciso.
    """
    df = df.copy()
    df["team_norm"] = df[team_col].apply(_resolve_team)
    df["league"]    = df["team_norm"].map(TEAM_LEAGUE).fillna("UNK")
    return df


# ---------------------------------------------------------------------------
# Rankings
# ---------------------------------------------------------------------------

def top_batters(
    df: pd.DataFrame,
    n: int = 10,
    sort_by: str = "xwOBA",
    min_pa: int = 0,
    ascending: bool = False,
) -> dict[str, pd.DataFrame]:
    """
    Retorna Top N bateadores por liga.

    Parámetros
    ----------
    df        : DataFrame de calc_batter_metrics (ya con columna 'league')
    n         : Top N por liga
    sort_by   : Columna de ordenamiento principal (default: xwOBA)
    min_pa    : Filtro mínimo de PA (0 = sin filtro)
    ascending : False = mayor es mejor (xwOBA, OPS), True = menor es mejor

    Retorna
    -------
    {'AL': DataFrame, 'NL': DataFrame}
    """
    df = assign_league(df)

    if min_pa > 0:
        df = df[df["PA"] >= min_pa]

    df = df[df["league"].isin(["AL", "NL"])]
    df = df.dropna(subset=[sort_by])
    df = df.sort_values(sort_by, ascending=ascending)

    cols_display = [
        "player_name", "league", "PA", "HR",
        "AVG", "OBP", "SLG", "OPS",
        "K_pct", "BB_pct",
        "xwOBA", "xBA", "xSLG",
    ]
    cols_display = [c for c in cols_display if c in df.columns]

    result = {}
    for league in ["AL", "NL"]:
        subset = df[df["league"] == league][cols_display].head(n).reset_index(drop=True)
        subset.index += 1  # ranking 1-based
        result[league] = subset

    return result


def top_pitchers(
    df: pd.DataFrame,
    n: int = 10,
    sort_by: str = "xERA",
    min_bf: int = 0,
    ascending: bool = True,
) -> dict[str, pd.DataFrame]:
    """
    Retorna Top N pitchers por liga.

    Parámetros
    ----------
    df        : DataFrame de calc_pitcher_metrics (ya con columna 'league')
    n         : Top N por liga
    sort_by   : Columna de ordenamiento (default: xERA — menor es mejor)
    min_bf    : Filtro mínimo de batters faced
    ascending : True = menor es mejor (xERA, ERA), False = mayor es mejor (K9)

    Retorna
    -------
    {'AL': DataFrame, 'NL': DataFrame}
    """
    df = assign_league(df)

    if min_bf > 0:
        df = df[df["BF"] >= min_bf]

    df = df[df["league"].isin(["AL", "NL"])]
    df = df.dropna(subset=[sort_by])
    df = df.sort_values(sort_by, ascending=ascending)

    cols_display = [
        "player_name", "league", "BF", "IP",
        "HR_allowed", "BB", "K",
        "K9", "BB9", "WHIP",
        "ERA_proxy", "K_pct", "BB_pct",
        "xwOBA_against", "xERA",
        "avg_velo", "avg_spin",
    ]
    cols_display = [c for c in cols_display if c in df.columns]

    result = {}
    for league in ["AL", "NL"]:
        subset = df[df["league"] == league][cols_display].head(n).reset_index(drop=True)
        subset.index += 1
        result[league] = subset

    return result
