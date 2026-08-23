"""
pages/2_Standings.py
Standings oficiales de MLB por División, Carrera por el Comodín (Wild Card) y Cuadro de Postemporada (Postseason Picture) con Números Mágicos y Logos vía MLB Stats API.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
import streamlit as st
import pandas as pd

import fetcher
from constants import AVAILABLE_SEASONS
from utils import clean_ascii_text, get_team_logo

_NOW_YEAR = datetime.now().year

st.set_page_config(
    page_title="Standings & Playoffs · MLB Stats",
    page_icon="🏆",
    layout="wide",
)

DIVISIONS_AL = ["AL East", "AL Central", "AL West"]
DIVISIONS_NL = ["NL East", "NL Central", "NL West"]

# Configuración estándar para renderizar logos en tablas
LOGO_CONFIG = {
    "Logo": st.column_config.ImageColumn("Logo", width="small"),
}

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏆 Standings & Postseason")
    st.caption("Fuente: MLB Stats API Oficial")
    st.divider()

    year = st.selectbox(
        "Temporada",
        options=AVAILABLE_SEASONS,
        index=0,
    )
    force = st.checkbox("🔄 Forzar re-descarga", value=False)
    st.divider()
    run_btn = st.button("▶ Cargar posiciones", type="primary", use_container_width=True)

# ── Session state ────────────────────────────────────────────────────────────
if "standings_dict" not in st.session_state:
    st.session_state.standings_dict = None
    st.session_state.standings_year = None

# ── Carga ────────────────────────────────────────────────────────────────────
if run_btn or st.session_state.standings_dict is None or st.session_state.standings_year != year:
    with st.spinner(f"Cargando standings y cuadro de playoffs {year}..."):
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
    st.info("👈 Selecciona la temporada y presiona **Cargar posiciones**.")
    st.stop()

postseason_data = fetcher.get_postseason_picture(tables)

status_badge = "🟢 En Vivo (Temporada en Curso)" if yr >= _NOW_YEAR else "⚪ Temporada Finalizada"
st.caption(f"Temporada **{yr}** · {status_badge} · Fuente: MLB Stats API Oficial")
st.markdown(
    """
    <div style="background-color: #1e293b; padding: 10px 15px; border-radius: 8px; font-size: 0.85rem; color: #cbd5e1; margin-bottom: 15px;">
        💡 <b>Glosario:</b> 
        <b>MN (Número Mágico)</b>: Combinación de victorias del líder y derrotas del 2do lugar para asegurar la división. | 
        <b>E#</b>: Número de eliminación para el equipo perseguidor. | 
        <b>(y)</b>: Campeón divisional asegurado | 
        <b>(x)</b>: Playoff asegurado | 
        <b>(e)</b>: Matemáticamente eliminado.
    </div>
    """,
    unsafe_allow_html=True,
)


def _format_table(df: pd.DataFrame, is_wc: bool = False) -> pd.DataFrame:
    """Formatea la tabla de standings para display e incluye la columna de logo."""
    if df.empty:
        return df
    out = df.copy()
    
    # Asegurar columna de Logo
    if "Logo" not in out.columns and "Team" in out.columns:
        out["Logo"] = out["Team"].apply(get_team_logo)

    # Rellenar columnas faltantes para evitar KeyErrors
    for default_col in ["Elim_Number", "Magic_Number", "WC_GB", "GB", "Streak", "L10"]:
        if default_col not in out.columns:
            out[default_col] = "-"

    # Decorar nombre de equipo con Clinch si existe
    if "Clinch" in out.columns and "Team" in out.columns:
        out["Team"] = out.apply(
            lambda r: f"{r['Team']} ({r['Clinch']})" if pd.notna(r.get("Clinch")) and str(r.get("Clinch")).strip() else r["Team"],
            axis=1
        )

    if is_wc:
        cols = ["Logo", "Team", "W", "L", "PCT", "WC_GB", "Elim_Number", "RS", "RA", "Diff", "Streak", "L10"]
    else:
        cols = ["Logo", "Team", "W", "L", "PCT", "GB", "Magic_Number", "Elim_Number", "RS", "RA", "Diff", "Streak", "L10"]
    
    avail = [c for c in cols if c in out.columns]
    out = out[avail].reset_index(drop=True)
    
    # Renombrar columnas para visualización clara
    rename_cols = {
        "Magic_Number": "Magic # (MN)",
        "Elim_Number": "E#",
        "WC_GB": "WC GB",
    }
    out = out.rename(columns=rename_cols)
    out.index += 1
    return out


# ── Tabs de Visualización ──────────────────────────────────────────────────
tab_postseason, tab_div, tab_wc = st.tabs([
    "🌟 Cuadro de Playoffs & Cruces",
    "🏛️ Posiciones por División & Números Mágicos",
    "🎫 Carrera por el Comodín (Wild Card)"
])

# ── TAB 1: POSTSEASON PICTURE ──────────────────────────────────────────────
with tab_postseason:
    st.subheader(f"🌟 Cuadro Oficial de Postemporada MLB — {yr}")
    st.caption("Estructura de 12 clasificados: 6 por cada Liga (3 Campeones de División + 3 Comodines).")

    for lg_code, lg_title in [("AL", "American League"), ("NL", "National League")]:
        lg_data = postseason_data.get(lg_code, {})
        df_seeds = lg_data.get("seeds", pd.DataFrame())
        df_hunt = lg_data.get("hunt", pd.DataFrame())
        bracket = lg_data.get("bracket", {})

        st.markdown(f"### 🏟️ {lg_title}")

        if not df_seeds.empty and bracket:
            # 1. Byes a Serie Divisional (ALDS / NLDS)
            st.markdown("#### 🏆 Byes a Serie Divisional (Seeds 1 y 2)")
            b_col1, b_col2 = st.columns(2)
            
            with b_col1:
                b1 = bracket.get("bye_1", {})
                b1_logo = b1.get("logo", get_team_logo(b1.get("team")))
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; background-color:#0f172a; padding:12px; border-radius:10px; border-left: 5px solid #22c55e; margin-bottom:10px;">
                        <img src="{b1_logo}" width="48" height="48" style="margin-right:15px; object-fit:contain;"/>
                        <div>
                            <div style="font-weight:700; font-size:1.1rem; color:#f8fafc;">🥇 {b1.get('seed')}: {b1.get('team')}</div>
                            <div style="font-size:0.85rem; color:#94a3b8;">Récord: <b>{b1.get('record')}</b> · <i>Avanza directo a Serie Divisional (Localía)</i></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with b_col2:
                b2 = bracket.get("bye_2", {})
                b2_logo = b2.get("logo", get_team_logo(b2.get("team")))
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; background-color:#0f172a; padding:12px; border-radius:10px; border-left: 5px solid #3b82f6; margin-bottom:10px;">
                        <img src="{b2_logo}" width="48" height="48" style="margin-right:15px; object-fit:contain;"/>
                        <div>
                            <div style="font-weight:700; font-size:1.1rem; color:#f8fafc;">🥈 {b2.get('seed')}: {b2.get('team')}</div>
                            <div style="font-size:0.85rem; color:#94a3b8;">Récord: <b>{b2.get('record')}</b> · <i>Avanza directo a Serie Divisional</i></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # 2. Cruces de Serie de Comodines (Wild Card Series)
            st.markdown("#### ⚔️ Enfrentamientos de Wild Card Series (Al mejor de 3 partidos)")
            wc_col1, wc_col2 = st.columns(2)
            
            with wc_col1:
                wc1 = bracket.get("wc_matchup_1", {})
                h1 = wc1.get("home", {})
                a1 = wc1.get("away", {})
                h1_logo = h1.get("logo", get_team_logo(h1.get("team")))
                a1_logo = a1.get("logo", get_team_logo(a1.get("team")))
                st.markdown(
                    f"""
                    <div style="background-color:#0f172a; padding:14px; border-radius:10px; border-left: 5px solid #eab308; margin-bottom:12px;">
                        <div style="font-weight:700; color:#fbbf24; font-size:0.95rem; margin-bottom:8px;">Llave 1: {h1.get('seed')} vs {a1.get('seed')}</div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <div style="display:flex; align-items:center;">
                                <img src="{h1_logo}" width="32" height="32" style="margin-right:10px; object-fit:contain;"/>
                                <span style="font-weight:600; color:#f8fafc;">🏠 Local: {h1.get('team')} ({h1.get('record')})</span>
                            </div>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                            <div style="display:flex; align-items:center;">
                                <img src="{a1_logo}" width="32" height="32" style="margin-right:10px; object-fit:contain;"/>
                                <span style="font-weight:600; color:#cbd5e1;">✈️ Visita: {a1.get('team')} ({a1.get('record')})</span>
                            </div>
                        </div>
                        <div style="font-size:0.8rem; color:#94a3b8; border-top:1px solid #334155; padding-top:6px;">
                            ➡️ Ganador enfrenta a: <b style="color:#e2e8f0;">{wc1.get('winner_faces')}</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with wc_col2:
                wc2 = bracket.get("wc_matchup_2", {})
                h2 = wc2.get("home", {})
                a2 = wc2.get("away", {})
                h2_logo = h2.get("logo", get_team_logo(h2.get("team")))
                a2_logo = a2.get("logo", get_team_logo(a2.get("team")))
                st.markdown(
                    f"""
                    <div style="background-color:#0f172a; padding:14px; border-radius:10px; border-left: 5px solid #eab308; margin-bottom:12px;">
                        <div style="font-weight:700; color:#fbbf24; font-size:0.95rem; margin-bottom:8px;">Llave 2: {h2.get('seed')} vs {a2.get('seed')}</div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <div style="display:flex; align-items:center;">
                                <img src="{h2_logo}" width="32" height="32" style="margin-right:10px; object-fit:contain;"/>
                                <span style="font-weight:600; color:#f8fafc;">🏠 Local: {h2.get('team')} ({h2.get('record')})</span>
                            </div>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                            <div style="display:flex; align-items:center;">
                                <img src="{a2_logo}" width="32" height="32" style="margin-right:10px; object-fit:contain;"/>
                                <span style="font-weight:600; color:#cbd5e1;">✈️ Visita: {a2.get('team')} ({a2.get('record')})</span>
                            </div>
                        </div>
                        <div style="font-size:0.8rem; color:#94a3b8; border-top:1px solid #334155; padding-top:6px;">
                            ➡️ Ganador enfrenta a: <b style="color:#e2e8f0;">{wc2.get('winner_faces')}</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # 3. Tabla resumen de clasificados y sembrados
            st.markdown("##### 📋 Tabla de Sembrados (Seeds 1 al 6)")
            seeds_cols = [c for c in ["Logo", "Seed", "Team", "Record", "PCT", "Type", "Status", "Diff"] if c in df_seeds.columns]
            st.dataframe(df_seeds[seeds_cols], column_config=LOGO_CONFIG, use_container_width=True, hide_index=True)

            # 4. Equipos en la pelea (In The Hunt)
            if not df_hunt.empty:
                st.markdown("##### 🔥 En la Caza / In the Hunt (Perseguidores)")
                hunt_copy = df_hunt.copy()
                for c in ["Logo", "Team", "W", "L", "PCT", "WC_GB", "Elim_Number", "Streak", "L10"]:
                    if c not in hunt_copy.columns:
                        hunt_copy[c] = "-"
                hunt_cols = ["Logo", "Team", "W", "L", "PCT", "WC_GB", "Elim_Number", "Streak", "L10"]
                hunt_display = hunt_copy[hunt_cols].rename(columns={"WC_GB": "Juegos Detrás (WC GB)", "Elim_Number": "E# (Eliminación)"})
                hunt_display.index = range(7, 7 + len(hunt_display))
                st.dataframe(hunt_display, column_config=LOGO_CONFIG, use_container_width=True, hide_index=False)

            st.divider()
        else:
            st.info(f"Sin datos de postemporada para {lg_title}.")


# ── TAB 2: DIVISION STANDINGS & MAGIC NUMBERS ──────────────────────────────
with tab_div:
    st.subheader(f"🏟️ American League — Posiciones por División ({yr})")
    al_cols = st.columns(3)
    for i, div_name in enumerate(DIVISIONS_AL):
        with al_cols[i]:
            st.markdown(f"### {div_name}")
            df_div = tables.get(div_name, pd.DataFrame())
            if not df_div.empty:
                st.dataframe(_format_table(df_div), column_config=LOGO_CONFIG, use_container_width=True, hide_index=False)
            else:
                st.info("Sin datos.")

    st.divider()

    st.subheader(f"🏟️ National League — Posiciones por División ({yr})")
    nl_cols = st.columns(3)
    for i, div_name in enumerate(DIVISIONS_NL):
        with nl_cols[i]:
            st.markdown(f"### {div_name}")
            df_div = tables.get(div_name, pd.DataFrame())
            if not df_div.empty:
                st.dataframe(_format_table(df_div), column_config=LOGO_CONFIG, use_container_width=True, hide_index=False)
            else:
                st.info("Sin datos.")


# ── TAB 3: WILD CARD RACE ──────────────────────────────────────────────────
with tab_wc:
    st.subheader(f"🎫 Carrera por el Comodín (Wild Card Race) — {yr}")
    st.caption("Los 3 mejores equipos fuera de los líderes divisionales obtienen el boleto de Wild Card (Seeds 4, 5 y 6).")

    wc_col1, wc_col2 = st.columns(2)

    with wc_col1:
        st.markdown("### 🏟️ AL Wild Card Standings")
        al_all = []
        for d in DIVISIONS_AL:
            df_d = tables.get(d, pd.DataFrame())
            if not df_d.empty:
                al_all.append(df_d.iloc[1:].copy() if len(df_d) > 1 else df_d)
        if al_all:
            al_wc_df = pd.concat(al_all, ignore_index=True)
            if "W" in al_wc_df.columns:
                al_wc_df["W_num"] = pd.to_numeric(al_wc_df["W"], errors="coerce").fillna(0)
                al_wc_df["Diff_num"] = pd.to_numeric(al_wc_df["Diff"], errors="coerce").fillna(0)
                al_wc_df = al_wc_df.sort_values(by=["W_num", "Diff_num"], ascending=[False, False]).drop(columns=["W_num", "Diff_num"])
            st.dataframe(_format_table(al_wc_df, is_wc=True), column_config=LOGO_CONFIG, use_container_width=True, height=520)
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
            if "W" in nl_wc_df.columns:
                nl_wc_df["W_num"] = pd.to_numeric(nl_wc_df["W"], errors="coerce").fillna(0)
                nl_wc_df["Diff_num"] = pd.to_numeric(nl_wc_df["Diff"], errors="coerce").fillna(0)
                nl_wc_df = nl_wc_df.sort_values(by=["W_num", "Diff_num"], ascending=[False, False]).drop(columns=["W_num", "Diff_num"])
            st.dataframe(_format_table(nl_wc_df, is_wc=True), column_config=LOGO_CONFIG, use_container_width=True, height=520)
        else:
            st.info("Sin datos de NL.")

