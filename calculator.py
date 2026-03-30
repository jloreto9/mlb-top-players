"""
calculator.py
-------------
Calcula métricas agregadas desde datos pitch-by-pitch de Statcast.

Métricas de bateadores : xwOBA, xBA, xSLG, AVG, OBP, SLG, OPS, K%, BB%, HR, PA
Métricas de pitchers   : xERA, AVG_velo, AVG_spin, K%, BB%, HR_allowed, IP
"""

import pandas as pd
import numpy as np


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
AB_EVENTS = PA_EVENTS - {"walk", "hit_by_pitch", "sac_fly", "sac_fly_double_play",
                          "sac_bunt", "sac_bunt_double_play"}

# Bases por hit para SLG
BASES = {"single": 1, "double": 2, "triple": 3, "home_run": 4}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _filter_pa(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra solo pitches que terminan un PA (el último pitch de cada PA)."""
    return df[df["events"].isin(PA_EVENTS)].copy()


def _ip_from_outs(outs: int) -> float:
    """Convierte outs registrados a innings pitched (formato decimal real)."""
    return outs / 3


# ---------------------------------------------------------------------------
# Métricas de BATEADORES
# ---------------------------------------------------------------------------

def calc_batter_metrics(df: pd.DataFrame, min_pa: int = 0) -> pd.DataFrame:
    """
    Calcula métricas ofensivas por bateador desde datos Statcast.

    Parámetros
    ----------
    df     : DataFrame raw de Statcast
    min_pa : mínimo de plate appearances para incluir al jugador

    Retorna
    -------
    DataFrame con una fila por bateador y sus métricas
    """
    # Solo filas con PA terminado
    pa_df = _filter_pa(df)

    if pa_df.empty:
        raise ValueError("[calculator] No se encontraron plate appearances en el DataFrame.")

    results = []

    for batter_id, grp in pa_df.groupby("batter"):
        pa   = len(grp)
        hits = grp["events"].isin(HIT_EVENTS).sum()
        ab   = grp["events"].isin(AB_EVENTS).sum()
        bb   = (grp["events"] == "walk").sum()
        hbp  = (grp["events"] == "hit_by_pitch").sum()
        hr   = (grp["events"] == "home_run").sum()
        k    = grp["events"].isin({"strikeout", "strikeout_double_play"}).sum()

        # Bases totales para SLG
        total_bases = grp["events"].map(BASES).fillna(0).sum()

        avg  = hits / ab if ab > 0 else np.nan
        obp  = (hits + bb + hbp) / pa if pa > 0 else np.nan
        slg  = total_bases / ab if ab > 0 else np.nan
        ops  = obp + slg if (not np.isnan(obp) and not np.isnan(slg)) else np.nan
        k_pct = k / pa if pa > 0 else np.nan
        bb_pct = bb / pa if pa > 0 else np.nan

        # Métricas Statcast (promedio de estimaciones por PA cuando están disponibles)
        xwoba = grp["estimated_woba_using_speedangle"].mean() \
                if "estimated_woba_using_speedangle" in grp.columns else np.nan
        xba   = grp["estimated_ba_using_speedangle"].mean() \
                if "estimated_ba_using_speedangle" in grp.columns else np.nan
        xslg  = grp["estimated_slg_using_speedangle"].mean() \
                if "estimated_slg_using_speedangle" in grp.columns else np.nan

        # Nombre del jugador (primera aparición no nula)
        name = grp["player_name"].dropna().iloc[0] if "player_name" in grp.columns \
               and not grp["player_name"].dropna().empty else str(batter_id)

        # Liga (home_team da una pista; tomamos la moda)
        league = grp["home_team"].mode().iloc[0] if "home_team" in grp.columns else "UNK"

        results.append({
            "player_id" : batter_id,
            "player_name": name,
            "league_raw": league,          # se refinará en ranker.py
            "PA"        : pa,
            "AB"        : int(ab),
            "H"         : int(hits),
            "HR"        : int(hr),
            "BB"        : int(bb),
            "K"         : int(k),
            "AVG"       : round(avg, 3)   if not np.isnan(avg)  else np.nan,
            "OBP"       : round(obp, 3)   if not np.isnan(obp)  else np.nan,
            "SLG"       : round(slg, 3)   if not np.isnan(slg)  else np.nan,
            "OPS"       : round(ops, 3)   if not np.isnan(ops)  else np.nan,
            "K_pct"     : round(k_pct, 3) if not np.isnan(k_pct) else np.nan,
            "BB_pct"    : round(bb_pct, 3) if not np.isnan(bb_pct) else np.nan,
            "xwOBA"     : round(xwoba, 3) if not np.isnan(xwoba) else np.nan,
            "xBA"       : round(xba, 3)   if not np.isnan(xba)  else np.nan,
            "xSLG"      : round(xslg, 3)  if not np.isnan(xslg) else np.nan,
        })

    out = pd.DataFrame(results)

    if min_pa > 0:
        out = out[out["PA"] >= min_pa]

    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Métricas de PITCHERS
# ---------------------------------------------------------------------------

def calc_pitcher_metrics(df: pd.DataFrame, min_bf: int = 0) -> pd.DataFrame:
    """
    Calcula métricas para pitchers desde datos Statcast.

    Parámetros
    ----------
    df     : DataFrame raw de Statcast
    min_bf : mínimo de bateadores enfrentados (batters faced) para incluir

    Retorna
    -------
    DataFrame con una fila por pitcher y sus métricas
    """
    pa_df = _filter_pa(df)

    if pa_df.empty:
        raise ValueError("[calculator] No se encontraron plate appearances en el DataFrame.")

    results = []

    for pitcher_id, grp in pa_df.groupby("pitcher"):
        bf   = len(grp)                          # batters faced ≈ PA del pitcher
        k    = grp["events"].isin({"strikeout", "strikeout_double_play"}).sum()
        bb   = (grp["events"] == "walk").sum()
        hbp  = (grp["events"] == "hit_by_pitch").sum()
        hr   = (grp["events"] == "home_run").sum()
        hits = grp["events"].isin(HIT_EVENTS).sum()

        # Outs registrados → IP
        # En Statcast, 'outs_when_up' indica outs antes del PA; necesitamos outs generados
        # Aproximamos: cada AB que no es hit ni BB ni HBP genera 1 out (simplificación)
        # Más correcto: contar outs por descripción de evento
        outs_on_play = grp["events"].isin(
            AB_EVENTS - HIT_EVENTS
        ).sum() + grp["events"].isin(
            {"grounded_into_double_play", "double_play", "triple_play",
             "strikeout_double_play", "sac_fly_double_play"}
        ).sum()  # doble plays suman un out extra
        ip = _ip_from_outs(outs_on_play)

        # ERA estimada (earned runs — Statcast no los registra directamente)
        # Usamos post_bat_score delta como proxy de carreras permitidas
        if "post_bat_score" in grp.columns and "bat_score" in grp.columns:
            runs_allowed = (grp["post_bat_score"] - grp["bat_score"]).clip(lower=0).sum()
        else:
            runs_allowed = np.nan

        era = (runs_allowed * 9 / ip) if (ip > 0 and not np.isnan(runs_allowed)) else np.nan

        k9  = (k * 9 / ip) if ip > 0 else np.nan
        bb9 = (bb * 9 / ip) if ip > 0 else np.nan
        whip = (hits + bb) / ip if ip > 0 else np.nan

        k_pct  = k / bf  if bf > 0 else np.nan
        bb_pct = bb / bf if bf > 0 else np.nan

        # xERA: media de xwOBA contra este pitcher × escala a ERA
        # xERA = estimated_woba_using_speedangle promedio * factor de liga (~4.5 escala)
        # Nota: xERA oficial de Statcast = (xwOBA_against - .100) / .140 * 9  (aprox)
        if "estimated_woba_using_speedangle" in grp.columns:
            xwoba_against = grp["estimated_woba_using_speedangle"].mean()
            # Fórmula aproximada usada por Baseball Savant
            xera = max(0, (xwoba_against - 0.100) / 0.140 * 9) \
                   if not np.isnan(xwoba_against) else np.nan
        else:
            xwoba_against = np.nan
            xera = np.nan

        # Velo y spin (todos los pitches, no solo PA finales — recalcular sobre df completo)
        pitcher_all = df[df["pitcher"] == pitcher_id]
        avg_velo  = pitcher_all["release_speed"].mean() \
                    if "release_speed" in pitcher_all.columns else np.nan
        avg_spin  = pitcher_all["release_spin_rate"].mean() \
                    if "release_spin_rate" in pitcher_all.columns else np.nan

        name = grp["player_name"].dropna().iloc[0] if "player_name" in grp.columns \
               and not grp["player_name"].dropna().empty else str(pitcher_id)

        league = grp["home_team"].mode().iloc[0] if "home_team" in grp.columns else "UNK"

        results.append({
            "player_id"   : pitcher_id,
            "player_name" : name,
            "league_raw"  : league,
            "BF"          : bf,
            "IP"          : round(ip, 1),
            "H_allowed"   : int(hits),
            "HR_allowed"  : int(hr),
            "BB"          : int(bb),
            "K"           : int(k),
            "K9"          : round(k9, 2)   if not np.isnan(k9)   else np.nan,
            "BB9"         : round(bb9, 2)  if not np.isnan(bb9)  else np.nan,
            "WHIP"        : round(whip, 3) if not np.isnan(whip) else np.nan,
            "ERA_proxy"   : round(era, 2)  if not np.isnan(era)  else np.nan,
            "K_pct"       : round(k_pct, 3)  if not np.isnan(k_pct)  else np.nan,
            "BB_pct"      : round(bb_pct, 3) if not np.isnan(bb_pct) else np.nan,
            "xwOBA_against": round(xwoba_against, 3) if not np.isnan(xwoba_against) else np.nan,
            "xERA"        : round(xera, 2) if not np.isnan(xera) else np.nan,
            "avg_velo"    : round(avg_velo, 1) if not np.isnan(avg_velo) else np.nan,
            "avg_spin"    : round(avg_spin, 0) if not np.isnan(avg_spin) else np.nan,
        })

    out = pd.DataFrame(results)

    if min_bf > 0:
        out = out[out["BF"] >= min_bf]

    return out.reset_index(drop=True)
