"""
fetcher.py
----------
Descarga y gestión de caché de estadísticas de béisbol MLB:
- Batting / Pitching individuales con métricas avanzadas (FanGraphs / Statcast) y posiciones (MLB Stats API)
- Stats colectivas por equipo (FanGraphs)
- Standings oficiales por división y wild card (MLB Stats API)
- Calendario con lanzadores abridores probables (MLB Stats API)
"""

from __future__ import annotations

import json
import time
from datetime import datetime, date
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from constants import TEAM_LEAGUE, MLB_TEAMS, resolve_team_league, get_team_logo
from utils import clean_ascii_text

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

_NOW_YEAR: int = datetime.now().year
_MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

_FG_API = "https://www.fangraphs.com/api/leaders/major-league/data"
_FG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.fangraphs.com/leaders/major-league",
    "Origin": "https://www.fangraphs.com",
}

DIVISION_NAMES = {
    201: ("AL East", "AL"),
    202: ("AL Central", "AL"),
    200: ("AL West", "AL"),
    204: ("NL East", "NL"),
    205: ("NL Central", "NL"),
    203: ("NL West", "NL"),
}

# ── Helpers de caché ──────────────────────────────────────────────────────────

def _path(key: str, ext: str = "parquet") -> Path:
    return CACHE_DIR / f"{key}.{ext}"


def _expired(path: Path, max_hours: float) -> bool:
    if not path.exists():
        return True
    return (time.time() - path.stat().st_mtime) > max_hours * 3600


def _fg_fetch(params: dict) -> pd.DataFrame:
    """Descarga JSON de FanGraphs."""
    resp = requests.get(_FG_API, params=params, headers=_FG_HEADERS, timeout=25)
    resp.raise_for_status()
    payload = resp.json()
    rows = payload.get("data", payload) if isinstance(payload, dict) else payload
    return pd.DataFrame(rows)


# ── Posiciones de Jugadores (MLB Stats API) ──────────────────────────────────

def get_player_metadata(year: int = _NOW_YEAR, force: bool = False) -> tuple[dict[str, str], dict[str, str]]:
    """
    Retorna dos diccionarios:
    1. {Player_Name: Primary_Position} (ej: 'Aaron Judge': 'RF')
    2. {Player_Name: Official_Team_Name} (ej: 'Aaron Judge': 'New York Yankees', 'Pete Alonso': 'New York Mets')
    Usa la API oficial de MLB y cachea en JSON.
    """
    cache_path = _path(f"player_meta_{year}", ext="json")
    ttl = 12.0 if year >= _NOW_YEAR else 24.0 * 365

    if not force and not _expired(cache_path, ttl):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("positions", {}), data.get("teams", {})
        except Exception:
            pass

    try:
        teams_resp = requests.get(f"{_MLB_API_BASE}/teams?sportId=1", timeout=20)
        teams_list = teams_resp.json().get("teams", []) if teams_resp.status_code == 200 else []
        team_id_to_name = {t["id"]: t["name"] for t in teams_list}

        url = f"{_MLB_API_BASE}/sports/1/players?season={year}"
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        people = resp.json().get("people", [])

        pos_map = {}
        team_map = {}
        for p in people:
            raw_name = p.get("fullName")
            if not raw_name:
                continue
            name = clean_ascii_text(raw_name)
            pos = p.get("primaryPosition", {}).get("abbreviation", "DH")
            pos_map[name] = pos
            pos_map[raw_name] = pos

            tid = p.get("currentTeam", {}).get("id")
            if tid in team_id_to_name:
                tname = team_id_to_name[tid]
                team_map[name] = tname
                team_map[raw_name] = tname

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"positions": pos_map, "teams": team_map}, f, ensure_ascii=False)

        return pos_map, team_map
    except Exception as e:
        print(f"[fetcher] Error obteniendo metadata de jugadores MLB: {e}")
        return {}, {}


def get_player_positions(year: int = _NOW_YEAR, force: bool = False) -> dict[str, str]:
    """Retorna diccionario {Player_Name: Primary_Position} (ej: 'Aaron Judge': 'OF')."""
    return get_player_metadata(year, force)[0]


def get_player_teams(year: int = _NOW_YEAR, force: bool = False) -> dict[str, str]:
    """Retorna diccionario {Player_Name: Official_Team_Name} (ej: 'Aaron Judge': 'New York Yankees')."""
    return get_player_metadata(year, force)[1]


# ── Statcast Expected Stats & Quality of Contact (Baseball Savant) ───────────

def statcast_batting(year: int, force: bool = False) -> pd.DataFrame:
    """
    Descarga estadísticas esperadas y calidad de contacto de Baseball Savant (Statcast).
    Métricas: xBA, xSLG, xwOBA, diff_wOBA, diff_BA, diff_SLG, EV, maxEV, HardHit%, Barrel%, SweetSpot%.
    """
    key = f"statcast_bat_{year}"
    path = _path(key)
    ttl = 12.0 if year >= _NOW_YEAR else 24.0 * 365

    if not force and not _expired(path, ttl):
        print(f"[fetcher] cache -> {path.name}")
        return pd.read_parquet(path)

    try:
        from pybaseball import statcast_batter_expected_stats, statcast_batter_exitvelo_barrels
        print(f"[fetcher] descargando statcast batting {year}...")
        df_exp = statcast_batter_expected_stats(year, 1)
        df_ev = statcast_batter_exitvelo_barrels(year, 1)

        if df_exp is not None and not df_exp.empty:
            df_exp = df_exp.rename(columns={
                "player_id": "mlbID",
                "est_ba": "xBA",
                "est_slg": "xSLG",
                "est_woba": "xwOBA",
                "woba": "wOBA_Savant",
                "ba": "BA_Savant",
                "slg": "SLG_Savant",
            })
            if "BA_Savant" in df_exp.columns and "xBA" in df_exp.columns:
                df_exp["diff_BA"] = (pd.to_numeric(df_exp["BA_Savant"], errors="coerce") - pd.to_numeric(df_exp["xBA"], errors="coerce")).round(3)
            elif "est_ba_minus_ba_diff" in df_exp.columns:
                df_exp["diff_BA"] = pd.to_numeric(df_exp["est_ba_minus_ba_diff"], errors="coerce").round(3)

            if "SLG_Savant" in df_exp.columns and "xSLG" in df_exp.columns:
                df_exp["diff_SLG"] = (pd.to_numeric(df_exp["SLG_Savant"], errors="coerce") - pd.to_numeric(df_exp["xSLG"], errors="coerce")).round(3)
            elif "est_slg_minus_slg_diff" in df_exp.columns:
                df_exp["diff_SLG"] = pd.to_numeric(df_exp["est_slg_minus_slg_diff"], errors="coerce").round(3)

            if "wOBA_Savant" in df_exp.columns and "xwOBA" in df_exp.columns:
                df_exp["diff_wOBA"] = (pd.to_numeric(df_exp["wOBA_Savant"], errors="coerce") - pd.to_numeric(df_exp["xwOBA"], errors="coerce")).round(3)
            elif "est_woba_minus_woba_diff" in df_exp.columns:
                df_exp["diff_wOBA"] = pd.to_numeric(df_exp["est_woba_minus_woba_diff"], errors="coerce").round(3)

            if "last_name, first_name" in df_exp.columns:
                df_exp["Name_Savant"] = df_exp["last_name, first_name"].apply(
                    lambda n: clean_ascii_text(" ".join(reversed([p.strip() for p in n.split(",")])) if "," in str(n) else str(n))
                )

        if df_ev is not None and not df_ev.empty:
            df_ev = df_ev.rename(columns={
                "player_id": "mlbID",
                "avg_hit_speed": "EV",
                "max_hit_speed": "maxEV",
                "ev95percent": "HardHit%",
                "brl_percent": "Barrel%",
                "anglesweetspotpercent": "SweetSpot%",
            })
            ev_cols = ["mlbID", "EV", "maxEV", "HardHit%", "Barrel%", "SweetSpot%"]
            ev_cols = [c for c in ev_cols if c in df_ev.columns]
            if df_exp is not None and not df_exp.empty and "mlbID" in df_exp.columns and "mlbID" in df_ev.columns:
                df_exp = pd.merge(df_exp, df_ev[ev_cols], on="mlbID", how="left")

        if df_exp is not None and not df_exp.empty:
            df_exp.to_parquet(path, index=False)
            return df_exp
        return pd.DataFrame()
    except Exception as e:
        print(f"[fetcher] Error descargando statcast batting {year}: {e}")
        if path.exists():
            return pd.read_parquet(path)
        return pd.DataFrame()


def statcast_pitching(year: int, force: bool = False) -> pd.DataFrame:
    """
    Descarga estadísticas esperadas y calidad de contacto permitido de Baseball Savant (Statcast).
    Métricas: xERA, diff_ERA, xwOBA_against, EV_against, HardHit%_against, Barrel%_against.
    """
    key = f"statcast_pit_{year}"
    path = _path(key)
    ttl = 12.0 if year >= _NOW_YEAR else 24.0 * 365

    if not force and not _expired(path, ttl):
        print(f"[fetcher] cache -> {path.name}")
        return pd.read_parquet(path)

    try:
        from pybaseball import statcast_pitcher_expected_stats, statcast_pitcher_exitvelo_barrels
        print(f"[fetcher] descargando statcast pitching {year}...")
        df_exp = statcast_pitcher_expected_stats(year, 1)
        df_ev = statcast_pitcher_exitvelo_barrels(year, 1)

        if df_exp is not None and not df_exp.empty:
            df_exp = df_exp.rename(columns={
                "player_id": "mlbID",
                "xera": "xERA",
                "era_minus_xera_diff": "diff_ERA",
                "est_woba": "xwOBA_against",
            })
            if "last_name, first_name" in df_exp.columns:
                df_exp["Name_Savant"] = df_exp["last_name, first_name"].apply(
                    lambda n: clean_ascii_text(" ".join(reversed([p.strip() for p in n.split(",")])) if "," in str(n) else str(n))
                )

        if df_ev is not None and not df_ev.empty:
            df_ev = df_ev.rename(columns={
                "player_id": "mlbID",
                "avg_hit_speed": "EV_against",
                "ev95percent": "HardHit%_against",
                "brl_percent": "Barrel%_against",
            })
            ev_cols = ["mlbID", "EV_against", "HardHit%_against", "Barrel%_against"]
            ev_cols = [c for c in ev_cols if c in df_ev.columns]
            if df_exp is not None and not df_exp.empty and "mlbID" in df_exp.columns and "mlbID" in df_ev.columns:
                df_exp = pd.merge(df_exp, df_ev[ev_cols], on="mlbID", how="left")

        if df_exp is not None and not df_exp.empty:
            df_exp.to_parquet(path, index=False)
            return df_exp
        return pd.DataFrame()
    except Exception as e:
        print(f"[fetcher] Error descargando statcast pitching {year}: {e}")
        if path.exists():
            return pd.read_parquet(path)
        return pd.DataFrame()


# ── Bateadores y Pitchers Individuales ────────────────────────────────────────

def batting(year: int, force: bool = False) -> pd.DataFrame:
    """
    Leaderboard individual de bateadores con métricas completas y posición de Fantasy.
    """
    key = f"bat_{year}"
    path = _path(key)
    ttl = 6.0 if year >= _NOW_YEAR else 24.0 * 365

    if not force and not _expired(path, ttl):
        print(f"[fetcher] cache -> {path.name}")
        df = pd.read_parquet(path)
    else:
        print(f"[fetcher] cargando {key}...")
        try:
            df = _fg_fetch({
                "pos": "all", "stats": "bat", "lg": "all", "qual": "0",
                "season": year, "season1": year, "ind": 1,
                "team": "0", "pageitems": 2500, "pagenum": 1, "type": 8,
            })
            if df is None or df.empty:
                raise ValueError("Respuesta vacía de FanGraphs")
            df.to_parquet(path, index=False)
        except Exception as e:
            if path.exists():
                print(f"[fetcher] Aviso: FanGraphs falló ({e}), usando caché parquet existente.")
                df = pd.read_parquet(path)
            else:
                raise RuntimeError(f"No se pudieron obtener datos de bateo para {year}: {e}")

    # Normalización defensiva de columnas (BRef / FanGraphs compatibility)
    df = df.copy()
    if "Team" not in df.columns and "Tm" in df.columns:
        df["Team"] = df["Tm"]
    if "AVG" not in df.columns and "BA" in df.columns:
        df["AVG"] = df["BA"]
    if "K" not in df.columns and "SO" in df.columns:
        df["K"] = df["SO"]
    elif "SO" not in df.columns and "K" in df.columns:
        df["SO"] = df["K"]
    if "WAR" not in df.columns:
        ops = pd.to_numeric(df.get("OPS", 0.700), errors="coerce").fillna(0.700)
        pa = pd.to_numeric(df.get("PA", 0), errors="coerce").fillna(0)
        hr = pd.to_numeric(df.get("HR", 0), errors="coerce").fillna(0)
        df["WAR"] = (((ops - 0.700) * pa / 100.0) + (hr * 0.05)).round(1)
    if "wOBA" not in df.columns:
        obp = pd.to_numeric(df.get("OBP", 0.320), errors="coerce").fillna(0.320)
        slg = pd.to_numeric(df.get("SLG", 0.400), errors="coerce").fillna(0.400)
        df["wOBA"] = ((obp * 0.69) + (slg * 0.45)).round(3)

    # Fusionar con métricas reales de Statcast (Baseball Savant)
    try:
        sc_bat = statcast_batting(year)
        if sc_bat is not None and not sc_bat.empty:
            merge_cols = [c for c in ["xBA", "xSLG", "xwOBA", "diff_wOBA", "diff_BA", "diff_SLG", "wOBA_Savant", "EV", "maxEV", "HardHit%", "Barrel%", "SweetSpot%"] if c in sc_bat.columns]
            if "mlbID" in df.columns and "mlbID" in sc_bat.columns:
                df["_join_id"] = pd.to_numeric(df["mlbID"], errors="coerce").fillna(-1).astype(int)
                sc_bat["_join_id"] = pd.to_numeric(sc_bat["mlbID"], errors="coerce").fillna(-1).astype(int)
                cols_to_drop = [c for c in merge_cols if c in df.columns]
                df_clean = df.drop(columns=cols_to_drop, errors="ignore")
                df = pd.merge(df_clean, sc_bat[["_join_id"] + merge_cols].drop_duplicates("_join_id"), on="_join_id", how="left").drop(columns=["_join_id"], errors="ignore")
            elif "Name" in df.columns and "Name_Savant" in sc_bat.columns:
                cols_to_drop = [c for c in merge_cols if c in df.columns]
                df_clean = df.drop(columns=cols_to_drop, errors="ignore")
                df = pd.merge(df_clean, sc_bat[["Name_Savant"] + merge_cols].drop_duplicates("Name_Savant"), left_on="Name", right_on="Name_Savant", how="left").drop(columns=["Name_Savant"], errors="ignore")

        if "wOBA_Savant" in df.columns:
            df["wOBA"] = pd.to_numeric(df["wOBA_Savant"], errors="coerce").combine_first(pd.to_numeric(df.get("wOBA", 0.320), errors="coerce"))
            df = df.drop(columns=["wOBA_Savant"], errors="ignore")
    except Exception as e:
        print(f"[fetcher] Aviso: no se pudo fusionar Statcast batting: {e}")

    # Asegurar diferenciales Statcast explícitos (Real - Esperado: Negativo = Por debajo de lo esperado)
    if "xBA" in df.columns and "AVG" in df.columns:
        df["diff_BA"] = (pd.to_numeric(df["AVG"], errors="coerce") - pd.to_numeric(df["xBA"], errors="coerce")).round(3)
    if "xSLG" in df.columns and "SLG" in df.columns:
        df["diff_SLG"] = (pd.to_numeric(df["SLG"], errors="coerce") - pd.to_numeric(df["xSLG"], errors="coerce")).round(3)
    if "xwOBA" in df.columns and "wOBA" in df.columns:
        df["diff_wOBA"] = (pd.to_numeric(df["wOBA"], errors="coerce") - pd.to_numeric(df["xwOBA"], errors="coerce")).round(3)

    # Enriquecer con posiciones de campo MLB y liga
    df["Name"] = df["Name"].apply(clean_ascii_text)
    pos_map, team_map = get_player_metadata(year)
    df["Team_Exact"] = df["Name"].map(team_map)
    df["Team"] = df["Team_Exact"].combine_first(df.get("Team", df.get("Tm", ""))).apply(clean_ascii_text)
    df = df.drop(columns=["Team_Exact"], errors="ignore")

    if "Pos" in df.columns and pd.to_numeric(df["Pos"], errors="coerce").notna().any():
        df["Pos_WAR"] = df["Pos"]
    df["Pos"] = df["Name"].map(pos_map).fillna(df.get("Pos", "UT"))

    df["League"] = df["Team"].apply(resolve_team_league)

    return df


def pitching(year: int, force: bool = False) -> pd.DataFrame:
    """
    Leaderboard individual de pitchers con métricas avanzadas y rol (SP/RP).
    """
    key = f"pit_{year}"
    path = _path(key)
    ttl = 6.0 if year >= _NOW_YEAR else 24.0 * 365

    if not force and not _expired(path, ttl):
        print(f"[fetcher] cache -> {path.name}")
        df = pd.read_parquet(path)
    else:
        print(f"[fetcher] cargando {key}...")
        try:
            df = _fg_fetch({
                "pos": "all", "stats": "pit", "lg": "all", "qual": "0",
                "season": year, "season1": year, "ind": 1,
                "team": "0", "pageitems": 2500, "pagenum": 1, "type": 8,
            })
            if df is None or df.empty:
                raise ValueError("Respuesta vacía de FanGraphs")
            df.to_parquet(path, index=False)
        except Exception as e:
            if path.exists():
                print(f"[fetcher] Aviso: FanGraphs falló ({e}), usando caché parquet existente.")
                df = pd.read_parquet(path)
            else:
                raise RuntimeError(f"No se pudieron obtener datos de pitcheo para {year}: {e}")

    # Normalización defensiva de columnas (BRef / FanGraphs compatibility)
    df = df.copy()
    if "Team" not in df.columns and "Tm" in df.columns:
        df["Team"] = df["Tm"]
    if "K" not in df.columns and "SO" in df.columns:
        df["K"] = df["SO"]
    elif "SO" not in df.columns and "K" in df.columns:
        df["SO"] = df["K"]
    if "WAR" not in df.columns:
        era = pd.to_numeric(df.get("ERA", 4.20), errors="coerce").fillna(4.20)
        ip = pd.to_numeric(df.get("IP", 0), errors="coerce").fillna(0)
        so = pd.to_numeric(df.get("SO", 0), errors="coerce").fillna(0)
        df["WAR"] = (((4.20 - era) * ip / 100.0) + (so * 0.01)).round(1)

    # Fusionar con métricas reales de Statcast (Baseball Savant)
    try:
        sc_pit = statcast_pitching(year)
        if sc_pit is not None and not sc_pit.empty:
            merge_cols = [c for c in ["xERA", "diff_ERA", "xwOBA_against", "EV_against", "HardHit%_against", "Barrel%_against"] if c in sc_pit.columns]
            if "mlbID" in df.columns and "mlbID" in sc_pit.columns:
                df["_join_id"] = pd.to_numeric(df["mlbID"], errors="coerce").fillna(-1).astype(int)
                sc_pit["_join_id"] = pd.to_numeric(sc_pit["mlbID"], errors="coerce").fillna(-1).astype(int)
                cols_to_drop = [c for c in merge_cols if c in df.columns]
                df_clean = df.drop(columns=cols_to_drop, errors="ignore")
                df = pd.merge(df_clean, sc_pit[["_join_id"] + merge_cols].drop_duplicates("_join_id"), on="_join_id", how="left").drop(columns=["_join_id"], errors="ignore")
            elif "Name" in df.columns and "Name_Savant" in sc_pit.columns:
                cols_to_drop = [c for c in merge_cols if c in df.columns]
                df_clean = df.drop(columns=cols_to_drop, errors="ignore")
                df = pd.merge(df_clean, sc_pit[["Name_Savant"] + merge_cols].drop_duplicates("Name_Savant"), left_on="Name", right_on="Name_Savant", how="left").drop(columns=["Name_Savant"], errors="ignore")
    except Exception as e:
        print(f"[fetcher] Aviso: no se pudo fusionar Statcast pitching: {e}")

    # Fallbacks si Statcast no contiene al lanzador
    if "xERA" not in df.columns and "ERA" in df.columns:
        df["xERA"] = df["ERA"]
    if "SIERA" not in df.columns and "ERA" in df.columns:
        df["SIERA"] = df["ERA"]
    if "FIP" not in df.columns and "ERA" in df.columns:
        df["FIP"] = df["ERA"]
    if "Stuff+" not in df.columns:
        df["Stuff+"] = 100

    # Asegurar diferencial de ERA explícito
    if "xERA" in df.columns and "ERA" in df.columns:
        df["diff_ERA"] = (pd.to_numeric(df["ERA"], errors="coerce") - pd.to_numeric(df["xERA"], errors="coerce")).round(2)

    # Enriquecer rol SP/RP y liga
    df["Name"] = df["Name"].apply(clean_ascii_text)
    pos_map, team_map = get_player_metadata(year)
    df["Team_Exact"] = df["Name"].map(team_map)
    df["Team"] = df["Team_Exact"].combine_first(df.get("Team", df.get("Tm", ""))).apply(clean_ascii_text)
    df = df.drop(columns=["Team_Exact"], errors="ignore")

    if "GS" in df.columns and "G" in df.columns:
        gs = pd.to_numeric(df["GS"], errors="coerce").fillna(0)
        g = pd.to_numeric(df["G"], errors="coerce").fillna(1)
        df["Pos"] = (gs >= (g * 0.5)).map({True: "SP", False: "RP"})
    else:
        df["Pos"] = df["Name"].map(pos_map).fillna("P")

    df["League"] = df["Team"].apply(resolve_team_league)

    return df


# ── Colectivas por Equipo ───────────────────────────────────────────────────

def team_bat(year: int, force: bool = False) -> pd.DataFrame:
    """Stats colectivas de bateo por equipo — FanGraphs."""
    key = f"tbat_{year}"
    path = _path(key)
    ttl = 6.0 if year >= _NOW_YEAR else 24.0 * 365

    if not force and not _expired(path, ttl):
        return pd.read_parquet(path)

    try:
        df = _fg_fetch({
            "pos": "all", "stats": "bat", "lg": "all", "qual": 0,
            "season": year, "season1": year, "ind": 0,
            "team": "0,ts", "pageitems": 30, "pagenum": 1, "type": 1,
        })
        if df is not None and not df.empty:
            df.to_parquet(path, index=False)
            return df
    except Exception as e:
        if path.exists():
            return pd.read_parquet(path)
        raise e
    return pd.DataFrame()


def team_pit(year: int, force: bool = False) -> pd.DataFrame:
    """Stats colectivas de pitcheo por equipo — FanGraphs."""
    key = f"tpit_{year}"
    path = _path(key)
    ttl = 6.0 if year >= _NOW_YEAR else 24.0 * 365

    if not force and not _expired(path, ttl):
        return pd.read_parquet(path)

    try:
        df = _fg_fetch({
            "pos": "all", "stats": "pit", "lg": "all", "qual": 0,
            "season": year, "season1": year, "ind": 0,
            "team": "0,ts", "pageitems": 30, "pagenum": 1, "type": 1,
        })
        if df is not None and not df.empty:
            df.to_parquet(path, index=False)
            return df
    except Exception as e:
        if path.exists():
            return pd.read_parquet(path)
        raise e
    return pd.DataFrame()


def team_field(year: int, force: bool = False) -> pd.DataFrame:
    """Stats colectivas de fildeo por equipo — FanGraphs."""
    key = f"tfield_{year}"
    path = _path(key)
    ttl = 6.0 if year >= _NOW_YEAR else 24.0 * 365

    if not force and not _expired(path, ttl):
        return pd.read_parquet(path)

    try:
        df = _fg_fetch({
            "pos": "all", "stats": "fld", "lg": "all", "qual": 0,
            "season": year, "season1": year, "ind": 0,
            "team": "0,ts", "pageitems": 30, "pagenum": 1, "type": 1,
        })
        if df is not None and not df.empty:
            df.to_parquet(path, index=False)
            return df
    except Exception as e:
        if path.exists():
            return pd.read_parquet(path)
        return pd.DataFrame()
    return pd.DataFrame()


# ── Standings Oficiales (MLB Stats API) ──────────────────────────────────────

def get_standings(year: int, force: bool = False) -> dict[str, pd.DataFrame]:
    """
    Retorna diccionario con DataFrames de Standings por división y Wild Card con Magic Numbers y Postseason status.
    Estructura: {'AL East': df, 'AL Central': df, ..., 'AL Wild Card': df, 'NL Wild Card': df}
    """
    cache_path = _path(f"standings_mlb_{year}", ext="json")
    ttl = 1.0 if year >= _NOW_YEAR else 24.0 * 365

    if not force and not _expired(cache_path, ttl):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {k: pd.DataFrame(v) for k, v in data.items()}
        except Exception:
            pass

    try:
        url = f"{_MLB_API_BASE}/standings?leagueId=103,104&season={year}&hydrate=team,streak"
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        records = resp.json().get("records", [])

        results = {}
        for rec in records:
            div_id = rec.get("division", {}).get("id")
            div_name, lg = DIVISION_NAMES.get(div_id, ("Division", "MLB"))

            rows = []
            team_records = rec.get("teamRecords", [])
            leader_w = team_records[0].get("wins", 0) if team_records else 0
            second_l = team_records[1].get("losses", 0) if len(team_records) > 1 else 0

            for idx, tr in enumerate(team_records):
                raw_name = tr.get("team", {}).get("name", "")
                t_name = clean_ascii_text(raw_name)
                t_abbr = tr.get("team", {}).get("abbreviation", "")
                w = tr.get("wins", 0)
                l = tr.get("losses", 0)
                pct = tr.get("winningPercentage", ".000")
                gb = tr.get("gamesBack", "-")
                wc_gb = tr.get("wildCardGamesBack", "-")
                rs = tr.get("runsScored", 0)
                ra = tr.get("runsAllowed", 0)
                diff = tr.get("runDifferential", 0)
                streak = tr.get("streak", {}).get("streakCode", "")
                clinch = tr.get("clinchIndicator", "")
                
                # Magic Number y Elimination Number
                api_mn = str(tr.get("magicNumber", "")).strip()
                api_e = str(tr.get("eliminationNumber", "")).strip()

                if idx == 0:
                    if api_mn and api_mn != "-":
                        mn = api_mn
                    else:
                        calc_mn = max(0, 163 - w - second_l)
                        mn = str(calc_mn) if calc_mn > 0 else "Clinched"
                    e_num = "-"
                else:
                    mn = "-"
                    if api_e and api_e != "-":
                        e_num = api_e
                    else:
                        calc_e = max(0, 163 - leader_w - l)
                        e_num = str(calc_e) if calc_e > 0 else "Eliminado"

                # Split records para L10
                l10 = ""
                for split in tr.get("records", {}).get("splitRecords", []):
                    if split.get("type") == "lastTen":
                        l10 = f"{split.get('wins', 0)}-{split.get('losses', 0)}"

                rows.append({
                    "Team": t_name,
                    "Abbr": t_abbr,
                    "W": w,
                    "L": l,
                    "PCT": pct,
                    "GB": gb,
                    "WC_GB": wc_gb,
                    "Magic_Number": mn,
                    "Elim_Number": e_num,
                    "Clinch": clinch,
                    "RS": rs,
                    "RA": ra,
                    "Diff": diff,
                    "Streak": streak,
                    "L10": l10,
                    "League": lg,
                    "Division": div_name,
                })

            df_div = pd.DataFrame(rows)
            results[div_name] = df_div

        # Guardar en caché
        serializable = {k: v.to_dict(orient="records") for k, v in results.items()}
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False)

        return results
    except Exception as e:
        print(f"[fetcher] Error descargando standings MLB: {e}")
        return {}


def get_postseason_picture(tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """
    Calcula los 6 clasificados (Seeds 1 al 6), los Byes, los enfrentamientos de Wild Card
    y los equipos 'In the Hunt' para la Liga Americana y la Liga Nacional.
    """
    out = {
        "AL": {"seeds": pd.DataFrame(), "hunt": pd.DataFrame(), "bracket": {}},
        "NL": {"seeds": pd.DataFrame(), "hunt": pd.DataFrame(), "bracket": {}},
    }
    if not tables:
        return out

    for lg, div_list in [("AL", ["AL East", "AL Central", "AL West"]), ("NL", ["NL East", "NL Central", "NL West"])]:
        div_leaders = []
        wildcard_pool = []

        for d_name in div_list:
            df_d = tables.get(d_name, pd.DataFrame())
            if df_d.empty:
                continue
            df_d_sorted = df_d.sort_values(by=["W", "Diff"], ascending=[False, False]).reset_index(drop=True)
            leader = df_d_sorted.iloc[0].to_dict()
            leader["Type"] = f"Campeón {d_name}"
            div_leaders.append(leader)

            if len(df_d_sorted) > 1:
                for _, r in df_d_sorted.iloc[1:].iterrows():
                    wc_item = r.to_dict()
                    wc_item["Type"] = "Wild Card"
                    wildcard_pool.append(wc_item)

        if not div_leaders:
            continue

        df_div_lead = pd.DataFrame(div_leaders).sort_values(by=["W", "Diff"], ascending=[False, False]).reset_index(drop=True)
        df_wc_pool = pd.DataFrame(wildcard_pool).sort_values(by=["W", "Diff"], ascending=[False, False]).reset_index(drop=True) if wildcard_pool else pd.DataFrame()

        seeds = []
        # Seeds 1, 2, 3: Campeones divisionales
        for i, row in df_div_lead.iterrows():
            seed_num = i + 1
            status = "🏆 Bye a Serie Divisional (ALDS/NLDS)" if seed_num <= 2 else "🏠 Sede de Wild Card Series (vs Seed 6)"
            t_name = row["Team"]
            seeds.append({
                "Logo": get_team_logo(t_name),
                "Seed": f"Seed {seed_num}",
                "Team": t_name,
                "Record": f"{row['W']}-{row['L']}",
                "PCT": row["PCT"],
                "Type": row["Type"],
                "Status": status,
                "Diff": row["Diff"],
            })

        # Seeds 4, 5, 6: Comodines
        if not df_wc_pool.empty:
            for i, row in df_wc_pool.head(3).iterrows():
                seed_num = i + 4
                status = "🏠 Sede de Wild Card Series (vs Seed 5)" if seed_num == 4 else ("✈️ Visita Wild Card Series (en Seed 4)" if seed_num == 5 else "✈️ Visita Wild Card Series (en Seed 3)")
                t_name = row["Team"]
                seeds.append({
                    "Logo": get_team_logo(t_name),
                    "Seed": f"Seed {seed_num} (WC{i+1})",
                    "Team": t_name,
                    "Record": f"{row['W']}-{row['L']}",
                    "PCT": row["PCT"],
                    "Type": "Wild Card",
                    "Status": status,
                    "Diff": row["Diff"],
                })

        df_seeds = pd.DataFrame(seeds)
        df_hunt = df_wc_pool.iloc[3:7].copy().reset_index(drop=True) if len(df_wc_pool) > 3 else pd.DataFrame()
        if not df_hunt.empty:
            df_hunt["Logo"] = df_hunt["Team"].apply(get_team_logo)

        # Bracket de cruces
        bracket = {}
        if len(seeds) >= 6:
            bracket = {
                "bye_1": {"seed": "Seed 1", "team": seeds[0]["Team"], "record": seeds[0]["Record"], "logo": seeds[0]["Logo"]},
                "bye_2": {"seed": "Seed 2", "team": seeds[1]["Team"], "record": seeds[1]["Record"], "logo": seeds[1]["Logo"]},
                "wc_matchup_1": {
                    "home": {"seed": "Seed 3", "team": seeds[2]["Team"], "record": seeds[2]["Record"], "logo": seeds[2]["Logo"]},
                    "away": {"seed": "Seed 6", "team": seeds[5]["Team"], "record": seeds[5]["Record"], "logo": seeds[5]["Logo"]},
                    "winner_faces": f"Seed 2 ({seeds[1]['Team']})",
                },
                "wc_matchup_2": {
                    "home": {"seed": "Seed 4", "team": seeds[3]["Team"], "record": seeds[3]["Record"], "logo": seeds[3]["Logo"]},
                    "away": {"seed": "Seed 5", "team": seeds[4]["Team"], "record": seeds[4]["Record"], "logo": seeds[4]["Logo"]},
                    "winner_faces": f"Seed 1 ({seeds[0]['Team']})",
                },
            }

        out[lg]["seeds"] = df_seeds
        out[lg]["hunt"] = df_hunt
        out[lg]["bracket"] = bracket

    return out


# ── Calendario & Matchups Semanales (MLB Stats API) ──────────────────────────

def get_schedule_range(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Descarga calendario con lanzadores abridores probables, horarios y parques.
    """
    url = f"{_MLB_API_BASE}/schedule?sportId=1&startDate={start_date}&endDate={end_date}&hydrate=probablePitcher,venue,linescore"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        dates = resp.json().get("dates", [])
        
        games_list = []
        for d in dates:
            game_date = d.get("date")
            for g in d.get("games", []):
                away_team = g.get("teams", {}).get("away", {})
                home_team = g.get("teams", {}).get("home", {})
                
                away_name = away_team.get("team", {}).get("name")
                away_abbr = away_team.get("team", {}).get("abbreviation", "")
                home_name = home_team.get("team", {}).get("name")
                home_abbr = home_team.get("team", {}).get("abbreviation", "")
                
                sp_away = away_team.get("probablePitcher", {}).get("fullName", "TBD")
                sp_home = home_team.get("probablePitcher", {}).get("fullName", "TBD")
                
                venue = g.get("venue", {}).get("name", "")
                status = g.get("status", {}).get("detailedState", "")
                
                # Marcador si ya finalizó
                linescore = g.get("linescore", {})
                away_runs = linescore.get("teams", {}).get("away", {}).get("runs", None)
                home_runs = linescore.get("teams", {}).get("home", {}).get("runs", None)

                games_list.append({
                    "Date": game_date,
                    "Away": away_name,
                    "Away_Abbr": away_abbr,
                    "SP_Away": sp_away,
                    "Away_Runs": away_runs,
                    "Home": home_name,
                    "Home_Abbr": home_abbr,
                    "SP_Home": sp_home,
                    "Home_Runs": home_runs,
                    "Venue": venue,
                    "Status": status,
                })

        return pd.DataFrame(games_list)
    except Exception as e:
        print(f"[fetcher] Error cargando schedule de MLB: {e}")
        return pd.DataFrame()


def get_team_schedule(year: int, team_abbr: str) -> pd.DataFrame:
    """
    Obtiene todos los juegos de la temporada de un equipo específico vía MLB Stats API.
    """
    start_date = f"{year}-03-20"
    end_date = f"{year}-11-05"
    
    # Primero obtener el teamId de MLB
    try:
        teams_url = f"{_MLB_API_BASE}/teams?sportId=1&season={year}"
        teams_resp = requests.get(teams_url, timeout=20).json().get("teams", [])
        team_id = None
        for t in teams_resp:
            if t.get("abbreviation") == team_abbr or t.get("fileCode") == team_abbr.lower():
                team_id = t.get("id")
                break
        
        if not team_id:
            return pd.DataFrame()

        url = f"{_MLB_API_BASE}/schedule?teamId={team_id}&startDate={start_date}&endDate={end_date}&sportId=1&hydrate=probablePitcher,decisions"
        resp = requests.get(url, timeout=25)
        resp.raise_for_status()
        dates = resp.json().get("dates", [])
        
        rows = []
        for d in dates:
            for g in d.get("games", []):
                is_home = g.get("teams", {}).get("home", {}).get("team", {}).get("id") == team_id
                my_team = g.get("teams", {}).get("home" if is_home else "away", {})
                opp_team = g.get("teams", {}).get("away" if is_home else "home", {})
                
                my_score = my_team.get("score")
                opp_score = opp_team.get("score")
                
                result = ""
                if my_score is not None and opp_score is not None:
                    if my_score > opp_score:
                        result = "W"
                    elif my_score < opp_score:
                        result = "L"
                    else:
                        result = "T"
                
                decisions = g.get("decisions", {})
                winner = decisions.get("winner", {}).get("fullName", "")
                loser = decisions.get("loser", {}).get("fullName", "")
                save = decisions.get("save", {}).get("fullName", "")

                rows.append({
                    "Date": d.get("date"),
                    "Team": team_abbr,
                    "Home_Away": "Home" if is_home else "Away",
                    "Opp": opp_team.get("team", {}).get("abbreviation", opp_team.get("team", {}).get("name")),
                    "Res": result,
                    "R": my_score,
                    "RA": opp_score,
                    "Pitcher_W": winner,
                    "Pitcher_L": loser,
                    "Save": save,
                    "Status": g.get("status", {}).get("detailedState", ""),
                    "SP_Opp": opp_team.get("probablePitcher", {}).get("fullName", "TBD"),
                })
                
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"[fetcher] Error obteniendo schedule del equipo {team_abbr}: {e}")
        return pd.DataFrame()

