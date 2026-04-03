"""
fetcher.py
----------
Descarga estadísticas desde FanGraphs via pybaseball.
Caché local Parquet:  6 h para temporada en curso, 1 año para pasadas.

Funciones públicas:
    batting(year)       → leaderboard individual bateadores
    pitching(year)      → leaderboard individual pitchers
    team_bat(year)      → stats colectivas bateo por equipo
    team_pit(year)      → stats colectivas pitcheo por equipo
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from pybaseball import batting_stats, pitching_stats, team_batting, team_pitching
from pybaseball import cache as pybb_cache

pybb_cache.enable()

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

_NOW_YEAR: int = datetime.now().year


# ── Helpers de caché ───────────────────────────────────────────────────────

def _path(key: str) -> Path:
    return CACHE_DIR / f"{key}.parquet"


def _expired(path: Path, max_hours: float) -> bool:
    if not path.exists():
        return True
    return (time.time() - path.stat().st_mtime) > max_hours * 3600


def _load(key: str, fetch_fn, year: int, force: bool) -> pd.DataFrame:
    path = _path(key)
    ttl = 6.0 if year >= _NOW_YEAR else 24.0 * 365  # año actual: 6h · pasados: 1 año
    if not force and not _expired(path, ttl):
        print(f"[fetcher] caché → {path.name}")
        return pd.read_parquet(path)

    print(f"[fetcher] descargando {key} desde FanGraphs...")
    df = fetch_fn()

    if df is None or df.empty:
        raise ValueError(f"FanGraphs no retornó datos para {key}")

    df.to_parquet(path, index=False)
    print(f"[fetcher] guardado {path.name} ({len(df):,} filas)")
    return df


# ── API pública ────────────────────────────────────────────────────────────

def batting(year: int, force: bool = False) -> pd.DataFrame:
    """Leaderboard individual de bateadores (temporada completa, sin filtro de PA)."""
    return _load(
        f"bat_{year}",
        lambda: batting_stats(year, qual=1, ind=1),
        year, force,
    )


def pitching(year: int, force: bool = False) -> pd.DataFrame:
    """Leaderboard individual de pitchers (temporada completa, sin filtro de IP)."""
    return _load(
        f"pit_{year}",
        lambda: pitching_stats(year, qual=1, ind=1),
        year, force,
    )


def team_bat(year: int, force: bool = False) -> pd.DataFrame:
    """Stats colectivas de bateo por equipo."""
    return _load(
        f"tbat_{year}",
        lambda: team_batting(year),
        year, force,
    )


def team_pit(year: int, force: bool = False) -> pd.DataFrame:
    """Stats colectivas de pitcheo por equipo."""
    return _load(
        f"tpit_{year}",
        lambda: team_pitching(year),
        year, force,
    )
