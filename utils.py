"""
utils.py — Formateo visual de columnas numéricas.

Reglas:
  Slash stats  (AVG, OBP, SLG, wOBA…) → .xxx  (sin cero inicial)
                                          si >= 1 → x.xxx
  Porcentajes  (BB%, K%, LOB%…)        → XX.XX%  (FanGraphs los devuelve como 22.5)
  Enteros      (G, PA, HR, W, wRC+…)   → sin decimales
  Ratios       (ERA, FIP, WHIP…)       → X.XX
  Tasas 1d     (WAR, IP, K/9…)         → X.X
"""

import pandas as pd

# ── Clasificación de columnas ──────────────────────────────────────────────

SLASH_COLS = {"AVG", "OBP", "SLG", "OPS", "wOBA", "ISO", "BABIP"}

PCT_COLS = {
    "BB%", "K%", "K-BB%", "LOB%",
    "HR/FB", "LD%", "GB%", "FB%", "IFFB%", "IFH%", "BUH%",
    "Soft%", "Med%", "Hard%",
    "Pull%", "Cent%", "Oppo%",
    "SwStr%", "CStr%", "Zone%",
    "F-Strike%", "O-Swing%", "Z-Swing%", "Swing%",
    "O-Contact%", "Z-Contact%", "Contact%",
}

INT_COLS = {
    "G", "GS", "PA", "AB", "H", "1B", "2B", "3B", "HR",
    "R", "RBI", "BB", "IBB", "SO", "HBP", "SF", "SH", "GDP",
    "SB", "CS", "W", "L", "CG", "ShO", "SV", "BS", "TBF",
    "wRC+", "ERA-", "FIP-", "xFIP-",
}

RATE1_COLS = {"WAR", "IP", "K/9", "BB/9", "HR/9", "H/9", "RS/9"}

RATE2_COLS = {"ERA", "FIP", "xFIP", "SIERA", "WHIP", "K/BB", "AVG_velo"}


# ── Funciones de formato ───────────────────────────────────────────────────

def _fmt_slash(v) -> str:
    if pd.isna(v):
        return ""
    v = float(v)
    s = f"{v:.3f}"
    return s.lstrip("0") if 0 <= v < 1 else s   # .317  o  1.012


def _fmt_pct(v) -> str:
    if pd.isna(v):
        return ""
    return f"{float(v):.2f}%"


def _fmt_int(v) -> str:
    if pd.isna(v):
        return ""
    try:
        return str(int(round(float(v))))
    except (ValueError, OverflowError):
        return ""


def _fmt_rate(v, d: int = 2) -> str:
    if pd.isna(v):
        return ""
    return f"{float(v):.{d}f}"


def format_display(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve copia del DataFrame con columnas formateadas como strings."""
    out = df.copy().astype(object)
    for col in out.columns:
        if col in SLASH_COLS:
            out[col] = out[col].apply(_fmt_slash)
        elif col in PCT_COLS:
            out[col] = out[col].apply(_fmt_pct)
        elif col in INT_COLS:
            out[col] = out[col].apply(_fmt_int)
        elif col in RATE1_COLS:
            out[col] = out[col].apply(lambda v: _fmt_rate(v, 1))
        elif col in RATE2_COLS:
            out[col] = out[col].apply(lambda v: _fmt_rate(v, 2))
    return out


def put_league_after_team(df: pd.DataFrame) -> pd.DataFrame:
    """Mueve la columna League para que quede inmediatamente después de Team."""
    if "League" not in df.columns or "Team" not in df.columns:
        return df
    cols = [c for c in df.columns if c != "League"]
    idx = cols.index("Team") + 1
    cols.insert(idx, "League")
    return df[cols]
