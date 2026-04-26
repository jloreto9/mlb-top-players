"""
fetcher.py
----------
Descarga estadísticas de béisbol MLB.
- batting / pitching individuales: Baseball Reference (accesible desde CI)
- team_bat / team_pit / team_field: FanGraphs JSON API (best-effort en CI)
- standings: Baseball Reference

Caché local Parquet:  6 h para temporada en curso, 1 año para pasadas.
"""

from __future__ import annotations

import pickle
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from pybaseball import batting_stats_bref, pitching_stats_bref, standings

# ── FanGraphs JSON API (team stats) ───────────────────────────────────────────

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

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

_NOW_YEAR: int = datetime.now().year


# ── Helpers de caché ──────────────────────────────────────────────────────────

def _path(key: str) -> Path:
    return CACHE_DIR / f"{key}.parquet"


def _expired(path: Path, max_hours: float) -> bool:
    if not path.exists():
        return True
    return (time.time() - path.stat().st_mtime) > max_hours * 3600


def _load(key: str, fetch_fn, year: int, force: bool) -> pd.DataFrame:
    path = _path(key)
    ttl = 6.0 if year >= _NOW_YEAR else 24.0 * 365
    if not force and not _expired(path, ttl):
        print(f"[fetcher] caché → {path.name}")
        return pd.read_parquet(path)

    print(f"[fetcher] descargando {key}...")
    df = fetch_fn()

    if df is None or df.empty:
        raise ValueError(f"No se obtuvieron datos para {key}")

    df.to_parquet(path, index=False)
    print(f"[fetcher] guardado {path.name} ({len(df):,} filas)")
    return df


def _fg_fetch(params: dict) -> pd.DataFrame:
    resp = requests.get(_FG_API, params=params, headers=_FG_HEADERS, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    rows = payload.get("data", payload) if isinstance(payload, dict) else payload
    return pd.DataFrame(rows)


# ── API pública ───────────────────────────────────────────────────────────────

def batting(year: int, force: bool = False) -> pd.DataFrame:
    """Leaderboard individual de bateadores — Baseball Reference."""
    return _load(
        f"bat_{year}",
        lambda: batting_stats_bref(year),
        year, force,
    )


def pitching(year: int, force: bool = False) -> pd.DataFrame:
    """Leaderboard individual de pitchers — Baseball Reference."""
    return _load(
        f"pit_{year}",
        lambda: pitching_stats_bref(year),
        year, force,
    )


def team_bat(year: int, force: bool = False) -> pd.DataFrame:
    """Stats colectivas de bateo por equipo — FanGraphs (best-effort)."""
    return _load(
        f"tbat_{year}",
        lambda: _fg_fetch({
            "pos": "all", "stats": "bat", "lg": "all", "qual": 0,
            "season": year, "season1": year, "ind": 0,
            "team": "0,ts", "pageitems": 30, "pagenum": 1, "type": 1,
        }),
        year, force,
    )


def team_pit(year: int, force: bool = False) -> pd.DataFrame:
    """Stats colectivas de pitcheo por equipo — FanGraphs (best-effort)."""
    return _load(
        f"tpit_{year}",
        lambda: _fg_fetch({
            "pos": "all", "stats": "pit", "lg": "all", "qual": 0,
            "season": year, "season1": year, "ind": 0,
            "team": "0,ts", "pageitems": 30, "pagenum": 1, "type": 1,
        }),
        year, force,
    )


def team_field(year: int, force: bool = False) -> pd.DataFrame:
    """Stats colectivas de fildeo por equipo — FanGraphs (best-effort)."""
    return _load(
        f"tfield_{year}",
        lambda: _fg_fetch({
            "pos": "all", "stats": "fld", "lg": "all", "qual": 0,
            "season": year, "season1": year, "ind": 0,
            "team": "0,ts", "pageitems": 30, "pagenum": 1, "type": 1,
        }),
        year, force,
    )


def get_standings(year: int, force: bool = False) -> list[pd.DataFrame]:
    """
    Standings por división — Baseball Reference.
    Retorna lista de 6 DataFrames:
    AL East, AL Central, AL West, NL East, NL Central, NL West
    """
    cache_file = CACHE_DIR / f"standings_{year}.pkl"
    ttl = 1.0 if year >= _NOW_YEAR else 24.0 * 365

    if not force and cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < ttl * 3600:
            with open(cache_file, "rb") as f:
                return pickle.load(f)

    print(f"[fetcher] descargando standings {year} desde Baseball Reference...")
    tables = standings(year)

    with open(cache_file, "wb") as f:
        pickle.dump(tables, f)

    return tables
