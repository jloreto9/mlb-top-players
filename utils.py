"""
utils.py — Formateo visual de columnas numéricas y helpers de UI.

Reglas:
  Slash stats  (AVG, OBP, SLG, wOBA…)  → .xxx  (sin cero inicial si < 1)
  Porcentajes  (BB%, K%, Barrel%…)    → XX.X% o XX.XX% (detecta automáticamente si viene en 0.25 o 25.0)
  Diferenciales(diff_wOBA, diff_ERA…) → +X.XXX / -X.XXX
  Z-Scores     (z_HR, z_Total…)       → +X.XX / -X.XX
  Enteros      (G, PA, HR, W, Rank…)  → sin decimales
  Ratios       (ERA, FIP, WHIP…)      → X.XX
  Tasas 1d     (WAR, IP, K/9, EV…)    → X.X
"""

import unicodedata
import pandas as pd

# ── Clasificación de columnas ──────────────────────────────────────────────

TEXT_COLS = {
    "Name", "Player", "Pitcher", "Batter", "Opponent", "Team", "Tm",
    "Pos", "Verdict", "Two_Start", "Matchup", "Status", "Recommendation", "League"
}

SLASH_COLS = {"AVG", "OBP", "SLG", "OPS", "wOBA", "xwOBA", "xBA", "xSLG", "ISO", "BABIP"}

PCT_COLS = {
    "BB%", "K%", "K-BB%", "LOB%", "CSW%",
    "HR/FB", "LD%", "GB%", "FB%", "IFFB%", "IFH%", "BUH%",
    "Soft%", "Med%", "Hard%", "HardHit%", "Barrel%", "SweetSpot%",
    "Pull%", "Cent%", "Oppo%",
    "SwStr%", "CStr%", "Zone%", "FP%",
    "F-Strike%", "O-Swing%", "Z-Swing%", "Swing%",
    "O-Contact%", "Z-Contact%", "Contact%",
}

DIFF_SLASH_COLS = {"diff_BA", "diff_SLG", "diff_wOBA"}
DIFF_RATE_COLS = {"diff_ERA"}

ZSCORE_COLS = {
    "z_R", "z_HR", "z_RBI", "z_SB", "z_AVG", "z_OBP",
    "z_W", "z_SV", "z_HLD", "z_SO", "z_ERA", "z_WHIP",
    "z_Total", "z_Points",
}

INT_COLS = {
    "G", "GS", "PA", "AB", "H", "1B", "2B", "3B", "HR",
    "R", "RBI", "BB", "IBB", "SO", "HBP", "SF", "SH", "GDP",
    "SB", "CS", "W", "L", "CG", "ShO", "SV", "BS", "HLD", "TBF",
    "wRC+", "ERA-", "FIP-", "xFIP-", "Stuff+", "Location+", "Pitching+",
    "Fantasy_Rank", "Rank", "Pos", "Inn", "PO", "A", "E", "DP", "DRS",
}

RATE1_COLS = {"WAR", "IP", "K/9", "BB/9", "HR/9", "H/9", "RS/9", "EV", "maxEV", "UZR", "UZR/150", "Def", "Fantasy_Pts"}

RATE2_COLS = {"ERA", "xERA", "FIP", "xFIP", "SIERA", "botERA", "WHIP", "K/BB", "AVG_velo"}


def get_team_logo(team_name_or_abbr: str | None) -> str:
    """Devuelve la URL del logo oficial para un equipo, o un logo genérico de MLB."""
    try:
        from constants import get_team_logo as _gtl
        return _gtl(team_name_or_abbr)
    except Exception:
        return "https://a.espncdn.com/i/teamlogos/mlb/500/mlb.png"


def clean_ascii_text(val) -> str:
    """
    Elimina acentos/tildes y normaliza caracteres a su equivalente ASCII base:
    á->a, é->e, í->i, ó->o, ú->u, ñ->n, y limpia escapes como \\xc3\\xa1 o \\'.
    """
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    if "\\x" in s or "\\u" in s:
        try:
            s = s.encode("raw_unicode_escape").decode("unicode_escape").encode("latin1").decode("utf-8")
        except Exception:
            try:
                s = s.encode("raw_unicode_escape").decode("utf-8")
            except Exception:
                pass
    s = s.replace("\\'", "'").replace('\\"', '"')
    s = s.replace("ñ", "n").replace("Ñ", "N")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return s


def _fmt_slash(v) -> str:
    if pd.isna(v):
        return ""
    try:
        val = float(v)
        s = f"{val:.3f}"
        return s.lstrip("0") if 0 <= val < 1 else s
    except (ValueError, TypeError):
        return str(v)


def _fmt_pct(v) -> str:
    if pd.isna(v):
        return ""
    try:
        val = float(v)
        # Si viene en escala [0, 1] (ej: 0.225) multiplicar por 100
        # Si ya viene en escala [0, 100] (ej: 22.5) dejar tal cual
        if abs(val) <= 1.0:
            val = val * 100.0
        return f"{val:.1f}%"
    except (ValueError, TypeError):
        return str(v)


def _fmt_diff(v, decimals: int = 3) -> str:
    if pd.isna(v):
        return ""
    try:
        val = float(v)
        return f"{val:+.{decimals}f}"
    except (ValueError, TypeError):
        return str(v)


def _fmt_zscore(v) -> str:
    if pd.isna(v):
        return ""
    try:
        val = float(v)
        return f"{val:+.2f}"
    except (ValueError, TypeError):
        return str(v)


def _fmt_int(v) -> str:
    if pd.isna(v):
        return ""
    try:
        return str(int(round(float(v))))
    except (ValueError, OverflowError, TypeError):
        return str(v)


def _fmt_rate(v, d: int = 2) -> str:
    if pd.isna(v):
        return ""
    try:
        return f"{float(v):.{d}f}"
    except (ValueError, TypeError):
        return str(v)


def format_display(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve copia del DataFrame con columnas formateadas como strings estéticas y sin acentos."""
    out = df.copy().astype(object)
    for col in out.columns:
        if col in SLASH_COLS:
            out[col] = out[col].apply(_fmt_slash)
        elif col in PCT_COLS:
            out[col] = out[col].apply(_fmt_pct)
        elif col in DIFF_SLASH_COLS:
            out[col] = out[col].apply(lambda v: _fmt_diff(v, 3))
        elif col in DIFF_RATE_COLS:
            out[col] = out[col].apply(lambda v: _fmt_diff(v, 2))
        elif col in ZSCORE_COLS:
            out[col] = out[col].apply(_fmt_zscore)
        elif col in INT_COLS:
            out[col] = out[col].apply(_fmt_int)
        elif col in RATE1_COLS:
            out[col] = out[col].apply(lambda v: _fmt_rate(v, 1))
        elif col in RATE2_COLS:
            out[col] = out[col].apply(lambda v: _fmt_rate(v, 2))
        elif col in TEXT_COLS or out[col].dtype == object:
            out[col] = out[col].apply(clean_ascii_text)
    return out


def put_league_after_team(df: pd.DataFrame) -> pd.DataFrame:
    """Mueve la columna League para que quede inmediatamente después de Team o Pos."""
    if "League" not in df.columns:
        return df
    cols = [c for c in df.columns if c != "League"]
    if "Team" in cols:
        idx = cols.index("Team") + 1
    elif "Pos" in cols:
        idx = cols.index("Pos") + 1
    else:
        idx = 1
    cols.insert(idx, "League")
    return df[cols]

