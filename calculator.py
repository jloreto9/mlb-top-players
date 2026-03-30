"""
calculator.py
-------------
Calcula metricas agregadas desde datos pitch-by-pitch de Statcast.

Metricas de bateadores : xwOBA, xBA, xSLG, AVG, OBP, SLG, OPS, K%, BB%, HR, PA
Metricas de pitchers   : xERA, AVG_velo, AVG_spin, K%, BB%, HR_allowed, IP
"""

from pathlib import Path

import numpy as np
import pandas as pd
from pybaseball import chadwick_register


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Eventos que cuentan como plate appearance completo
PA_EVENTS = {
    "single", "double", "triple", "home_run",
    "field_out", "strikeout", "walk", "hit_by_pitch",
    "grounded_into_double_play", "double_play", "triple_play",
    "fielders_choice", "fielders_choice_out",
    "force_out", "sac_fly", "sac_fly_double_play",
    "strikeout_double_play", "sac_bunt", "sac_bunt_double_play",
    "caught_stealing_2b", "caught_stealing_3b", "caught_stealing_home",
}

# Eventos de hit
HIT_EVENTS = {"single", "double", "triple", "home_run"}

# Eventos que cuentan como AB (excluye BB, HBP, SAC)
AB_EVENTS = PA_EVENTS - {
    "walk", "hit_by_pitch", "sac_fly", "sac_fly_double_play",
    "sac_bunt", "sac_bunt_double_play",
}

# Bases por hit para SLG
BASES = {"single": 1, "double": 2, "triple": 3, "home_run": 4}
CHADWICK_CACHE_PATH = Path("cache") / "chadwick_register.parquet"


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _filter_pa(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra solo pitches que terminan un PA (el ultimo pitch de cada PA)."""
    return df[df["events"].isin(PA_EVENTS)].copy()


def _ip_from_outs(outs: int) -> float:
    """Convierte outs registrados a innings pitched (formato decimal real)."""
    return outs / 3


def _safe_round(value, digits: int):
    """Redondea solo cuando el valor no es NaN/NA."""
    return round(value, digits) if pd.notna(value) else np.nan


def _load_chadwick_register() -> pd.DataFrame:
    """Carga el registro de Chadwick desde cache local o pybaseball."""
    if CHADWICK_CACHE_PATH.exists():
        return pd.read_parquet(CHADWICK_CACHE_PATH)

    CHADWICK_CACHE_PATH.parent.mkdir(exist_ok=True)
    register_df = chadwick_register()
    register_df.to_parquet(CHADWICK_CACHE_PATH, index=False)
    return register_df


def _player_name_lookup() -> dict[int, str]:
    """Crea un lookup MLBAM -> nombre completo desde Chadwick."""
    register_df = _load_chadwick_register().copy()
    register_df = register_df.dropna(subset=["key_mlbam"])
    register_df["key_mlbam"] = register_df["key_mlbam"].astype(int)
    register_df["full_name"] = (
        register_df["name_first"].fillna("").str.strip()
        + " "
        + register_df["name_last"].fillna("").str.strip()
    ).str.strip()
    register_df = register_df[register_df["full_name"] != ""]
    register_df = register_df.drop_duplicates(subset=["key_mlbam"], keep="last")
    return dict(zip(register_df["key_mlbam"], register_df["full_name"]))


def _mode_or_default(series: pd.Series, default: str = "UNK") -> str:
    """Retorna la moda no nula de una serie o un valor por defecto."""
    cleaned = series.dropna()
    if cleaned.empty:
        return default
    mode = cleaned.mode()
    return str(mode.iloc[0]) if not mode.empty else default


def _derive_team(grp: pd.DataFrame, role: str) -> str:
    """Deriva el equipo del bateador o pitcher usando home/away e inning_topbot."""
    if {"home_team", "away_team", "inning_topbot"}.issubset(grp.columns):
        if role == "batter":
            team_series = np.where(grp["inning_topbot"].eq("Top"), grp["away_team"], grp["home_team"])
        else:
            team_series = np.where(grp["inning_topbot"].eq("Top"), grp["home_team"], grp["away_team"])
        return _mode_or_default(pd.Series(team_series, index=grp.index))

    if "home_team" in grp.columns:
        return _mode_or_default(grp["home_team"])

    return "UNK"


def _sum_stat(grp: pd.DataFrame, candidates: list[str], default: int = 0) -> int:
    """Suma la primera columna disponible entre varios candidatos."""
    for col in candidates:
        if col in grp.columns:
            return int(pd.to_numeric(grp[col], errors="coerce").fillna(0).sum())
    return default


# ---------------------------------------------------------------------------
# Metricas de BATEADORES
# ---------------------------------------------------------------------------

def calc_batter_metrics(df: pd.DataFrame, min_pa: int = 0) -> pd.DataFrame:
    """
    Calcula metricas ofensivas por bateador desde datos Statcast.

    Parametros
    ----------
    df     : DataFrame raw de Statcast
    min_pa : minimo de plate appearances para incluir al jugador
    """
    pa_df = _filter_pa(df)
    name_lookup = _player_name_lookup()

    if pa_df.empty:
        raise ValueError("[calculator] No se encontraron plate appearances en el DataFrame.")

    results = []

    for batter_id, grp in pa_df.groupby("batter"):
        pa = len(grp)
        hits = grp["events"].isin(HIT_EVENTS).sum()
        ab = grp["events"].isin(AB_EVENTS).sum()
        bb = (grp["events"] == "walk").sum()
        hbp = (grp["events"] == "hit_by_pitch").sum()
        hr = (grp["events"] == "home_run").sum()
        k = grp["events"].isin({"strikeout", "strikeout_double_play"}).sum()

        total_bases = grp["events"].map(BASES).fillna(0).sum()

        avg = hits / ab if ab > 0 else np.nan
        obp = (hits + bb + hbp) / pa if pa > 0 else np.nan
        slg = total_bases / ab if ab > 0 else np.nan
        ops = obp + slg if pd.notna(obp) and pd.notna(slg) else np.nan
        k_pct = k / pa if pa > 0 else np.nan
        bb_pct = bb / pa if pa > 0 else np.nan

        xwoba = grp["estimated_woba_using_speedangle"].mean() \
            if "estimated_woba_using_speedangle" in grp.columns else np.nan
        xba = grp["estimated_ba_using_speedangle"].mean() \
            if "estimated_ba_using_speedangle" in grp.columns else np.nan
        xslg = grp["estimated_slg_using_speedangle"].mean() \
            if "estimated_slg_using_speedangle" in grp.columns else np.nan

        name = name_lookup.get(int(batter_id), str(batter_id))
        team = _derive_team(grp, role="batter")
        runs = _sum_stat(grp, ["batter_runs_scored", "runs_scored"], default=int(hr))
        rbi = _sum_stat(grp, ["rbi"])
        stolen_bases = _sum_stat(grp, ["sb", "stolen_bases"])

        results.append({
            "player_id": batter_id,
            "player_name": name,
            "team": team,
            "PA": pa,
            "AB": int(ab),
            "R": int(runs),
            "H": int(hits),
            "HR": int(hr),
            "RBI": int(rbi),
            "SB": int(stolen_bases),
            "BB": int(bb),
            "K": int(k),
            "AVG": _safe_round(avg, 3),
            "OBP": _safe_round(obp, 3),
            "SLG": _safe_round(slg, 3),
            "OPS": _safe_round(ops, 3),
            "K_pct": _safe_round(k_pct, 3),
            "BB_pct": _safe_round(bb_pct, 3),
            "xwOBA": _safe_round(xwoba, 3),
            "xBA": _safe_round(xba, 3),
            "xSLG": _safe_round(xslg, 3),
        })

    out = pd.DataFrame(results)

    if min_pa > 0:
        out = out[out["PA"] >= min_pa]

    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Metricas de PITCHERS
# ---------------------------------------------------------------------------

def calc_pitcher_metrics(df: pd.DataFrame, min_bf: int = 0) -> pd.DataFrame:
    """
    Calcula metricas para pitchers desde datos Statcast.

    Parametros
    ----------
    df     : DataFrame raw de Statcast
    min_bf : minimo de bateadores enfrentados
    """
    pa_df = _filter_pa(df)
    name_lookup = _player_name_lookup()

    if pa_df.empty:
        raise ValueError("[calculator] No se encontraron plate appearances en el DataFrame.")

    results = []

    for pitcher_id, grp in pa_df.groupby("pitcher"):
        bf = len(grp)
        k = grp["events"].isin({"strikeout", "strikeout_double_play"}).sum()
        bb = (grp["events"] == "walk").sum()
        hr = (grp["events"] == "home_run").sum()
        hits = grp["events"].isin(HIT_EVENTS).sum()

        outs_on_play = grp["events"].isin(AB_EVENTS - HIT_EVENTS).sum() + grp["events"].isin(
            {
                "grounded_into_double_play", "double_play", "triple_play",
                "strikeout_double_play", "sac_fly_double_play",
            }
        ).sum()
        ip = _ip_from_outs(outs_on_play)

        if "post_bat_score" in grp.columns and "bat_score" in grp.columns:
            runs_allowed = (grp["post_bat_score"] - grp["bat_score"]).clip(lower=0).sum()
        else:
            runs_allowed = np.nan

        era = (runs_allowed * 9 / ip) if ip > 0 and pd.notna(runs_allowed) else np.nan
        k9 = (k * 9 / ip) if ip > 0 else np.nan
        bb9 = (bb * 9 / ip) if ip > 0 else np.nan
        whip = (hits + bb) / ip if ip > 0 else np.nan
        k_pct = k / bf if bf > 0 else np.nan
        bb_pct = bb / bf if bf > 0 else np.nan

        if "estimated_woba_using_speedangle" in grp.columns:
            xwoba_against = grp["estimated_woba_using_speedangle"].mean()
            xera = max(0, (xwoba_against - 0.100) / 0.140 * 9) if pd.notna(xwoba_against) else np.nan
        else:
            xwoba_against = np.nan
            xera = np.nan

        pitcher_all = df[df["pitcher"] == pitcher_id]
        avg_velo = pitcher_all["release_speed"].mean() if "release_speed" in pitcher_all.columns else np.nan
        avg_spin = pitcher_all["release_spin_rate"].mean() if "release_spin_rate" in pitcher_all.columns else np.nan

        name = name_lookup.get(int(pitcher_id), str(pitcher_id))
        team = _derive_team(grp, role="pitcher")

        results.append({
            "player_id": pitcher_id,
            "player_name": name,
            "team": team,
            "BF": bf,
            "IP": round(ip, 1),
            "H_allowed": int(hits),
            "HR_allowed": int(hr),
            "BB": int(bb),
            "K": int(k),
            "K9": _safe_round(k9, 2),
            "BB9": _safe_round(bb9, 2),
            "WHIP": _safe_round(whip, 3),
            "ERA_proxy": _safe_round(era, 2),
            "K_pct": _safe_round(k_pct, 3),
            "BB_pct": _safe_round(bb_pct, 3),
            "xwOBA_against": _safe_round(xwoba_against, 3),
            "xERA": _safe_round(xera, 2),
            "avg_velo": _safe_round(avg_velo, 1),
            "avg_spin": _safe_round(avg_spin, 0),
        })

    out = pd.DataFrame(results)

    if min_bf > 0:
        out = out[out["BF"] >= min_bf]

    return out.reset_index(drop=True)
