"""
pages/1_Leaderboard.py
Leaderboard individual de bateadores y pitchers con soporte completo para Fantasy Baseball y Statcast.

Vistas:
- 📊 Estándar (Clásicas & Sabermétricas)
- 🎯 Fantasy 5x5 (Z-Scores & Puntos)
- ⚡ Statcast (xStats & Regresión)

Filtros:
- Liga: Todos | AL | NL
- Posición de Fantasy (C, 1B, 2B, 3B, SS, OF, DH, SP, RP)
- Equipo (Multiselect)
- Filtro de volumen (Min PA / Min IP)
"""

import sys
from pathlib import Path
from datetime import datetime

# Asegurar que el root del proyecto este en el path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

import fetcher
import fantasy
from constants import (
    TEAM_LEAGUE, BAT_COLS, BAT_FANTASY_COLS, STATCAST_BAT_COLS,
    PIT_COLS, PIT_FANTASY_COLS, STATCAST_PIT_COLS, LOWER_IS_BETTER,
    FANTASY_SCORING_PRESETS, AVAILABLE_SEASONS, get_team_logo
)
from utils import format_display, put_league_after_team

# ── Config ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Leaderboard & Fantasy · MLB Stats",
    page_icon="📊",
    layout="wide",
)

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 MLB Leaderboards")
    st.caption("Analítica y Valoración Fantasy")
    st.divider()

    year = st.selectbox(
        "Temporada",
        options=AVAILABLE_SEASONS,
        index=0,
    )
    
    scoring_preset = st.selectbox(
        "Sistema de Fantasy Points",
        options=list(FANTASY_SCORING_PRESETS.keys()),
        index=0,
    )
    
    force = st.checkbox("🔄 Forzar re-descarga", value=False)
    st.divider()
    run_btn = st.button("▶ Cargar datos", type="primary", use_container_width=True)

# ── Session state ──────────────────────────────────────────────────────────
for key in ("lb_bat", "lb_pit", "lb_year", "lb_preset"):
    if key not in st.session_state:
        st.session_state[key] = None

# ── Carga ──────────────────────────────────────────────────────────────────
if run_btn or (st.session_state.lb_bat is None and st.session_state.lb_year != year):
    with st.spinner(f"Cargando leaderboard {year}..."):
        try:
            raw_bat = fetcher.batting(year, force=force)
            raw_pit = fetcher.pitching(year, force=force)
            
            # Calcular capas de Fantasy y Statcast
            st.session_state.lb_bat = fantasy.calculate_batting_fantasy(raw_bat, scoring_preset=scoring_preset)
            st.session_state.lb_pit = fantasy.calculate_pitching_fantasy(raw_pit, scoring_preset=scoring_preset)
            st.session_state.lb_year = year
            st.session_state.lb_preset = scoring_preset
        except Exception as e:
            st.error(f"❌ Error al cargar datos: {e}")
            st.stop()

# ── Header ─────────────────────────────────────────────────────────────────
st.title("📊 Leaderboard Individual & Fantasy Hub")

if st.session_state.lb_bat is None:
    st.info("👈 Selecciona la temporada y presiona **Cargar datos**.")
    st.stop()

yr = st.session_state.lb_year
bat_df = st.session_state.lb_bat.copy()
pit_df = st.session_state.lb_pit.copy()

if yr >= datetime.now().year:
    st.warning(
        f"⚠️ Temporada **{yr}** en curso. "
        "Selecciona **2025** para analizar una temporada completa consolidada."
    )
else:
    st.caption(f"Temporada **{yr}** · Scoring: **{st.session_state.lb_preset}**")


# ── Helpers ────────────────────────────────────────────────────────────────

def _avail(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in df.columns]


def _team_options(df: pd.DataFrame) -> list[str]:
    if "Team" not in df.columns:
        return []
    return sorted(df["Team"].dropna().unique().tolist())


def _pos_options(df: pd.DataFrame) -> list[str]:
    if "Pos" not in df.columns:
        return []
    return sorted(df["Pos"].dropna().unique().tolist())


def _show_leaderboard(
    df: pd.DataFrame,
    cols: list[str],
    prefix: str,
    min_col: str | None = None,
    min_label: str = "Min PA",
    min_default: int = 50,
    is_pitcher: bool = False,
) -> None:
    """Muestra filtros interactivos (equipos, posiciones, volumen) y tabla sorteable."""
    if df.empty:
        st.warning("Sin datos para este filtro.")
        return

    avail = _avail(df, cols)

    # ── Controles de filtro ────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns([2, 2, 2])

    with fc1:
        teams = _team_options(df)
        sel_teams = st.multiselect(
            "Equipo",
            options=teams,
            default=[],
            placeholder="Todos los equipos",
            key=f"teams_{prefix}",
        )

    with fc2:
        pos_list = _pos_options(df)
        sel_pos = st.multiselect(
            "Posición",
            options=pos_list,
            default=[],
            placeholder="Todas las posiciones",
            key=f"pos_{prefix}",
        )

    with fc3:
        if min_col and min_col in df.columns:
            col_max = int(pd.to_numeric(df[min_col], errors="coerce").max() or 700)
            safe_default = min(min_default, col_max)
            min_val = st.number_input(
                min_label,
                min_value=0,
                max_value=col_max,
                value=safe_default,
                step=10,
                key=f"min_{prefix}",
            )
        else:
            min_val = 0

    # ── Controles de orden ─────────────────────────────────────────────────
    sc1, sc2 = st.columns([3, 1])
    sort_options = [c for c in avail if c not in ("Name", "Team", "League", "Pos")]

    default_sort = "WAR" if "WAR" in sort_options else ("Fantasy_Pts" if "Fantasy_Pts" in sort_options else sort_options[0])

    with sc1:
        sort_col = st.selectbox(
            "Ordenar por",
            options=sort_options,
            index=sort_options.index(default_sort) if default_sort in sort_options else 0,
            key=f"sort_{prefix}",
        )
    with sc2:
        asc_default = sort_col in LOWER_IS_BETTER
        ascending = st.checkbox(
            "↑ Asc",
            value=asc_default,
            key=f"asc_{prefix}",
            help="Menor primero (ERA, WHIP, etc.)",
        )

    # ── Aplicar filtros ────────────────────────────────────────────────────
    filtered = df.copy()

    if sel_teams:
        filtered = filtered[filtered["Team"].isin(sel_teams)]

    if sel_pos:
        filtered = filtered[filtered["Pos"].isin(sel_pos)]

    if min_col and min_col in filtered.columns and min_val > 0:
        filtered = filtered[
            pd.to_numeric(filtered[min_col], errors="coerce") >= min_val
        ]

    if filtered.empty:
        st.warning("Sin jugadores con los filtros seleccionados.")
        return

    # ── Tabla ──────────────────────────────────────────────────────────────
    display_cols = _avail(filtered, avail)
    sorted_df = (
        filtered[display_cols]
        .sort_values(sort_col, ascending=ascending)
        .reset_index(drop=True)
    )
    sorted_df = put_league_after_team(sorted_df)
    
    # Inyectar logo del equipo
    if "Team" in sorted_df.columns:
        sorted_df.insert(0, "Logo", sorted_df["Team"].apply(get_team_logo))
    
    sorted_df.index += 1

    table_config = {
        "Logo": st.column_config.ImageColumn("Logo", width="small"),
    }

    st.dataframe(
        format_display(sorted_df),
        column_config=table_config,
        use_container_width=True,
        hide_index=False,
        height=620,
    )
    st.caption(f"Mostrando **{len(sorted_df)}** jugadores · Ordenado por **{sort_col}** ({'Ascendente' if ascending else 'Descendente'})")


def _render_player_section(
    df: pd.DataFrame,
    standard_cols: list[str],
    fantasy_cols: list[str],
    statcast_cols: list[str],
    prefix: str,
    min_col: str,
    min_label: str,
    min_default: int,
    is_pitcher: bool = False,
) -> None:
    """Renderiza los sub-tabs de Liga y el selector de Vistas."""
    v1, v2 = st.columns([2, 4])
    with v1:
        view_mode = st.radio(
            "Seleccionar Vista",
            options=["📊 Estándar / Sabermetría", "🎯 Fantasy (Z-Scores & Puntos)", "⚡ Statcast & Calidad de Contacto"],
            horizontal=True,
            key=f"view_mode_{prefix}",
        )

    if view_mode == "🎯 Fantasy (Z-Scores & Puntos)":
        active_cols = fantasy_cols
    elif view_mode == "⚡ Statcast & Calidad de Contacto":
        active_cols = statcast_cols
    else:
        active_cols = standard_cols

    cols_with_league = active_cols + (["League"] if "League" not in active_cols else [])

    all_t, al_t, nl_t = st.tabs(["🌐 Toda la MLB", "🏟️ Liga Americana (AL)", "🏟️ Liga Nacional (NL)"])

    with all_t:
        _show_leaderboard(df, cols_with_league, f"{prefix}_all", min_col, min_label, min_default, is_pitcher)
    with al_t:
        _show_leaderboard(df[df["League"] == "AL"].copy(), cols_with_league, f"{prefix}_al", min_col, min_label, min_default, is_pitcher)
    with nl_t:
        _show_leaderboard(df[df["League"] == "NL"].copy(), cols_with_league, f"{prefix}_nl", min_col, min_label, min_default, is_pitcher)


# ── Tabs principales ───────────────────────────────────────────────────────
bat_tab, pit_tab = st.tabs(["🏏 Bateadores", "⚡ Pitchers"])

with bat_tab:
    st.subheader(f"Bateadores — {yr}")
    _render_player_section(
        bat_df,
        standard_cols=BAT_COLS,
        fantasy_cols=BAT_FANTASY_COLS,
        statcast_cols=STATCAST_BAT_COLS,
        prefix="bat",
        min_col="PA",
        min_label="Min PA",
        min_default=50,
        is_pitcher=False,
    )

with pit_tab:
    st.subheader(f"Pitchers — {yr}")
    _render_player_section(
        pit_df,
        standard_cols=PIT_COLS,
        fantasy_cols=PIT_FANTASY_COLS,
        statcast_cols=STATCAST_PIT_COLS,
        prefix="pit",
        min_col="IP",
        min_label="Min IP",
        min_default=20,
        is_pitcher=True,
    )

