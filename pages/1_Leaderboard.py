"""
pages/1_Leaderboard.py
Leaderboard individual de bateadores y pitchers (FanGraphs via pybaseball).

Tabs: Bateadores | Pitchers
  Sub-tabs: Todos | AL | NL
  Filtros: equipo (multiselect), min PA / min IP, SP/RP (pitchers)
"""

import sys
from pathlib import Path

# Asegurar que el root del proyecto este en el path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

import fetcher
from constants import TEAM_LEAGUE, BAT_COLS, PIT_COLS, LOWER_IS_BETTER

# ── Config ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Leaderboard · MLB Stats",
    page_icon="📊",
    layout="wide",
)

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 Leaderboard")
    st.caption("Fuente: FanGraphs via pybaseball")
    st.divider()

    year = st.selectbox(
        "Temporada",
        options=list(range(2026, 2009, -1)),
        index=1,
    )
    force = st.checkbox("🔄 Forzar re-descarga", value=False)
    st.divider()
    run_btn = st.button("▶ Cargar datos", type="primary", use_container_width=True)

# ── Session state ──────────────────────────────────────────────────────────
for key in ("lb_bat", "lb_pit", "lb_year"):
    if key not in st.session_state:
        st.session_state[key] = None

# ── Carga ──────────────────────────────────────────────────────────────────
if run_btn:
    with st.spinner(f"Descargando leaderboard {year}..."):
        try:
            st.session_state.lb_bat  = fetcher.batting(year, force=force)
            st.session_state.lb_pit  = fetcher.pitching(year, force=force)
            st.session_state.lb_year = year
        except Exception as e:
            st.error(f"❌ {e}")
            st.stop()

# ── Header ─────────────────────────────────────────────────────────────────
st.title("📊 Leaderboard Individual")

if st.session_state.lb_bat is None:
    st.info("👈 Selecciona la temporada y presiona **Cargar datos**.")
    st.stop()

yr      = st.session_state.lb_year
bat_raw = st.session_state.lb_bat.copy()
pit_raw = st.session_state.lb_pit.copy()

st.caption(f"Temporada **{yr}** · Fuente: FanGraphs")


# ── Helpers ────────────────────────────────────────────────────────────────

def _add_league(df: pd.DataFrame, col: str = "Team") -> pd.DataFrame:
    df = df.copy()
    if col in df.columns:
        df["League"] = df[col].str.upper().map(TEAM_LEAGUE).fillna("UNK")
    return df


def _avail(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in df.columns]


def _team_options(df: pd.DataFrame) -> list[str]:
    if "Team" not in df.columns:
        return []
    return sorted(df["Team"].dropna().unique().tolist())


def _show_leaderboard(
    df: pd.DataFrame,
    cols: list[str],
    prefix: str,
    min_col: str | None = None,
    min_label: str = "Min PA",
    min_default: int = 50,
    extra_filters: bool = False,
) -> None:
    """
    Muestra filtros + tabla sorteable para un subconjunto del leaderboard.

    Parametros
    ----------
    df           : DataFrame ya filtrado por liga (o sin filtro si es 'Todos')
    cols         : columnas deseadas (se intersecta con las disponibles)
    prefix       : clave unica para los widgets de Streamlit
    min_col      : columna para el filtro de volumen (PA o IP)
    min_label    : etiqueta del filtro de volumen
    min_default  : valor por defecto del filtro
    extra_filters: si True muestra filtro SP/RP (solo para pitchers)
    """
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
        if min_col and min_col in df.columns:
            min_val = st.number_input(
                min_label,
                min_value=0,
                max_value=int(df[min_col].max()) if not df[min_col].empty else 700,
                value=min_default,
                step=10,
                key=f"min_{prefix}",
            )
        else:
            min_val = 0

    with fc3:
        if extra_filters and "GS" in df.columns and "G" in df.columns:
            role = st.radio(
                "Rol",
                options=["Todos", "SP", "RP"],
                horizontal=True,
                key=f"role_{prefix}",
            )
        else:
            role = "Todos"

    # ── Controles de orden ─────────────────────────────────────────────────
    sc1, sc2 = st.columns([3, 1])
    sort_options = [c for c in avail if c not in ("Name", "Team", "League")]

    with sc1:
        sort_col = st.selectbox(
            "Ordenar por",
            options=sort_options,
            key=f"sort_{prefix}",
        )
    with sc2:
        asc_default = sort_col in LOWER_IS_BETTER
        ascending = st.checkbox(
            "↑ Asc",
            value=asc_default,
            key=f"asc_{prefix}",
            help="Menor primero",
        )

    # ── Aplicar filtros ────────────────────────────────────────────────────
    filtered = df.copy()

    if sel_teams:
        filtered = filtered[filtered["Team"].isin(sel_teams)]

    if min_col and min_col in filtered.columns and min_val > 0:
        filtered = filtered[
            pd.to_numeric(filtered[min_col], errors="coerce") >= min_val
        ]

    if role == "SP" and "GS" in filtered.columns and "G" in filtered.columns:
        filtered = filtered[
            pd.to_numeric(filtered["GS"], errors="coerce")
            >= pd.to_numeric(filtered["G"], errors="coerce") * 0.5
        ]
    elif role == "RP" and "GS" in filtered.columns and "G" in filtered.columns:
        filtered = filtered[
            pd.to_numeric(filtered["GS"], errors="coerce")
            < pd.to_numeric(filtered["G"], errors="coerce") * 0.5
        ]

    if filtered.empty:
        st.warning("Sin jugadores con estos filtros.")
        return

    # ── Tabla ──────────────────────────────────────────────────────────────
    display_cols = _avail(filtered, avail)
    sorted_df = (
        filtered[display_cols]
        .sort_values(sort_col, ascending=ascending)
        .reset_index(drop=True)
    )
    sorted_df.index += 1

    st.dataframe(
        sorted_df,
        use_container_width=True,
        hide_index=False,
        height=600,
    )
    st.caption(f"{len(sorted_df)} jugadores")


def _show_by_league(
    df: pd.DataFrame,
    cols: list[str],
    prefix: str,
    min_col: str | None = None,
    min_label: str = "Min PA",
    min_default: int = 50,
    extra_filters: bool = False,
) -> None:
    """Sub-tabs Todos | AL | NL."""
    df = _add_league(df)
    cols_with_league = cols + (["League"] if "League" not in cols else [])

    all_t, al_t, nl_t = st.tabs(["🌐 Todos", "🏟️ AL", "🏟️ NL"])

    with all_t:
        _show_leaderboard(df, cols_with_league, f"{prefix}_all",
                          min_col, min_label, min_default, extra_filters)
    with al_t:
        _show_leaderboard(df[df["League"] == "AL"].copy(), cols_with_league,
                          f"{prefix}_al", min_col, min_label, min_default, extra_filters)
    with nl_t:
        _show_leaderboard(df[df["League"] == "NL"].copy(), cols_with_league,
                          f"{prefix}_nl", min_col, min_label, min_default, extra_filters)


# ── Tabs principales ───────────────────────────────────────────────────────
bat_tab, pit_tab = st.tabs(["🏏 Bateadores", "⚡ Pitchers"])

with bat_tab:
    st.subheader(f"Bateadores — {yr}")
    _show_by_league(
        bat_raw,
        BAT_COLS,
        prefix="bat",
        min_col="PA",
        min_label="Min PA",
        min_default=50,
        extra_filters=False,
    )

with pit_tab:
    st.subheader(f"Pitchers — {yr}")
    _show_by_league(
        pit_raw,
        PIT_COLS,
        prefix="pit",
        min_col="IP",
        min_label="Min IP",
        min_default=20,
        extra_filters=True,
    )
