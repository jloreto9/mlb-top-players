"""
fetcher.py
----------
Descarga datos pitch-by-pitch de Statcast via pybaseball.
Incluye caché local en Parquet para no re-descargar en cada ejecución.
"""

import os
import pandas as pd
from pathlib import Path
from pybaseball import statcast
from pybaseball import cache

# Activar caché interno de pybaseball (evita rate limits)
cache.enable()

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)


def _cache_path(start_dt: str, end_dt: str) -> Path:
    """Genera nombre de archivo de caché basado en el rango de fechas."""
    return CACHE_DIR / f"statcast_{start_dt}_{end_dt}.parquet"


def fetch_statcast(start_dt: str, end_dt: str, force_refresh: bool = False) -> pd.DataFrame:
    """
    Descarga datos de Statcast para el rango de fechas dado.
    Si existe caché local, lo usa (a menos que force_refresh=True).

    Parámetros
    ----------
    start_dt      : str  — Fecha inicio 'YYYY-MM-DD'
    end_dt        : str  — Fecha fin    'YYYY-MM-DD'
    force_refresh : bool — Si True, ignora caché y re-descarga

    Retorna
    -------
    pd.DataFrame con todos los pitches del período
    """
    cache_file = _cache_path(start_dt, end_dt)

    if cache_file.exists() and not force_refresh:
        print(f"[fetcher] Cargando desde caché: {cache_file}")
        return pd.read_parquet(cache_file)

    print(f"[fetcher] Descargando Statcast {start_dt} → {end_dt} (puede tardar)...")
    df = statcast(start_dt=start_dt, end_dt=end_dt)

    if df is None or df.empty:
        raise ValueError(f"Statcast no retornó datos para el rango {start_dt} → {end_dt}")

    # Guardar caché
    df.to_parquet(cache_file, index=False)
    print(f"[fetcher] Datos guardados en caché: {cache_file} ({len(df):,} pitches)")

    return df


def get_column_inventory(df: pd.DataFrame) -> None:
    """Imprime columnas disponibles — útil para debugging."""
    print(f"\n[fetcher] Total columnas: {len(df.columns)}")
    print(df.dtypes.to_string())
