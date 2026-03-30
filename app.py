"""
app.py
------
Streamlit app: MLB Top Players por Liga
Tabs: Bateadores | Pitchers  →  sub-tabs AL | NL
Sidebar: controles de parámetros + botón Ejecutar
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from main import run

# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="MLB Top Players",
    page_icon="⚾",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Sidebar — controles
# ---------------------------------------------------------------------------
st.sidebar.title("⚾ MLB Top Players")
st.sidebar.markdown("Datos: **Statcast / Baseball Savant**")
st.sidebar.divider()

st.sidebar.subheader("📅 Rango de fechas")
col1, col2 = st.sidebar.columns(2)
default_end_dt = date.today()
default_start_dt = default_end_dt - timedelta(days=7)
with col1:
    start_dt = st.date_input(
        "Inicio",
        value=default_start_dt,
        min_value=date(2015, 1, 1),
        max_value=date.today(),
    )
with col2:
    end_dt = st.date_input(
        "Fin",
        value=default_end_dt,
        min_value=date(2015, 1, 2),
        max_value=date.today(),
    )

st.sidebar.divider()
st.sidebar.subheader("🔧 Parámetros")

top_n = st.sidebar.slider("Top N jugadores por liga", min_value=5, max_value=30, value=10, step=5)

min_pa = st.sidebar.number_input(
    "Mínimo PA (bateadores)",
    min_value=0, max_value=500, value=50, step=10,
    help="Plate appearances mínimos. 0 = sin filtro (cuidado con ruido estadístico)"
)
min_bf = st.sidebar.number_input(
    "Mínimo BF (pitchers)",
    min_value=0, max_value=500, value=30, step=10,
    help="Batters faced mínimos. 0 = sin filtro"
)

force_refresh = st.sidebar.checkbox(
    "🔄 Forzar re-descarga",
    value=False,
    help="Ignora el caché local y vuelve a descargar de Statcast"
)

st.sidebar.divider()
ejecutar = st.sidebar.button("▶ Ejecutar", type="primary", use_container_width=True)

st.sidebar.markdown(
    """
    ---
    **Métricas clave**
    - **xwOBA**: Calidad de contacto esperada (bateadores)
    - **xERA**: ERA esperado por calidad de contacto (pitchers)
    - Fuente: Statcast pitch-by-pitch
    """,
    unsafe_allow_html=False,
)

# ---------------------------------------------------------------------------
# Header principal
# ---------------------------------------------------------------------------
st.title("⚾ MLB Top Players por Liga")
st.caption(
    f"Período seleccionado: **{start_dt}** → **{end_dt}**  |  "
    f"Top **{top_n}** por liga  |  min PA={min_pa}  |  min BF={min_bf}"
)

# ---------------------------------------------------------------------------
# Validaciones
# ---------------------------------------------------------------------------
if start_dt >= end_dt:
    st.error("⚠️ La fecha de inicio debe ser anterior a la fecha de fin.")
    st.stop()

# ---------------------------------------------------------------------------
# Helpers de display
# ---------------------------------------------------------------------------

BATTER_COL_CONFIG = {
    "player_name": st.column_config.TextColumn("Jugador", width="medium"),
    "PA"         : st.column_config.NumberColumn("PA",    format="%d"),
    "HR"         : st.column_config.NumberColumn("HR",    format="%d"),
    "AVG"        : st.column_config.NumberColumn("AVG",   format="%.3f"),
    "OBP"        : st.column_config.NumberColumn("OBP",   format="%.3f"),
    "SLG"        : st.column_config.NumberColumn("SLG",   format="%.3f"),
    "OPS"        : st.column_config.NumberColumn("OPS",   format="%.3f"),
    "K_pct"      : st.column_config.NumberColumn("K%",    format="%.1%%"),
    "BB_pct"     : st.column_config.NumberColumn("BB%",   format="%.1%%"),
    "xwOBA"      : st.column_config.NumberColumn("xwOBA", format="%.3f"),
    "xBA"        : st.column_config.NumberColumn("xBA",   format="%.3f"),
    "xSLG"       : st.column_config.NumberColumn("xSLG",  format="%.3f"),
}

PITCHER_COL_CONFIG = {
    "player_name"   : st.column_config.TextColumn("Jugador",      width="medium"),
    "BF"            : st.column_config.NumberColumn("BF",          format="%d"),
    "IP"            : st.column_config.NumberColumn("IP",          format="%.1f"),
    "HR_allowed"    : st.column_config.NumberColumn("HR",          format="%d"),
    "BB"            : st.column_config.NumberColumn("BB",          format="%d"),
    "K"             : st.column_config.NumberColumn("K",           format="%d"),
    "K9"            : st.column_config.NumberColumn("K/9",         format="%.2f"),
    "BB9"           : st.column_config.NumberColumn("BB/9",        format="%.2f"),
    "WHIP"          : st.column_config.NumberColumn("WHIP",        format="%.3f"),
    "ERA_proxy"     : st.column_config.NumberColumn("ERA~",        format="%.2f"),
    "K_pct"         : st.column_config.NumberColumn("K%",          format="%.1%%"),
    "BB_pct"        : st.column_config.NumberColumn("BB%",         format="%.1%%"),
    "xwOBA_against" : st.column_config.NumberColumn("xwOBA contra",format="%.3f"),
    "xERA"          : st.column_config.NumberColumn("xERA",        format="%.2f"),
    "avg_velo"      : st.column_config.NumberColumn("Velo (mph)",  format="%.1f"),
    "avg_spin"      : st.column_config.NumberColumn("Spin (rpm)",  format="%.0f"),
}


def show_league_table(df: pd.DataFrame, col_config: dict, key: str) -> None:
    """Muestra tabla con formato y highlight de la métrica principal."""
    if df.empty:
        st.warning("Sin datos suficientes para este filtro.")
        return
    st.dataframe(
        df,
        use_container_width=True,
        column_config=col_config,
        hide_index=False,
        key=key,
    )


def show_batter_tabs(rankings: dict[str, pd.DataFrame], prefix: str) -> None:
    al_tab, nl_tab = st.tabs(["🏟️ American League", "🏟️ National League"])
    with al_tab:
        show_league_table(rankings.get("AL", pd.DataFrame()), BATTER_COL_CONFIG, f"{prefix}_al")
    with nl_tab:
        show_league_table(rankings.get("NL", pd.DataFrame()), BATTER_COL_CONFIG, f"{prefix}_nl")


def show_pitcher_tabs(rankings: dict[str, pd.DataFrame], prefix: str) -> None:
    al_tab, nl_tab = st.tabs(["🏟️ American League", "🏟️ National League"])
    with al_tab:
        show_league_table(rankings.get("AL", pd.DataFrame()), PITCHER_COL_CONFIG, f"{prefix}_al")
    with nl_tab:
        show_league_table(rankings.get("NL", pd.DataFrame()), PITCHER_COL_CONFIG, f"{prefix}_nl")


# ---------------------------------------------------------------------------
# Estado de sesión — conserva resultados entre reruns sin re-ejecutar
# ---------------------------------------------------------------------------
if "batter_rankings" not in st.session_state:
    st.session_state.batter_rankings  = None
    st.session_state.pitcher_rankings = None
    st.session_state.last_params      = None

# ---------------------------------------------------------------------------
# Ejecución del pipeline
# ---------------------------------------------------------------------------
if ejecutar:
    params = (str(start_dt), str(end_dt), top_n, min_pa, min_bf, force_refresh)

    with st.spinner("Descargando datos de Statcast... (puede tardar en la primera ejecución)"):
        try:
            batter_r, pitcher_r = run(
                start_dt      = str(start_dt),
                end_dt        = str(end_dt),
                top           = top_n,
                min_pa        = min_pa,
                min_bf        = min_bf,
                force_refresh = force_refresh,
            )
            st.session_state.batter_rankings  = batter_r
            st.session_state.pitcher_rankings = pitcher_r
            st.session_state.last_params      = params
            st.success("✅ Datos cargados correctamente.")
        except Exception as e:
            st.error(f"❌ Error al procesar datos: {e}")
            st.stop()

# ---------------------------------------------------------------------------
# Display de resultados
# ---------------------------------------------------------------------------
if st.session_state.batter_rankings is None:
    st.info("👈 Configura los parámetros en el sidebar y presiona **Ejecutar**.")
    st.stop()

bat_tab, pit_tab = st.tabs(["🏏 Bateadores", "⚡ Pitchers"])

with bat_tab:
    st.subheader(f"Top {top_n} Bateadores — ordenados por xwOBA")
    st.caption("xwOBA: calidad de contacto esperada según exit velocity y launch angle. Mayor = mejor.")
    show_batter_tabs(st.session_state.batter_rankings, prefix="bat")

with pit_tab:
    st.subheader(f"Top {top_n} Pitchers — ordenados por xERA")
    st.caption("xERA: ERA esperado basado en calidad de contacto permitido. Menor = mejor.")
    show_pitcher_tabs(st.session_state.pitcher_rankings, prefix="pit")
