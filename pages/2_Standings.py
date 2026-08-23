"""
pages/2_Standings.py
Standings oficiales de MLB por División y Carrera por el Comodín (Wild Card) vía MLB Stats API.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
import streamlit as st
import pandas as pd

import fetcher
from constants import AVAILABLE_SEASONS

st.set_page_config(
    page_title="Standings & Playoffs · MLB Stats",
    page_icon="🏆",
    layout="wide",
)

DIVISIONS_AL = ["AL East", "AL Central", "AL West"]
DIVISIONS_NL = ["NL East", "NL Central", "NL West"]

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏆 Standings")
    st.caption("Fuente: MLB Stats API Oficial")
    st.divider()

    year = st.selectbox(
        "Temporada",
        options=AVAILABLE_SEASONS,
        index=0,
    )
    force = st.checkbox("🔄 Forzar re-descarga", value=False)
    st.divider()
    run_btn = st.button("▶ Cargar standings", type="primary", use_container_width=True)

# ── Session state ────────────────────────────────────────────────────────────
if "standings_dict" not in st.session_state:
    st.session_state.standings_dict = None
    st.session_state.standings_year = None

# ── Carga ────────────────────────────────────────────────────────────────────
if run_btn or st.session_state.standings_dict is None or st.session_state.standings_year != year:
    with st.spinner(f"Cargando standings oficiales {year}..."):
        try:
            st.session_state.standings_dict = fetcher.get_standings(year, force=force)
            st.session_state.standings_year = year
        except Exception as e:
            st.error(f"❌ Error al cargar standings: {e}")
            st.stop()

# ── Header ───────────────────────────────────────────────────────────────────
st.title("🏆 MLB Standings & Postseason Picture")

tables = st.session_state.standings_dict
yr = st.session_state.standings_year

if tables is None or not tables:
    st.info("👈 Selecciona la temporada y presiona **Cargar standings**.")
    st.stop()

if yr >= _NOW_YEAR:
    st.caption(f"Temporada **{yr}** — Posiciones en vivo · Fuente: MLB Stats API")
else:
    st.caption(f"Temporada **{yr}** (finalizada) · Fuente: MLB Stats API")


def _format_table(df: pd.DataFrame, is_wc: bool = False) -> pd.DataFrame:
    """Formatea la tabla de standings para display."""
    if df.empty:
        return df
    out = df.copy()
    if is_wc:
        cols = ["Team", "W", "L", "PCT", "WC_GB", "RS", "RA", "Diff", "Streak", "L10"]
    else:
        cols = ["Team", "W", "L", "PCT", "GB", "RS", "RA", "Diff", "Streak", "L10"]
    avail = [c for c in cols if c in out.columns]
    out = out[avail].reset_index(drop=True)
    out.index += 1
    return out


# ── Tabs de Visualización ──────────────────────────────────────────────────
tab_div, tab_wc = st.tabs(["🏛️ Posiciones por División", "🎫 Carrera por el Comodín (Wild Card)"])

with tab_div:
    st.subheader(f"🏟️ American League — {yr}")
    al_cols = st.columns(3)
    for i, div_name in enumerate(DIVISIONS_AL):
        with al_cols[i]:
            st.markdown(f"**{div_name}**")
            df_div = tables.get(div_name, pd.DataFrame())
            if not df_div.empty:
                st.dataframe(_format_table(df_div), use_container_width=True, hide_index=False)
            else:
                st.info("Sin datos.")

    st.divider()

    st.subheader(f"🏟️ National League — {yr}")
    nl_cols = st.columns(3)
    for i, div_name in enumerate(DIVISIONS_NL):
        with nl_cols[i]:
            st.markdown(f"**{div_name}**")
            df_div = tables.get(div_name, pd.DataFrame())
            if not df_div.empty:
                st.dataframe(_format_table(df_div), use_container_width=True, hide_index=False)
            else:
                st.info("Sin datos.")

with tab_wc:
    st.subheader(f"🎫 Cuadro de Comodín (Wild Card) — {yr}")
    st.caption("Los 3 mejores clasificados fuera de los campeones divisionales avanzan a la postemporada.")

    wc_col1, wc_col2 = st.columns(2)

    with wc_col1:
        st.markdown("### 🏟️ AL Wild Card Standings")
        al_all = []
        for d in DIVISIONS_AL:
            df_d = tables.get(d, pd.DataFrame())
            if not df_d.empty:
                # El líder divisional clasifica directo
                al_all.append(df_d.iloc[1:].copy() if len(df_d) > 1 else df_d)
        if al_all:
            al_wc_df = pd.concat(al_all, ignore_index=True)
            if "PCT" in al_wc_df.columns:
                al_wc_df["pct_num"] = pd.to_numeric(al_wc_df["PCT"], errors="coerce").fillna(0)
                al_wc_df = al_wc_df.sort_values("pct_num", ascending=False).drop(columns=["pct_num"])
            st.dataframe(_format_table(al_wc_df, is_wc=True), use_container_width=True, height=500)
        else:
            st.info("Sin datos de AL.")

    with wc_col2:
        st.markdown("### 🏟️ NL Wild Card Standings")
        nl_all = []
        for d in DIVISIONS_NL:
            df_d = tables.get(d, pd.DataFrame())
            if not df_d.empty:
                nl_all.append(df_d.iloc[1:].copy() if len(df_d) > 1 else df_d)
        if nl_all:
            nl_wc_df = pd.concat(nl_all, ignore_index=True)
            if "PCT" in nl_wc_df.columns:
                nl_wc_df["pct_num"] = pd.to_numeric(nl_wc_df["PCT"], errors="coerce").fillna(0)
                nl_wc_df = nl_wc_df.sort_values("pct_num", ascending=False).drop(columns=["pct_num"])
            st.dataframe(_format_table(nl_wc_df, is_wc=True), use_container_width=True, height=500)
        else:
            st.info("Sin datos de NL.")
