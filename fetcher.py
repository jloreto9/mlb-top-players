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

from constants import TEAM_LEAGUE, MLB_TEAMS, resolve_team_league

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

def get_player_positions(year: int = _NOW_YEAR, force: bool = False) -> dict[str, str]:
    """
    Retorna diccionario {Player_Name: Primary_Position} (ej: 'Aaron Judge': 'OF').
    Usa la API oficial de MLB y cachea en JSON.
    """
    cache_path = _path(f"positions_{year}", ext="json")
    ttl = 12.0 if year >= _NOW_YEAR else 24.0 * 365

    if not force and not _expired(cache_path, ttl):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    try:
        url = f"{_MLB_API_BASE}/sports/1/players?season={year}"
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        people = resp.json().get("people", [])
        
        pos_map = {}
        for p in people:
            name = p.get("fullName")
            pos = p.get("primaryPosition", {}).get("abbreviation", "DH")
            if name:
                pos_map[name] = pos

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(pos_map, f, ensure_ascii=False)

        return pos_map
    except Exception as e:
        print(f"[fetcher] Error obteniendo posiciones MLB: {e}")
        return {}


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
            })
            ba_col = "ba" if "ba" in df_exp.columns else "ba_sc"
            if ba_col in df_exp.columns and "xBA" in df_exp.columns:
                df_exp["diff_BA"] = (pd.to_numeric(df_exp[ba_col], errors="coerce") - pd.to_numeric(df_exp["xBA"], errors="coerce")).round(3)
            elif "est_ba_minus_ba_diff" in df_exp.columns:
                df_exp["diff_BA"] = pd.to_numeric(df_exp["est_ba_minus_ba_diff"], errors="coerce").round(3)

            slg_col = "slg" if "slg" in df_exp.columns else "slg_sc"
            if slg_col in df_exp.columns and "xSLG" in df_exp.columns:
                df_exp["diff_SLG"] = (pd.to_numeric(df_exp[slg_col], errors="coerce") - pd.to_numeric(df_exp["xSLG"], errors="coerce")).round(3)
            elif "est_slg_minus_slg_diff" in df_exp.columns:
                df_exp["diff_SLG"] = pd.to_numeric(df_exp["est_slg_minus_slg_diff"], errors="coerce").round(3)

            woba_col = "woba" if "woba" in df_exp.columns else "woba_sc"
            if woba_col in df_exp.columns and "xwOBA" in df_exp.columns:
                df_exp["diff_wOBA"] = (pd.to_numeric(df_exp[woba_col], errors="coerce") - pd.to_numeric(df_exp["xwOBA"], errors="coerce")).round(3)
            elif "est_woba_minus_woba_diff" in df_exp.columns:
                df_exp["diff_wOBA"] = pd.to_numeric(df_exp["est_woba_minus_woba_diff"], errors="coerce").round(3)

            if "last_name, first_name" in df_exp.columns:
                df_exp["Name_Savant"] = df_exp["last_name, first_name"].apply(
                    lambda n: " ".join(reversed([p.strip() for p in n.split(",")])) if "," in str(n) else str(n)
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
                    lambda n: " ".join(reversed([p.strip() for p in n.split(",")])) if "," in str(n) else str(n)
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
            merge_cols = [c for c in ["xBA", "xSLG", "xwOBA", "diff_wOBA", "diff_BA", "diff_SLG", "EV", "maxEV", "HardHit%", "Barrel%", "SweetSpot%"] if c in sc_bat.columns]
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
    pos_map = get_player_positions(year)
    if "Pos" in df.columns and pd.to_numeric(df["Pos"], errors="coerce").notna().any():
        df["Pos_WAR"] = df["Pos"]
    df["Pos"] = df["Name"].map(pos_map).fillna("UT")

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
    if "GS" in df.columns and "G" in df.columns:
        gs = pd.to_numeric(df["GS"], errors="coerce").fillna(0)
        g = pd.to_numeric(df["G"], errors="coerce").fillna(1)
        df["Pos"] = (gs >= (g * 0.5)).map({True: "SP", False: "RP"})
    else:
        df["Pos"] = "P"

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
    Retorna diccionario con DataFrames de Standings por división y Wild Card.
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
            div_info = rec.get("division", {})
            div_id = div_info.get("id")
            div_name, lg = DIVISION_NAMES.get(div_id, (div_info.get("name", "Division"), "MLB"))

            rows = []
            for tr in rec.get("teamRecords", []):
                t_name = tr.get("team", {}).get("name", "")
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
                    "RS": rs,
                    "RA": ra,
                    "Diff": diff,
                    "Streak": streak,
                    "L10": l10,
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

