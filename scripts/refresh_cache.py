#!/usr/bin/env python3
"""
scripts/refresh_cache.py
------------------------
Descarga y guarda los datos para la temporada actual
(y la anterior si estamos antes de julio).
Se ejecuta manualmente o via GitHub Actions.

Uso:
    python scripts/refresh_cache.py
    python scripts/refresh_cache.py --year 2024
"""

import argparse
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Asegurar que el root del proyecto este en el path
sys.path.insert(0, str(Path(__file__).parent.parent))

import fetcher


def refresh(year: int) -> None:
    print(f"\n{'='*50}")
    print(f"  Refreshing stats: {year}")
    print(f"{'='*50}")

    # Críticos: Baseball Reference — accesibles desde CI
    critical_tasks = [
        ("batting",  lambda: fetcher.batting(year, force=True)),
        ("pitching", lambda: fetcher.pitching(year, force=True)),
    ]

    # Best-effort: FanGraphs — puede fallar en CI por bloqueo de IP
    best_effort_tasks = [
        ("team_batting",  lambda: fetcher.team_bat(year, force=True)),
        ("team_pitching", lambda: fetcher.team_pit(year, force=True)),
    ]

    for name, fn in critical_tasks:
        try:
            df = fn()
            print(f"  [OK] {name}: {len(df):,} filas")
        except Exception as e:
            print(f"  [ERROR] {name}: {type(e).__name__}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)

    for name, fn in best_effort_tasks:
        try:
            df = fn()
            print(f"  [OK] {name}: {len(df):,} filas")
        except Exception as e:
            print(f"  [WARN] {name}: {type(e).__name__}: {e} (omitido)", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh stats cache")
    parser.add_argument("--year", type=int, default=None,
                        help="Temporada a refrescar (default: automatico)")
    args = parser.parse_args()

    now = datetime.utcnow()
    current_year = now.year

    if args.year:
        years = [args.year]
    else:
        years = [current_year]
        if now.month < 7:
            years.append(current_year - 1)

    for year in years:
        refresh(year)

    print(f"\nDone. {len(years)} temporada(s) actualizadas.")


if __name__ == "__main__":
    main()
