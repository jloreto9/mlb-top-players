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
from constants import MLB_TEAMS, AVAILABLE_SEASONS, get_team_logo

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

team_full = MLB_TEAMS.get(team, team)
team_logo = get_team_logo(team_full)

st.markdown(
    f"""
    <div style="display:flex; align-items:center; background-color:#0f172a; padding:15px 20px; border-radius:12px; margin-bottom:20px; border-left: 6px solid #3b82f6;">
        <img src="{team_logo}" width="64" height="64" style="margin-right:20px; object-fit:contain;"/>
        <div>
            <h2 style="margin:0; padding:0; color:#f8fafc; font-size:1.6rem;">{team_full} ({team})</h2>
            <span style="color:#94a3b8; font-size:0.95rem;">Temporada <b>{yr}</b> · Calendario oficial y resultados</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

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

# Configuración de logo
SCHED_LOGO_CONFIG = {
    "Logo": st.column_config.ImageColumn("Logo", width="small"),
}

# ── Columnas de display ────────────────────────────────────────────────────
PLAYED_COLS = ["Logo", "Date", "Home_Away", "Opp", "Res", "R", "RA", "Pitcher_W", "Pitcher_L", "Save", "Status"]
UPCOMING_COLS = ["Logo", "Date", "Home_Away", "Opp", "SP_Opp", "Status"]

# ── Tabs: Jugados | Próximos ───────────────────────────────────────────────
played_tab, upcoming_tab = st.tabs([
    f"✅ Jugados ({len(played)})",
    f"🗓️ Próximos ({len(upcoming)})",
])

with played_tab:
    if played.empty:
        st.info("Aún no hay juegos completados en esta temporada.")
    else:
        played_disp = played.copy()
        if "Opp" in played_disp.columns:
            played_disp["Logo"] = played_disp["Opp"].apply(get_team_logo)
        disp_p = played_disp[[c for c in PLAYED_COLS if c in played_disp.columns]].reset_index(drop=True)
        disp_p_rev = disp_p.iloc[::-1].reset_index(drop=True)
        disp_p_rev.index += 1
        st.dataframe(disp_p_rev, column_config=SCHED_LOGO_CONFIG, use_container_width=True, height=600)

with upcoming_tab:
    if upcoming.empty:
        st.success("Temporada finalizada — No quedan juegos por disputar.")
    else:
        upcoming_disp = upcoming.copy()
        if "Opp" in upcoming_disp.columns:
            upcoming_disp["Logo"] = upcoming_disp["Opp"].apply(get_team_logo)
        disp_u = upcoming_disp[[c for c in UPCOMING_COLS if c in upcoming_disp.columns]].reset_index(drop=True)
        disp_u.index += 1
        st.dataframe(disp_u, column_config=SCHED_LOGO_CONFIG, use_container_width=True, height=600)

