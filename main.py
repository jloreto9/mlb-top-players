"""
main.py
-------
Entry point del pipeline MLB Stats.

Uso directo:
    python main.py --start 2024-04-01 --end 2024-06-30 --top 10 --min_pa 50 --min_bf 30

En Streamlit, importar solo la función run():
    from main import run
    batter_rankings, pitcher_rankings = run(start_dt, end_dt, top, min_pa, min_bf)
"""

import argparse
import pandas as pd
from fetcher    import fetch_statcast
from calculator import calc_batter_metrics, calc_pitcher_metrics
from ranker     import top_batters, top_pitchers

# ---------------------------------------------------------------------------
# Parámetros por defecto
# ---------------------------------------------------------------------------
DEFAULT_START  = "2024-04-01"
DEFAULT_END    = "2024-06-30"
DEFAULT_TOP    = 10
DEFAULT_MIN_PA = 50
DEFAULT_MIN_BF = 30


# ---------------------------------------------------------------------------
# Pretty print (solo para ejecución directa por CLI)
# ---------------------------------------------------------------------------

def print_ranking(title: str, rankings: dict[str, pd.DataFrame]) -> None:
    sep = "=" * 80
    print(f"\n{sep}")
    print(f"  {title}")
    print(sep)
    for league, df in rankings.items():
        print(f"\n  ── {league} ──")
        print(df.to_string())
    print()


# ---------------------------------------------------------------------------
# Pipeline principal (importable desde Streamlit)
# ---------------------------------------------------------------------------

def run(
    start_dt: str,
    end_dt: str,
    top: int = DEFAULT_TOP,
    min_pa: int = DEFAULT_MIN_PA,
    min_bf: int = DEFAULT_MIN_BF,
    force_refresh: bool = False,
) -> tuple[dict, dict]:
    """
    Ejecuta el pipeline completo y retorna los rankings.

    Retorna
    -------
    (batter_rankings, pitcher_rankings)
    Cada uno es {'AL': DataFrame, 'NL': DataFrame}
    """
    print(f"\n[main] Período: {start_dt} → {end_dt}")
    print(f"[main] Top {top} | min_PA={min_pa} | min_BF={min_bf}\n")

    # 1. Fetch
    df_raw = fetch_statcast(start_dt, end_dt, force_refresh=force_refresh)
    print(f"[main] Pitches totales descargados: {len(df_raw):,}")

    # 2. Calcular métricas
    print("[main] Calculando métricas de bateadores...")
    df_batters = calc_batter_metrics(df_raw, min_pa=min_pa)
    print(f"[main] Bateadores únicos: {len(df_batters):,}")

    print("[main] Calculando métricas de pitchers...")
    df_pitchers = calc_pitcher_metrics(df_raw, min_bf=min_bf)
    print(f"[main] Pitchers únicos: {len(df_pitchers):,}")

    # 3. Rankings
    batter_rankings  = top_batters(df_batters,  n=top, sort_by="xwOBA", min_pa=0)
    pitcher_rankings = top_pitchers(df_pitchers, n=top, sort_by="xERA",  min_bf=0)

    return batter_rankings, pitcher_rankings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MLB Top Players por Liga (Statcast)")
    p.add_argument("--start",         default=DEFAULT_START,  help="Fecha inicio YYYY-MM-DD")
    p.add_argument("--end",           default=DEFAULT_END,    help="Fecha fin   YYYY-MM-DD")
    p.add_argument("--top",           default=DEFAULT_TOP,    type=int)
    p.add_argument("--min_pa",        default=DEFAULT_MIN_PA, type=int)
    p.add_argument("--min_bf",        default=DEFAULT_MIN_BF, type=int)
    p.add_argument("--force_refresh", action="store_true",    help="Re-descarga ignorando caché")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    batter_rankings, pitcher_rankings = run(
        start_dt      = args.start,
        end_dt        = args.end,
        top           = args.top,
        min_pa        = args.min_pa,
        min_bf        = args.min_bf,
        force_refresh = args.force_refresh,
    )

    print_ranking("TOP BATEADORES POR LIGA (ordenados por xwOBA)", batter_rankings)
    print_ranking("TOP PITCHERS POR LIGA (ordenados por xERA)",     pitcher_rankings)
