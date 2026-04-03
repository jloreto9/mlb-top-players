"""
pages/3_Schedule.py
Schedule y record por equipo — Baseball Reference via pybaseball.
Muestra partidos jugados (resultado, score, pitchers) y próximos juegos.
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

from pybaseball import schedule_and_record

st.set_page_config(
    page_title="Schedule · MLB Stats",
    page_icon="📅",
    layout="wide",
)

# ── Equipos (abreviatura BRef → nombre completo) ───────────────────────────
TEAMS = {
    # AL East
    "BAL": "Baltimore Orioles",
    "BOS": "Boston Red Sox",
    "NYY": "New York Yankees",
    "TBR": "Tampa Bay Rays",
    "TOR": "Toronto Blue Jays",
    # AL Central
    "CHW": "Chicago White Sox",
    "CLE": "Cleveland Guardians",
    "DET": "Detroit Tigers",
    "KCR": "Kansas City Royals",
    "MIN": "Minnesota Twins",
    # AL West
    "HOU": "Houston Astros",
    "LAA": "Los Angeles Angels",
    "OAK": "Oakland Athletics",
    "SEA": "Seattle Mariners",
    "TEX": "Texas Rangers",
    # NL East
    "ATL": "Atlanta Braves",
    "MIA": "Miami Marlins",
    "NYM": "New York Mets",
    "PHI": "Philadelphia Phillies",
    "WSN": "Washington Nationals",
    # NL Central
    "CHC": "Chicago Cubs",
    "CIN": "Cincinnati Reds",
    "MIL": "Milwaukee Brewers",
    "PIT": "Pittsburgh Pirates",
    "STL": "St. Louis Cardinals",
    # NL West
    "ARI": "Arizona Diamondbacks",
    "COL": "Colorado Rockies",
    "LAD": "Los Angeles Dodgers",
    "SDP": "San Diego Padres",
    "SFG": "San Francisco Giants",
}

_NOW_YEAR = datetime.now().year

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📅 Schedule")
    st.caption("Fuente: Baseball Reference via pybaseball")
    st.divider()

    team_label = st.selectbox(
        "Equipo",
        options=list(TEAMS.keys()),
        format_func=lambda k: f"{k} — {TEAMS[k]}",
    )
    year = st.selectbox(
        "Temporada",
        options=list(range(_NOW_YEAR, 2009, -1)),
        index=0,
    )
    force = st.checkbox("🔄 Forzar re-descarga", value=False)
    st.divider()
    run_btn = st.button("▶ Cargar schedule", type="primary", use_container_width=True)

# ── Session state ────────────────────────────────────────────────────────────
for k in ("sched_df", "sched_team", "sched_year"):
    if k not in st.session_state:
        st.session_state[k] = None

# ── Carga ─────────────────────────────────────────────────────────────────────
if run_btn:
    if force:
        # Limpiar cache de pybaseball para este equipo/año
        from pybaseball import cache as pybb_cache
        pybb_cache.purge()

    with st.spinner(f"Descargando schedule {TEAMS[team_label]} {year}..."):
        try:
            df = schedule_and_record(year, team_label)
            st.session_state.sched_df   = df
            st.session_state.sched_team = team_label
            st.session_state.sched_year = year
        except Exception as e:
            st.error(f"❌ {e}")
            st.stop()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📅 Schedule por Equipo")

if st.session_state.sched_df is None:
    st.info("👈 Selecciona el equipo y la temporada, luego presiona **Cargar schedule**.")
    st.stop()

df   = st.session_state.sched_df.copy()
team = st.session_state.sched_team
yr   = st.session_state.sched_year

st.subheader(f"{TEAMS[team]} ({team}) — {yr}")

# ── Limpieza y split pasados/futuros ─────────────────────────────────────────

# Normalizar columna W/L (puede llamarse W/L o similar)
wl_col = next((c for c in df.columns if c in ("W/L", "Unnamed: 5", "Result")), None)

# Juegos jugados: tienen resultado (W, L, W-wo, L-wo, T)
played_mask = df.get(wl_col, pd.Series(dtype=str)).str.match(r"^[WLT]", na=False) if wl_col else pd.Series([False]*len(df))
played = df[played_mask].copy()
upcoming = df[~played_mask].copy()

# ── Resumen de record ──────────────────────────────────────────────────────
if not played.empty and wl_col:
    wins   = played[wl_col].str.startswith("W").sum()
    losses = played[wl_col].str.startswith("L").sum()
    ties   = played[wl_col].str.startswith("T").sum()

    r_col  = next((c for c in played.columns if c == "R"), None)
    ra_col = next((c for c in played.columns if c == "RA"), None)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Record",  f"{wins}-{losses}" + (f"-{ties}" if ties else ""))
    m2.metric("Jugados", len(played))
    if r_col and ra_col:
        rs  = pd.to_numeric(played[r_col],  errors="coerce").sum()
        ra  = pd.to_numeric(played[ra_col], errors="coerce").sum()
        m3.metric("Carreras Anotadas", int(rs))
        m4.metric("Dif. Carreras",     f"{int(rs - ra):+d}")

st.divider()

# ── Columnas de display ────────────────────────────────────────────────────
PLAYED_COLS   = ["Date", "Tm", "Home_Away", "Opp", wl_col, "R", "RA",
                 "Win", "Loss", "Save", "Inn", "Attendance", "Streak", "Rank", "GB"]
UPCOMING_COLS = ["Date", "Tm", "Home_Away", "Opp", "Time", "D/N"]

def _sel(df, cols):
    return df[[c for c in cols if c and c in df.columns]]

def _rename(df):
    return df.rename(columns={
        "Tm": "Equipo", "Home_Away": "L/V", "Opp": "Rival",
        wl_col: "Res", "R": "R", "RA": "RA",
        "Win": "Pitcher W", "Loss": "Pitcher L", "Save": "Save",
        "Inn": "Inn", "Attendance": "Asistencia",
        "Streak": "Racha", "Rank": "Pos", "GB": "GB",
    })

# ── Colorear resultado ──────────────────────────────────────────────────────
def _color_row(row):
    res = str(row.get("Res", ""))
    if res.startswith("W"):
        return ["background-color: #1a3a1a; color: #7dff7d"] * len(row)
    elif res.startswith("L"):
        return ["background-color: #3a1a1a; color: #ff7d7d"] * len(row)
    return [""] * len(row)

# ── Tab: Jugados | Próximos ───────────────────────────────────────────────
played_tab, upcoming_tab = st.tabs([
    f"✅ Jugados ({len(played)})",
    f"🗓️ Próximos ({len(upcoming)})",
])

with played_tab:
    if played.empty:
        st.info("Aún no hay juegos jugados.")
    else:
        display = _rename(_sel(played, PLAYED_COLS)).reset_index(drop=True)
        display.index += 1

        # Mostrar los más recientes primero
        display_rev = display.iloc[::-1].reset_index(drop=True)
        display_rev.index = range(len(display_rev), 0, -1)

        styled = display_rev.style.apply(_color_row, axis=1)
        st.dataframe(styled, use_container_width=True, height=600)

with upcoming_tab:
    if upcoming.empty:
        st.success("No quedan juegos por jugar (temporada finalizada).")
    else:
        display = _rename(_sel(upcoming, UPCOMING_COLS)).reset_index(drop=True)
        display.index += 1
        st.dataframe(display, use_container_width=True, height=600)
