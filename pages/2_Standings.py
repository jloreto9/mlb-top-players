"""
pages/2_Standings.py
Standings MLB por división — Baseball Reference via pybaseball.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
import streamlit as st
import pandas as pd

import fetcher

st.set_page_config(
    page_title="Standings · MLB Stats",
    page_icon="🏆",
    layout="wide",
)

# ── Constantes ──────────────────────────────────────────────────────────────
DIVISIONS = [
    ("AL East",    "AL"),
    ("AL Central", "AL"),
    ("AL West",    "AL"),
    ("NL East",    "NL"),
    ("NL Central", "NL"),
    ("NL West",    "NL"),
]

_NOW_YEAR = datetime.now().year

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏆 Standings")
    st.caption("Fuente: Baseball Reference via pybaseball")
    st.divider()

    year = st.selectbox(
        "Temporada",
        options=list(range(_NOW_YEAR, 2009, -1)),
        index=0,       # default: año actual (standings en vivo)
    )
    force = st.checkbox("🔄 Forzar re-descarga", value=False)
    st.divider()
    run_btn = st.button("▶ Cargar standings", type="primary", use_container_width=True)

# ── Session state ────────────────────────────────────────────────────────────
if "standings_tables" not in st.session_state:
    st.session_state.standings_tables = None
    st.session_state.standings_year   = None

# ── Carga ────────────────────────────────────────────────────────────────────
if run_btn:
    with st.spinner(f"Descargando standings {year}..."):
        try:
            st.session_state.standings_tables = fetcher.get_standings(year, force=force)
            st.session_state.standings_year   = year
        except Exception as e:
            st.error(f"❌ {e}")
            st.stop()

# ── Header ───────────────────────────────────────────────────────────────────
st.title("🏆 MLB Standings")

if st.session_state.standings_tables is None:
    st.info("👈 Selecciona la temporada y presiona **Cargar standings**.")
    st.stop()

tables = st.session_state.standings_tables
yr     = st.session_state.standings_year

if yr >= _NOW_YEAR:
    st.caption(f"Temporada **{yr}** — standings en curso · Fuente: Baseball Reference")
else:
    st.caption(f"Temporada **{yr}** (final) · Fuente: Baseball Reference")


# ── Helper: limpiar tabla ────────────────────────────────────────────────────

def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia y renombra columnas de la tabla de standings de BRef."""
    df = df.copy()

    # BRef a veces incluye filas de separación con guiones
    if "Tm" in df.columns:
        df = df[~df["Tm"].str.startswith("-", na=True)]
        df = df[df["Tm"].notna() & (df["Tm"] != "Tm")]

    # Columnas númericas
    num_cols = ["W", "L", "GB", "RS", "RA", "Diff"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # PCT
    if "W-L%" in df.columns:
        df["PCT"] = pd.to_numeric(df["W-L%"], errors="coerce").apply(
            lambda v: f"{v:.3f}".lstrip("0") if pd.notna(v) and v < 1 else (f"{v:.3f}" if pd.notna(v) else "")
        )
        df = df.drop(columns=["W-L%"])

    # Renombrar Tm → Team
    if "Tm" in df.columns:
        df = df.rename(columns={"Tm": "Team"})

    # Ordenar columnas preferidas
    preferred = ["Team", "W", "L", "PCT", "GB", "RS", "RA", "Diff", "Streak", "L10"]
    cols = [c for c in preferred if c in df.columns]
    extra = [c for c in df.columns if c not in cols]
    df = df[cols + extra].reset_index(drop=True)
    df.index += 1

    return df


# ── Layout: AL arriba, NL abajo — 3 divisiones por fila ─────────────────────
st.subheader(f"🏟️ American League — {yr}")
al_cols = st.columns(3)
for i, (div_name, _) in enumerate(DIVISIONS[:3]):
    with al_cols[i]:
        st.markdown(f"**{div_name}**")
        if i < len(tables):
            try:
                st.dataframe(_clean(tables[i]), use_container_width=True, hide_index=False)
            except Exception as e:
                st.warning(f"No se pudo mostrar {div_name}: {e}")
        else:
            st.warning("Sin datos.")

st.divider()

st.subheader(f"🏟️ National League — {yr}")
nl_cols = st.columns(3)
for i, (div_name, _) in enumerate(DIVISIONS[3:]):
    with nl_cols[i]:
        st.markdown(f"**{div_name}**")
        idx = i + 3
        if idx < len(tables):
            try:
                st.dataframe(_clean(tables[idx]), use_container_width=True, hide_index=False)
            except Exception as e:
                st.warning(f"No se pudo mostrar {div_name}: {e}")
        else:
            st.warning("Sin datos.")
