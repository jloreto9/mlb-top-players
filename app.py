"""
app.py — PÁGINA PRINCIPAL
Stats Colectivas por Equipo (FanGraphs via pybaseball)

Tabs: Bateo Colectivo | Pitcheo Colectivo
  Sub-tabs por cada tab: Todos | AL | NL
  Selector de métrica + gráfico de barras interactivo
"""

import streamlit as st
import pandas as pd
import plotly.express as px

import fetcher
from constants import TEAM_LEAGUE, TBAT_COLS, TPIT_COLS, LOWER_IS_BETTER

# ── Configuración ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="⚾ MLB Stats",
    page_icon="⚾",
    layout="wide",
)

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚾ MLB Fangraphs Lite")
    st.caption("Fuente: FanGraphs via pybaseball")
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
for key in ("team_bat_df", "team_pit_df", "loaded_year"):
    if key not in st.session_state:
        st.session_state[key] = None

# ── Carga ──────────────────────────────────────────────────────────────────
if run_btn:
    with st.spinner(f"Descargando stats de equipo {year}..."):
        try:
            st.session_state.team_bat_df = fetcher.team_bat(year, force=force)
            st.session_state.team_pit_df = fetcher.team_pit(year, force=force)
            st.session_state.loaded_year = year
        except Exception as e:
            st.error(f"❌ {e}")
            st.stop()

# ── Header ─────────────────────────────────────────────────────────────────
st.title("📊 Stats Colectivas por Equipo")

if st.session_state.team_bat_df is None:
    st.info("👈 Selecciona la temporada y presiona **Cargar datos**.")
    st.stop()

yr  = st.session_state.loaded_year
tbd = st.session_state.team_bat_df.copy()
tpd = st.session_state.team_pit_df.copy()

st.caption(f"Temporada **{yr}** · Fuente: FanGraphs")


# ── Helpers ────────────────────────────────────────────────────────────────

def _add_league(df: pd.DataFrame, col: str = "Team") -> pd.DataFrame:
    """Agrega columna League (AL / NL / UNK) usando el mapeo de equipo."""
    df = df.copy()
    if col in df.columns:
        df["League"] = df[col].str.upper().map(TEAM_LEAGUE).fillna("UNK")
    return df


def _avail(df: pd.DataFrame, cols: list[str]) -> list[str]:
    """Filtra a las columnas que existen en el DataFrame."""
    return [c for c in cols if c in df.columns]


def _show_table_and_chart(
    df: pd.DataFrame,
    cols: list[str],
    prefix: str,
) -> None:
    """Muestra selector de métrica, tabla ordenada y gráfico de barras."""
    avail = _avail(df, cols)
    if df.empty or len(avail) < 2:
        st.warning("Sin datos suficientes.")
        return

    sort_options = [c for c in avail if c not in ("Team", "League")]
    default_sort = sort_options[0] if sort_options else avail[0]

    c1, c2 = st.columns([3, 1])
    with c1:
        sort_col = st.selectbox(
            "Ordenar por",
            sort_options,
            index=0,
            key=f"sort_{prefix}",
        )
    with c2:
        asc_default = sort_col in LOWER_IS_BETTER
        ascending = st.checkbox(
            "↑ Asc",
            value=asc_default,
            key=f"asc_{prefix}",
            help="Menor primero (útil para ERA, FIP, etc.)",
        )

    display_cols = _avail(df, avail)
    sorted_df = (
        df[display_cols]
        .sort_values(sort_col, ascending=ascending)
        .reset_index(drop=True)
    )
    sorted_df.index += 1

    st.dataframe(sorted_df, use_container_width=True, hide_index=False)

    # ── Gráfico de barras ──────────────────────────────────────────────────
    chart_df = sorted_df.reset_index(names="Rank")
    fig = px.bar(
        chart_df,
        x="Team",
        y=sort_col,
        color="Team",
        text=sort_col,
        title=f"{sort_col} por equipo — {yr}",
        height=380,
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        showlegend=False,
        xaxis_title="",
        yaxis_title=sort_col,
        margin=dict(t=50, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


def _show_by_league(
    df: pd.DataFrame,
    cols: list[str],
    prefix: str,
) -> None:
    """Presenta sub-tabs Todos | AL | NL con tabla y chart."""
    all_tab, al_tab, nl_tab = st.tabs(["🌐 Todos", "🏟️ AL", "🏟️ NL"])

    with all_tab:
        _show_table_and_chart(df, cols, f"{prefix}_all")
    with al_tab:
        _show_table_and_chart(df[df["League"] == "AL"].copy(), cols, f"{prefix}_al")
    with nl_tab:
        _show_table_and_chart(df[df["League"] == "NL"].copy(), cols, f"{prefix}_nl")


# ── Enriquecer con liga ────────────────────────────────────────────────────
tbd = _add_league(tbd)
tpd = _add_league(tpd)

# Agregar League al final de las listas de cols para que aparezca en tabla
tbat_cols = TBAT_COLS + ["League"]
tpit_cols = TPIT_COLS + ["League"]

# ── Tabs principales ───────────────────────────────────────────────────────
bat_tab, pit_tab = st.tabs(["🏏 Bateo Colectivo", "⚡ Pitcheo Colectivo"])

with bat_tab:
    st.subheader(f"Bateo Colectivo por Equipo — {yr}")
    _show_by_league(tbd, tbat_cols, "tbat")

with pit_tab:
    st.subheader(f"Pitcheo Colectivo por Equipo — {yr}")
    _show_by_league(tpd, tpit_cols, "tpit")
