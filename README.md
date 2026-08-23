# ⚾ MLB Intelligence & Fantasy Baseball Suite

Aplicación analítica integral en **Streamlit** para análisis avanzado de Grandes Ligas (MLB) y toma de decisiones estratégicas en **Fantasy Baseball** (Yahoo, ESPN, Fantrax, CBS, NFBC).

Combina la **MLB Stats API oficial** (`statsapi.mlb.com`), métricas sabermétricas de **FanGraphs** y datos de calidad de contacto de **Statcast**.

---

## 🎯 Módulos Principales

### 1. 📊 Leaderboards & Valoración Fantasy (`pages/1_Leaderboard.py`)
- **Vistas dinámicas**:
  - **Estándar**: AVG, OBP, SLG, OPS, wOBA, wRC+, WAR, ERA, FIP, xFIP, K/9, BB/9.
  - **Fantasy 5x5**: Z-Scores por categoría ($z_R, z_{HR}, z_{RBI}, z_{SB}, z_{AVG}$ y $z_W, z_{SV}, z_{SO}, z_{ERA}, z_{WHIP}$), ranking general (`Fantasy_Rank`) y puntos totales (`Fantasy_Pts`).
  - **Statcast**: Métricas esperadas ($xBA, xSLG, xwOBA, xERA$), diferenciales de regresión, HardHit% y Barrel%.
- **Filtros por Posición de Fantasy**: C, 1B, 2B, 3B, SS, OF, DH, SP, RP (obtenidos directamente de los rosters oficiales de MLB).
- **Filtros de Liga y Equipo**: AL, NL, Toda la MLB y selección de equipos individuales.

### 2. 🎯 Fantasy Intelligence Hub (`pages/4_Fantasy_Hub.py`)
- **🔍 Statcast Buy-Low / Sell-High**: Detector de jugadores con mala suerte estadística (candidatos a repuntar / comprar barato) vs sobre-rendimiento no sostenible.
- **📅 SP Streamer & Matchup Planner**: Planificador de abridores para la semana con evaluación automática del talento del lanzador, wRC+ del rival y factor de parque (Streamer Score de 1 a 100), con alertas de lanzadores de doble apertura (**Two-Start Pitchers**).
- **🔒 Bullpen & Closer Depth Chart**: Monitoreo de jerarquías en los 30 bullpens (Cerradores titulares, Setup de 8va entrada, comités y sleepers de salvamentos/holds).
- **⚖️ Comparador Cara a Cara & Trade Analyzer**: Comparador visual y estadístico entre 2 a 4 jugadores para evaluar alineaciones y trades.

### 3. 🏆 Standings & Postseason Picture (`pages/2_Standings.py`)
- Posiciones oficiales en vivo por división (AL / NL East, Central, West).
- Tabla de **Wild Card (Comodín)** con la carrera por los 3 cupos a la postemporada.

### 4. 📅 Calendario & Schedule por Equipo (`pages/3_Schedule.py`)
- Historial de partidos disputados con resultados, lanzadores ganadores/perdedores y salvamentos.
- Calendario de juegos futuros con **lanzadores abridores probables**.

### 5. 📊 Estadísticas Colectivas (`app.py`)
- Dashboard ejecutivo con líderes de la temporada y comparativas colectivas por equipo (Bateo, Pitcheo y Fildeo) con gráficos interactivos de Plotly.

---

## 🏗️ Estructura del Proyecto

```
mlb_stats/
├── app.py                      # Dashboard Principal y Estadísticas Colectivas
├── constants.py                # Mapeos de equipos, factores de parque, columnas y presets de Fantasy
├── fantasy.py                  # Motor de Z-Scores 5x5, Puntos Fantasy, Regresión Statcast y SP Streaming
├── fetcher.py                  # Cliente MLB Stats API oficial + FanGraphs con caché Parquet/JSON
├── utils.py                    # Formateo visual numérico (slash stats, %, z-scores, diferenciales)
├── pages/
│   ├── 1_Leaderboard.py        # Leaderboards individuales con filtros de posición y vistas Fantasy
│   ├── 2_Standings.py          # Standings por división y Wild Card oficial
│   ├── 3_Schedule.py           # Calendario por equipo con abridores probables
│   └── 4_Fantasy_Hub.py        # Hub de Fantasy (Buy-Low/Sell-High, SP Streamer, Bullpen, Trade Analyzer)
├── cache/                      # Almacenamiento local en Parquet y JSON
├── scripts/
│   └── refresh_cache.py        # Script de actualización programada de datos
├── requirements.txt            # Dependencias del proyecto
└── README.md                   # Documentación técnica
```

---

## 🚀 Instalación y Uso Local

```bash
# 1. Clonar el repositorio
git clone https://github.com/TU_USUARIO/mlb_stats.git
cd mlb_stats

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar la aplicación Streamlit
streamlit run app.py
```

---

## 🌐 Despliegue en Streamlit Community Cloud

1. Sube el repositorio a GitHub (rama `main`).
2. Ve a [share.streamlit.io](https://share.streamlit.io).
3. Conecta tu repositorio seleccionando `app.py` como **Main file**.
4. ¡Listo! La suite se desplegará automáticamente.

---

## 👨‍💻 Autor

**Jorge Leonardo Loreto**  
*Economista & AI Data Scientist — Especialista en Sabermetría y Modelado Analítico*

- **GitHub:** [@jloreto9](https://github.com/jloreto9)
- **Portafolio:** [jloreto9.github.io](https://jloreto9.github.io)
- **LinkedIn:** [linkedin.com/in/jloreto](https://www.linkedin.com/in/jloreto/)

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.

