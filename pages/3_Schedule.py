"""
pages/3_Schedule.py
Schedule y resultados por equipo vía MLB Stats API oficial.
Muestra partidos jugados (resultado, score, pitchers de decisión) y próximos juegos con lanzadores abridores probables.
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

import fetcher
from constants import MLB_TEAMS, AVAILABLE_SEASONS

st.set_page_config(
    page_title="Schedule · MLB Stats",
    page_icon="📅",
    layout="wide",
)

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📅 Schedule")
    st.caption("Fuente: MLB Stats API Oficial")
    st.divider()

    # Obtener lista única de equipos ordenados
    team_keys = sorted(list(set(MLB_TEAMS.keys())))
    
    team_label = st.selectbox(
        "Equipo",
        options=team_keys,
        format_func=lambda k: f"{k} — {MLB_TEAMS[k]}",
        index=team_keys.index("NYY") if "NYY" in team_keys else 0,
    )
    year = st.selectbox(
        "Temporada",
        options=AVAILABLE_SEASONS,
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
if run_btn or st.session_state.sched_df is None or st.session_state.sched_team != team_label or st.session_state.sched_year != year:
    with st.spinner(f"Cargando calendario {MLB_TEAMS.get(team_label, team_label)} {year}..."):
        try:
            df = fetcher.get_team_schedule(year, team_label)
            st.session_state.sched_df = df
            st.session_state.sched_team = team_label
            st.session_state.sched_year = year
        except Exception as e:
            st.error(f"❌ Error cargando schedule: {e}")
            st.stop()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📅 Calendario & Resultados por Equipo")

if st.session_state.sched_df is None or st.session_state.sched_df.empty:
    st.info("👈 Selecciona el equipo y la temporada, luego presiona **Cargar schedule**.")
    st.stop()

df = st.session_state.sched_df.copy()
team = st.session_state.sched_team
yr = st.session_state.sched_year

st.subheader(f"🏟️ {MLB_TEAMS.get(team, team)} ({team}) — Temporada {yr}")

# ── Split pasados / futuros ─────────────────────────────────────────────────
played = df[df["Res"].isin(["W", "L", "T"])].copy()
upcoming = df[~df["Res"].isin(["W", "L", "T"])].copy()

# ── Resumen de record ──────────────────────────────────────────────────────
if not played.empty:
    wins = (played["Res"] == "W").sum()
    losses = (played["Res"] == "L").sum()
    ties = (played["Res"] == "T").sum()

    rs = pd.to_numeric(played["R"], errors="coerce").sum()
    ra = pd.to_numeric(played["RA"], errors="coerce").sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Récord W-L", f"{wins}-{losses}" + (f"-{ties}" if ties else ""))
    m2.metric("Juegos Jugados", len(played))
    m3.metric("Carreras Anotadas", int(rs))
    m4.metric("Diferencial", f"{int(rs - ra):+d}")

st.divider()

# ── Columnas de display ────────────────────────────────────────────────────
PLAYED_COLS = ["Date", "Home_Away", "Opp", "Res", "R", "RA", "Pitcher_W", "Pitcher_L", "Save", "Status"]
UPCOMING_COLS = ["Date", "Home_Away", "Opp", "SP_Opp", "Status"]

def _color_row(row):
    res = str(row.get("Res", ""))
    if res.startswith("W"):
        return ["background-color: #1a3a1a; color: #7dff7d"] * len(row)
    elif res.startswith("L"):
        return ["background-color: #3a1a1a; color: #ff7d7d"] * len(row)
    return [""] * len(row)

# ── Tabs: Jugados | Próximos ───────────────────────────────────────────────
played_tab, upcoming_tab = st.tabs([
    f"✅ Jugados ({len(played)})",
    f"🗓️ Próximos ({len(upcoming)})",
])

with played_tab:
    if played.empty:
        st.info("Aún no hay juegos completados en esta temporada.")
    else:
        disp_p = played[[c for c in PLAYED_COLS if c in played.columns]].reset_index(drop=True)
        # Mostrar los más recientes primero
        disp_p_rev = disp_p.iloc[::-1].reset_index(drop=True)
        disp_p_rev.index += 1
        styled = disp_p_rev.style.apply(_color_row, axis=1)
        st.dataframe(styled, use_container_width=True, height=600)

with upcoming_tab:
    if upcoming.empty:
        st.success("Temporada finalizada — No quedan juegos por disputar.")
    else:
        disp_u = upcoming[[c for c in UPCOMING_COLS if c in upcoming.columns]].reset_index(drop=True)
        disp_u.index += 1
        st.dataframe(disp_u, use_container_width=True, height=600)

