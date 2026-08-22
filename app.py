"""
app.py — PÁGINA PRINCIPAL & CENTRO DE CONTROL
MLB Analytics & Fantasy Baseball Suite
"""

import sys
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px

import fetcher
import fantasy
from constants import TEAM_LEAGUE, TBAT_COLS, TPIT_COLS, TFIELD_COLS, LOWER_IS_BETTER
from utils import format_display, put_league_after_team

# ── Configuración ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="⚾ MLB Analytics & Fantasy Suite",
    page_icon="⚾",
    layout="wide",
)

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚾ MLB Intelligence")
    st.caption("Analítica Avanzada & Fantasy Hub")
    st.divider()

    year = st.selectbox(
        "Temporada",
        options=list(range(2026, 2009, -1)),
        index=1,          # default: 2025
    )
    force = st.checkbox("🔄 Forzar re-descarga", value=False)
    st.divider()
    run_btn = st.button("▶ Cargar datos", type="primary", use_container_width=True)

# ── Session state ──────────────────────────────────────────────────────────
for key in ("team_bat_df", "team_pit_df", "team_field_df", "loaded_year", "quick_bat", "quick_pit"):
    if key not in st.session_state:
        st.session_state[key] = None

# ── Carga ──────────────────────────────────────────────────────────────────
if run_btn or st.session_state.team_bat_df is None or st.session_state.loaded_year != year:
    with st.spinner(f"Cargando analítica MLB {year}..."):
        try:
            st.session_state.team_bat_df   = fetcher.team_bat(year, force=force)
            st.session_state.team_pit_df   = fetcher.team_pit(year, force=force)
            st.session_state.team_field_df = fetcher.team_field(year, force=force)
            st.session_state.quick_bat     = fantasy.calculate_batting_fantasy(fetcher.batting(year, force=force))
            st.session_state.quick_pit     = fantasy.calculate_pitching_fantasy(fetcher.pitching(year, force=force))
            st.session_state.loaded_year   = year
        except Exception as e:
            st.error(f"❌ Error al cargar datos: {e}")
            st.stop()

# ── Header ─────────────────────────────────────────────────────────────────
st.title("⚾ MLB Analytics & Fantasy Intelligence Suite")

yr  = st.session_state.loaded_year
tbd = st.session_state.team_bat_df.copy()
tpd = st.session_state.team_pit_df.copy()
tfd = st.session_state.team_field_df.copy() if st.session_state.team_field_df is not None else pd.DataFrame()
q_bat = st.session_state.quick_bat
q_pit = st.session_state.quick_pit

if yr >= datetime.now().year:
    st.warning(
        f"⚠️ Temporada **{yr}** en curso. "
        "Selecciona **2025** para analizar una temporada completa consolidada."
    )
else:
    st.caption(f"Temporada **{yr}** · Datos de FanGraphs, Statcast y MLB Stats API")

# ── Tarjetas de Resumen & Destacados ────────────────────────────────────────
st.markdown("### 🌟 Líderes de la Temporada")
k1, k2, k3, k4 = st.columns(4)

if q_bat is not None and not q_bat.empty:
    # Líder WAR / Fantasy
    bat_sort_col = "WAR" if "WAR" in q_bat.columns else ("Fantasy_Pts" if "Fantasy_Pts" in q_bat.columns else ("OPS" if "OPS" in q_bat.columns else "R"))
    top_war_bat = q_bat.sort_values(bat_sort_col, ascending=False).iloc[0]
    val_disp = f"{top_war_bat[bat_sort_col]} {bat_sort_col}" if bat_sort_col in top_war_bat else ""
    k1.metric(
        label=f"👑 Líder Bateo ({val_disp})",
        value=top_war_bat.get("Name", "N/A"),
        delta=f"{top_war_bat.get('Team', top_war_bat.get('Tm', ''))} · {top_war_bat.get('Pos', 'DH')}",
        delta_color="off"
    )

    # Líder HR / RBI
    hr_col = "HR" if "HR" in q_bat.columns else ("RBI" if "RBI" in q_bat.columns else "H")
    if hr_col in q_bat.columns:
        top_hr_bat = q_bat.sort_values(hr_col, ascending=False).iloc[0]
        k2.metric(
            label=f"💥 Líder {hr_col} ({int(top_hr_bat[hr_col])} {hr_col})",
            value=top_hr_bat.get("Name", "N/A"),
            delta=f"{top_hr_bat.get('Team', top_hr_bat.get('Tm', ''))} · {top_hr_bat.get('Pos', 'DH')}",
            delta_color="off"
        )

if q_pit is not None and not q_pit.empty:
    # Líder WAR / Fantasy Pitcheo
    pit_sort_col = "WAR" if "WAR" in q_pit.columns else ("Fantasy_Pts" if "Fantasy_Pts" in q_pit.columns else ("SO" if "SO" in q_pit.columns else "W"))
    top_war_pit = q_pit.sort_values(pit_sort_col, ascending=False).iloc[0]
    val_pit_disp = f"{top_war_pit[pit_sort_col]} {pit_sort_col}" if pit_sort_col in top_war_pit else ""
    k3.metric(
        label=f"👑 Líder Pitcheo ({val_pit_disp})",
        value=top_war_pit.get("Name", "N/A"),
        delta=f"{top_war_pit.get('Team', top_war_pit.get('Tm', ''))} · {top_war_pit.get('Pos', 'SP')}",
        delta_color="off"
    )

    # Líder Ponches SO / K
    k_col = "SO" if "SO" in q_pit.columns else ("K" if "K" in q_pit.columns else "W")
    if k_col in q_pit.columns:
        top_k_pit = q_pit.sort_values(k_col, ascending=False).iloc[0]
        k4.metric(
            label=f"⚡ Líder Ponches ({int(top_k_pit[k_col])} K)",
            value=top_k_pit.get("Name", "N/A"),
            delta=f"{top_k_pit.get('Team', top_k_pit.get('Tm', ''))} · {top_k_pit.get('Pos', 'SP')}",
            delta_color="off"
        )

st.divider()

# ── Módulos de la Suite ────────────────────────────────────────────────────
st.markdown("### 🧭 Explorar Módulos del Sistema")
m_col1, m_col2, m_col3, m_col4 = st.columns(4)

with m_col1:
    st.info("#### 📊 Leaderboard Individual\nRankings completos con filtro por posición (C, 1B, 2B, SS, OF, SP, RP), z-scores y métricas avanzadas.")
with m_col2:
    st.success("#### 🎯 Fantasy Hub\nDetector Buy-Low / Sell-High de Statcast, SP Streamer con Two-Starts y jerarquías de Bullpen.")
with m_col3:
    st.warning("#### 🏆 Standings & Postseason\nPosiciones oficiales en vivo por división y carrera por el Comodín (Wild Card).")
with m_col4:
    st.error("#### 📅 Calendario & Schedule\nResultados por equipo, abridores probables y contexto de parque.")

st.divider()


# ── Helpers de Estadísticas Colectivas ──────────────────────────────────────

def _add_league(df: pd.DataFrame, col: str = "Team") -> pd.DataFrame:
    df = df.copy()
    if col in df.columns:
        df["League"] = df[col].str.upper().map(TEAM_LEAGUE).fillna("UNK")
    return df


def _avail(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in df.columns]


def _show_table_and_chart(df: pd.DataFrame, cols: list[str], prefix: str) -> None:
    avail = _avail(df, cols)
    if df.empty or len(avail) < 2:
        st.warning("Sin datos suficientes.")
        return

    sort_options = [c for c in avail if c not in ("Team", "League")]

    c1, c2 = st.columns([3, 1])
    with c1:
        sort_col = st.selectbox("Ordenar por", sort_options, index=0, key=f"sort_{prefix}")
    with c2:
        asc_default = sort_col in LOWER_IS_BETTER
        ascending = st.checkbox("↑ Asc", value=asc_default, key=f"asc_{prefix}", help="Menor primero (ERA, FIP, etc.)")

    display_cols = _avail(df, avail)
    sorted_df = df[display_cols].sort_values(sort_col, ascending=ascending).reset_index(drop=True)
    sorted_df = put_league_after_team(sorted_df)
    sorted_df.index += 1

    st.dataframe(format_display(sorted_df), use_container_width=True, hide_index=False)

    # Gráfico de barras horizontal
    chart_df = sorted_df[["Team", sort_col]].copy().sort_values(sort_col, ascending=not ascending)
    color_scale = "RdYlGn_r" if sort_col in LOWER_IS_BETTER else "RdYlGn"

    fig = px.bar(
        chart_df,
        y="Team",
        x=sort_col,
        orientation="h",
        color=sort_col,
        color_continuous_scale=color_scale,
        text=sort_col,
        title=f"{sort_col} Colectivo por Equipo — {yr}",
        height=max(480, len(chart_df) * 22),
    )
    fig.update_traces(texttemplate="%{x:.3f}", textposition="outside")
    fig.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        yaxis_title="",
        xaxis_title=sort_col,
        yaxis={"categoryorder": "total ascending" if not ascending else "total descending"},
        margin=dict(t=50, r=80, b=30, l=10),
    )
    st.plotly_chart(fig, use_container_width=True)


def _show_by_league(df: pd.DataFrame, cols: list[str], prefix: str) -> None:
    all_tab, al_tab, nl_tab = st.tabs(["🌐 Toda la MLB", "🏟️ Liga Americana (AL)", "🏟️ Liga Nacional (NL)"])
    with all_tab:
        _show_table_and_chart(df, cols, f"{prefix}_all")
    with al_tab:
        _show_table_and_chart(df[df["League"] == "AL"].copy(), cols, f"{prefix}_al")
    with nl_tab:
        _show_table_and_chart(df[df["League"] == "NL"].copy(), cols, f"{prefix}_nl")


# ── Enriquecer con liga ────────────────────────────────────────────────────
tbd = _add_league(tbd)
tpd = _add_league(tpd)
if not tfd.empty:
    tfd = _add_league(tfd)

tbat_cols   = TBAT_COLS   + ["League"]
tpit_cols   = TPIT_COLS   + ["League"]
tfield_cols = TFIELD_COLS + ["League"]

# ── Tabs de Estadísticas Colectivas ────────────────────────────────────────
st.markdown("### 📊 Estadísticas Colectivas por Equipo")
bat_tab, pit_tab, field_tab = st.tabs([
    "🏏 Bateo Colectivo",
    "⚡ Pitcheo Colectivo",
    "🧤 Fildeo Colectivo",
])

with bat_tab:
    st.subheader(f"Bateo Colectivo — {yr}")
    _show_by_league(tbd, tbat_cols, "tbat")

with pit_tab:
    st.subheader(f"Pitcheo Colectivo — {yr}")
    _show_by_league(tpd, tpit_cols, "tpit")

with field_tab:
    st.subheader(f"Fildeo Colectivo — {yr}")
    if tfd.empty:
        st.warning("No se pudieron cargar los datos de fildeo.")
    else:
        _show_by_league(tfd, tfield_cols, "tfield")

