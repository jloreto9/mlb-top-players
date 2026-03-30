# ⚾ MLB Top Players por Liga

Aplicación Streamlit que rankea los mejores bateadores y pitchers de MLB por liga (AL / NL) usando datos **pitch-by-pitch de Statcast (Baseball Savant)**.

## Métricas principales

| Grupo | Métrica | Descripción |
|---|---|---|
| Bateadores | **xwOBA** | Calidad de contacto esperada (exit velocity + launch angle) |
| Bateadores | xBA, xSLG, AVG, OBP, SLG, OPS, K%, BB%, HR | Complementarias |
| Pitchers | **xERA** | ERA esperado por calidad de contacto permitido |
| Pitchers | ERA~, WHIP, K/9, BB/9, K%, BB%, velo, spin | Complementarias |

> **Nota:** `ERA~` es una aproximación via diferencial de score, no ERA oficial.  
> `xERA` usa la fórmula aproximada de Baseball Savant: `(xwOBA_against - 0.100) / 0.140 * 9`.

## Estructura del proyecto

```
mlb_stats/
├── app.py           # Streamlit UI
├── main.py          # Pipeline principal (importable)
├── fetcher.py       # Descarga Statcast + caché Parquet
├── calculator.py    # Cálculo de métricas por jugador
├── ranker.py        # Asignación AL/NL + Top N
├── requirements.txt
└── README.md
```

## Instalación local

```bash
git clone https://github.com/TU_USUARIO/mlb-top-players.git
cd mlb-top-players

pip install -r requirements.txt

streamlit run app.py
```

## Deploy en Streamlit Cloud

1. Sube el repositorio a GitHub (rama `main`)
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu repo y apunta el **Main file** a `app.py`
4. Deploy

> Streamlit Cloud instala automáticamente las dependencias de `requirements.txt`.

## Uso

1. Selecciona el **rango de fechas** en el sidebar
2. Ajusta **Top N**, **min PA** y **min BF**
3. Presiona **▶ Ejecutar**
4. Navega entre tabs **Bateadores** / **Pitchers** → sub-tabs **AL** / **NL**

### Caché local

La primera descarga de Statcast puede tardar varios minutos dependiendo del rango.  
Los datos se guardan en `cache/` como Parquet para ejecuciones posteriores.  
Usa **🔄 Forzar re-descarga** para refrescar.

> En Streamlit Cloud el caché es efímero (se borra al reiniciar la app).

## Advertencias

- La **asignación AL/NL** usa `home_team` del juego como proxy — muy preciso en temporada completa, con posible ruido en rangos cortos
- Sin filtro mínimo de PA/BF aparecen jugadores con muestras pequeñas y métricas extremas
- Statcast tiene datos desde **2015**

## Dependencias

```
pybaseball>=2.2.7
pandas>=2.0.0
numpy>=1.24.0
pyarrow>=14.0.0
streamlit>=1.32.0
```
