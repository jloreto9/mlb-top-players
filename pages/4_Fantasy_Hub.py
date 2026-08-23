"""
pages/4_Fantasy_Hub.py
------------------------
Centro de Comando y Herramientas Estratégicas para Fantasy Baseball:
1. 🔍 Statcast Buy-Low & Sell-High (Detección de regresión esperada)
2. 📅 SP Streamer & Two-Start Pitchers (Matchup Planner semanal)
3. 🔒 Bullpen & Closer Depth Chart (Cazador de Salvamentos y Holds)
4. ⚖️ Comparador Cara a Cara & Trade Analyzer (Visual & Métricas)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px

import fetcher
import fantasy
from constants import (
    MLB_TEAMS, PARK_FACTORS, FANTASY_SCORING_PRESETS,
    STATCAST_BAT_COLS, STATCAST_PIT_COLS, LOWER_IS_BETTER, AVAILABLE_SEASONS, get_team_logo
)
from utils import format_display

st.set_page_config(
    page_title="Fantasy Hub · MLB Stats",
    page_icon="🎯",
    layout="wide",
)

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎯 Fantasy Hub")
    st.caption("Herramientas avanzadas para dominar tu liga")
    st.divider()

    year = st.selectbox(
        "Temporada",
        options=AVAILABLE_SEASONS,
        index=0,
    )
    scoring_preset = st.selectbox(
        "Formato de Puntos",
        options=list(FANTASY_SCORING_PRESETS.keys()),
        index=0,
    )
    force = st.checkbox("🔄 Forzar re-descarga", value=False)
    st.divider()
    run_btn = st.button("▶ Cargar Fantasy Hub", type="primary", use_container_width=True)

# ── Session State ──────────────────────────────────────────────────────────
for k in ("fh_bat", "fh_pit", "fh_tbat", "fh_year"):
    if k not in st.session_state:
        st.session_state[k] = None

if run_btn or st.session_state.fh_bat is None or st.session_state.fh_year != year:
    with st.spinner("Cargando analítica avanzada de Fantasy..."):
        try:
            raw_bat = fetcher.batting(year, force=force)
            raw_pit = fetcher.pitching(year, force=force)
            tbat = fetcher.team_bat(year, force=force)

            st.session_state.fh_bat = fantasy.calculate_batting_fantasy(raw_bat, scoring_preset)
            st.session_state.fh_pit = fantasy.calculate_pitching_fantasy(raw_pit, scoring_preset)
            st.session_state.fh_tbat = tbat
            st.session_state.fh_year = year
        except Exception as e:
            st.error(f"❌ Error al cargar Fantasy Hub: {e}")
            st.stop()

st.title("🎯 Fantasy Baseball Intelligence Hub")
st.caption(f"Temporada **{st.session_state.fh_year}** · Scoring: **{scoring_preset}** · Statcast & FanGraphs")

bat_df = st.session_state.fh_bat.copy()
pit_df = st.session_state.fh_pit.copy()
tbat_df = st.session_state.fh_tbat.copy() if st.session_state.fh_tbat is not None else pd.DataFrame()

# ── Tabs Principales ───────────────────────────────────────────────────────
tab_buy_sell, tab_streamer, tab_bullpen, tab_compare = st.tabs([
    "🔍 Buy-Low / Sell-High",
    "📅 SP Streamer & Matchups",
    "🔒 Bullpen & Closers",
    "⚖️ Comparador de Jugadores",
])

# ── TAB 1: Buy-Low / Sell-High ─────────────────────────────────────────────
with tab_buy_sell:
    st.subheader("🔍 Detector de Regresión Esperada (Statcast)")
    st.markdown(
        "Identifica jugadores con desvíos estadísticos significativos entre sus números reales y esperados. "
        "Ideal para hacer **ofertas de trade ganadoras** o encontrar gangas en la agencia libre (waivers)."
    )

    c1, c2 = st.columns(2)
    with c1:
        min_pa = st.slider("Mínimo de Turnos al Bate (PA)", 30, 400, 80, step=10, key="bl_pa")
    with c2:
        min_ip = st.slider("Mínimo de Entradas Lanzadas (IP)", 10, 200, 30, step=5, key="bl_ip")

    reg_dict = fantasy.get_buy_low_sell_high(bat_df, pit_df, min_pa=min_pa, min_ip=min_ip)

    FH_LOGO_CONFIG = {"Logo": st.column_config.ImageColumn("Logo", width="small")}

    st.divider()
    b_col1, b_col2 = st.columns(2)

    with b_col1:
        st.markdown("### 🟢 Bateadores: Candidatos a Repuntar (Buy-Low)")
        st.caption("Tienen métricas Statcast superiores a sus números tradicionales (xwOBA > wOBA).")
        buy_bat = reg_dict["bat_buy_low"].copy()
        if not buy_bat.empty:
            if "Logo" not in buy_bat.columns and "Team" in buy_bat.columns:
                buy_bat.insert(0, "Logo", buy_bat["Team"].apply(get_team_logo))
            cols = ["Logo", "Name", "Team", "Pos", "PA", "AVG", "xBA", "diff_BA", "wOBA", "xwOBA", "diff_wOBA", "HardHit%", "Barrel%"]
            disp_cols = [c for c in cols if c in buy_bat.columns]
            st.dataframe(format_display(buy_bat[disp_cols].head(30)), column_config=FH_LOGO_CONFIG, use_container_width=True, hide_index=True)
            st.download_button("📥 Descargar Bateadores Buy-Low (CSV)", data=buy_bat[disp_cols].to_csv(index=False).encode('utf-8'), file_name=f"buy_low_batting_{year}.csv", mime="text/csv")
        else:
            st.info("No hay candidatos suficientes con el filtro actual.")

    with b_col2:
        st.markdown("### 🔴 Bateadores: Riesgo de Caída (Sell-High)")
        st.caption("Están sobre-rindiendo su calidad real de contacto (wOBA > xwOBA).")
        sell_bat = reg_dict["bat_sell_high"].copy()
        if not sell_bat.empty:
            if "Logo" not in sell_bat.columns and "Team" in sell_bat.columns:
                sell_bat.insert(0, "Logo", sell_bat["Team"].apply(get_team_logo))
            cols = ["Logo", "Name", "Team", "Pos", "PA", "AVG", "xBA", "diff_BA", "wOBA", "xwOBA", "diff_wOBA", "HardHit%", "Barrel%"]
            disp_cols = [c for c in cols if c in sell_bat.columns]
            st.dataframe(format_display(sell_bat[disp_cols].head(30)), column_config=FH_LOGO_CONFIG, use_container_width=True, hide_index=True)
            st.download_button("📥 Descargar Bateadores Sell-High (CSV)", data=sell_bat[disp_cols].to_csv(index=False).encode('utf-8'), file_name=f"sell_high_batting_{year}.csv", mime="text/csv")
        else:
            st.info("No hay candidatos suficientes con el filtro actual.")

    st.divider()
    p_col1, p_col2 = st.columns(2)

    with p_col1:
        st.markdown("### 🟢 Pitchers: Efectividad Inflada por Mala Suerte (Buy-Low)")
        st.caption("Tienen una ERA más alta que su xERA / SIERA pero mantienen buen Stuff/K%.")
        buy_pit = reg_dict["pit_buy_low"].copy()
        if not buy_pit.empty:
            if "Logo" not in buy_pit.columns and "Team" in buy_pit.columns:
                buy_pit.insert(0, "Logo", buy_pit["Team"].apply(get_team_logo))
            cols = ["Logo", "Name", "Team", "Pos", "IP", "ERA", "xERA", "diff_ERA", "SIERA", "WHIP", "SO", "K%", "BB%"]
            disp_cols = [c for c in cols if c in buy_pit.columns]
            st.dataframe(format_display(buy_pit[disp_cols].head(30)), column_config=FH_LOGO_CONFIG, use_container_width=True, hide_index=True)
            st.download_button("📥 Descargar Pitchers Buy-Low (CSV)", data=buy_pit[disp_cols].to_csv(index=False).encode('utf-8'), file_name=f"buy_low_pitching_{year}.csv", mime="text/csv")
        else:
            st.info("Sin candidatos.")

    with p_col2:
        st.markdown("### 🔴 Pitchers: Efectividad Engañosa (Sell-High)")
        st.caption("Tienen una ERA baja pero su contacto permitido (xERA) predice regresión negativa.")
        sell_pit = reg_dict["pit_sell_high"].copy()
        if not sell_pit.empty:
            if "Logo" not in sell_pit.columns and "Team" in sell_pit.columns:
                sell_pit.insert(0, "Logo", sell_pit["Team"].apply(get_team_logo))
            cols = ["Logo", "Name", "Team", "Pos", "IP", "ERA", "xERA", "diff_ERA", "SIERA", "WHIP", "SO", "K%", "BB%"]
            disp_cols = [c for c in cols if c in sell_pit.columns]
            st.dataframe(format_display(sell_pit[disp_cols].head(30)), column_config=FH_LOGO_CONFIG, use_container_width=True, hide_index=True)
            st.download_button("📥 Descargar Pitchers Sell-High (CSV)", data=sell_pit[disp_cols].to_csv(index=False).encode('utf-8'), file_name=f"sell_high_pitching_{year}.csv", mime="text/csv")
        else:
            st.info("Sin candidatos.")


# ── TAB 2: SP Streamer & Matchups ───────────────────────────────────────────
with tab_streamer:
    st.subheader("📅 SP Streamer & Two-Start Pitchers Planner")
    st.markdown(
        "Planifica tus lanzadores abridores para la semana. El algoritmo evalúa el **talento del abridor (K%, ERA, WHIP)**, "
        "el **nivel ofensivo del rival (wRC+)** y el **factor de parque**, generando un **Streamer Score de 1 a 100**."
    )

    sc1, sc2 = st.columns([2, 2])
    today = datetime.now().date()
    
    def_start = today
    def_end = today + timedelta(days=6)
    if year < datetime.now().year:
        def_start = datetime(year, 5, 10).date()
        def_end = datetime(year, 5, 16).date()

    with sc1:
        s_date = st.date_input("Fecha Inicio", value=def_start)
    with sc2:
        e_date = st.date_input("Fecha Fin", value=def_end)

    if s_date and e_date:
        with st.spinner("Consultando calendario oficial de MLB..."):
            sched_df = fetcher.get_schedule_range(str(s_date), str(e_date))
            eval_sp = fantasy.evaluate_sp_matchups(sched_df, pit_df, tbat_df)

        if not eval_sp.empty:
            two_starts = eval_sp[eval_sp["Two_Start"] == "⭐ 2-Starts"]["Pitcher"].nunique()
            must_starts = len(eval_sp[eval_sp["Verdict"] == "🟢 Must-Start"])
            good_streams = len(eval_sp[eval_sp["Verdict"] == "🟢 Buen Stream"])

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Juegos Programados", len(eval_sp))
            m2.metric("Lanzadores 2-Starts ⭐", two_starts)
            m3.metric("Must-Start 🟢", must_starts)
            m4.metric("Buen Stream 🟢", good_streams)

            st.divider()

            fc1, fc2 = st.columns(2)
            with fc1:
                verdict_filter = st.multiselect(
                    "Filtrar por Veredicto",
                    options=["🟢 Must-Start", "🟢 Buen Stream", "🟡 Opcional / Riesgo", "🔴 Evitar (Sit)"],
                    default=["🟢 Must-Start", "🟢 Buen Stream", "🟡 Opcional / Riesgo"],
                )
            with fc2:
                only_two_starts = st.checkbox("Mostrar únicamente lanzadores de doble salida (⭐ 2-Starts)", value=False)

            filtered_sp = eval_sp.copy()
            if verdict_filter:
                filtered_sp = filtered_sp[filtered_sp["Verdict"].isin(verdict_filter)]
            if only_two_starts:
                filtered_sp = filtered_sp[filtered_sp["Two_Start"] == "⭐ 2-Starts"]

            if "Logo" not in filtered_sp.columns and "Team" in filtered_sp.columns:
                filtered_sp.insert(0, "Logo", filtered_sp["Team"].apply(get_team_logo))

            sp_logo_config = {"Logo": st.column_config.ImageColumn("Logo", width="small")}
            st.dataframe(format_display(filtered_sp), column_config=sp_logo_config, use_container_width=True, height=550, hide_index=True)
            st.download_button("📥 Descargar Planificador de Abridores (CSV)", data=filtered_sp.to_csv(index=False).encode('utf-8'), file_name=f"sp_streamer_{s_date}_{e_date}.csv", mime="text/csv")
        else:
            st.info("No se encontraron partidos o abridores programados para el rango de fechas seleccionado.")


# ── TAB 3: Bullpen & Closers ────────────────────────────────────────────────
with tab_bullpen:
    st.subheader("🔒 Bullpen & Closer Depth Chart")
    st.markdown(
        "Monitorea los roles de bullpen en las 30 organizaciones: cerradores establecidos, comités de rescates, "
        "relevistas de 8va entrada (*Setup / Holds*) y relevistas dominantes con potencial de heredar el puesto."
    )

    bp_df = fantasy.get_bullpen_depth_chart(pit_df)
    if not bp_df.empty:
        tm_sel = st.multiselect(
            "Filtrar por Equipo",
            options=sorted(bp_df["Team"].dropna().unique().tolist()),
            default=[],
            placeholder="Todos los equipos",
        )

        f_bp = bp_df[bp_df["Team"].isin(tm_sel)] if tm_sel else bp_df.copy()
        if "Logo" not in f_bp.columns and "Team" in f_bp.columns:
            f_bp.insert(0, "Logo", f_bp["Team"].apply(get_team_logo))
        
        bp_logo_config = {"Logo": st.column_config.ImageColumn("Logo", width="small")}
        st.dataframe(format_display(f_bp), column_config=bp_logo_config, use_container_width=True, height=600, hide_index=True)
        st.download_button("📥 Descargar Jerarquías de Bullpen (CSV)", data=f_bp.to_csv(index=False).encode('utf-8'), file_name=f"bullpen_depth_chart_{year}.csv", mime="text/csv")
    else:
        st.info("Sin datos suficientes de bullpen.")


# ── TAB 4: Comparador de Jugadores (Trade Analyzer) ─────────────────────────
with tab_compare:
    st.subheader("⚖️ Comparador Cara a Cara & Trade Analyzer")
    st.markdown(
        "Compara de 2 a 4 jugadores simultáneamente con métricas tradicionales, valores de Fantasy y gráficos comparativos."
    )

    comp_type = st.radio("Tipo de Jugadores", options=["Bateadores", "Pitchers"], horizontal=True)

    if comp_type == "Bateadores":
        avail_players = sorted(bat_df["Name"].dropna().unique().tolist())
        def_players = [p for p in ["Aaron Judge", "Shohei Ohtani", "Juan Soto", "Bobby Witt Jr."] if p in avail_players][:3]
        sel_players = st.multiselect("Selecciona Jugadores a Comparar", options=avail_players, default=def_players)

        if sel_players:
            comp_df = bat_df[bat_df["Name"].isin(sel_players)].copy()
            if "Logo" not in comp_df.columns and "Team" in comp_df.columns:
                comp_df.insert(0, "Logo", comp_df["Team"].apply(get_team_logo))
            show_cols = ["Logo", "Name", "Team", "Pos", "G", "PA", "R", "HR", "RBI", "SB", "AVG", "OBP", "SLG", "wOBA", "xwOBA", "HardHit%", "Barrel%", "Fantasy_Rank", "Fantasy_Pts", "z_Total"]
            st.markdown("#### 📋 Tabla Comparativa")
            comp_logo_cfg = {"Logo": st.column_config.ImageColumn("Logo", width="small")}
            st.dataframe(format_display(comp_df[[c for c in show_cols if c in comp_df.columns]]), column_config=comp_logo_cfg, use_container_width=True, hide_index=True)

            fig = px.bar(
                comp_df,
                x="Name",
                y="Fantasy_Pts",
                color="Name",
                text="Fantasy_Pts",
                title=f"Puntos Fantasy ({scoring_preset}) — {year}",
            )
            fig.update_layout(showlegend=False, yaxis_title="Puntos Fantasy")
            st.plotly_chart(fig, use_container_width=True)

    else:
        avail_players = sorted(pit_df["Name"].dropna().unique().tolist())
        def_players = [p for p in ["Tarik Skubal", "Paul Skenes", "Garrett Crochet"] if p in avail_players][:3]
        sel_players = st.multiselect("Selecciona Pitchers a Comparar", options=avail_players, default=def_players)

        if sel_players:
            comp_df = pit_df[pit_df["Name"].isin(sel_players)].copy()
            if "Logo" not in comp_df.columns and "Team" in comp_df.columns:
                comp_df.insert(0, "Logo", comp_df["Team"].apply(get_team_logo))
            show_cols = ["Logo", "Name", "Team", "Pos", "W", "L", "SV", "IP", "ERA", "xERA", "SIERA", "WHIP", "SO", "K%", "BB%", "Stuff+", "Fantasy_Rank", "Fantasy_Pts", "z_Total"]
            st.markdown("#### 📋 Tabla Comparativa")
            comp_logo_cfg = {"Logo": st.column_config.ImageColumn("Logo", width="small")}
            st.dataframe(format_display(comp_df[[c for c in show_cols if c in comp_df.columns]]), column_config=comp_logo_cfg, use_container_width=True, hide_index=True)

            fig = px.bar(
                comp_df,
                x="Name",
                y="Fantasy_Pts",
                color="Name",
                text="Fantasy_Pts",
                title=f"Puntos Fantasy Pitchers ({scoring_preset}) — {year}",
            )
            fig.update_layout(showlegend=False, yaxis_title="Puntos Fantasy")
            st.plotly_chart(fig, use_container_width=True)
