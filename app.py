import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import datetime

st.set_page_config(page_title="Dashboard CD / CW", layout="wide")

# -------------------------
# 1) CARGA DE DATOS (archivos reales)
# -------------------------
@st.cache_data
def load_sources():
    # Archivos que dijiste tener en el repo
    df_cd = pd.read_csv("CD_unificado.csv")
    df_cw = pd.read_csv("CW_unificado.csv")
    # Excel de límites en formato ancho (bloques de 3 columnas por máquina)
    lim_raw = pd.read_excel("Limites en tablas (1).xlsx", header=None)
    return df_cd, df_cw, lim_raw

try:
    df_cd, df_cw, lim_raw = load_sources()
except FileNotFoundError as e:
    st.error(f"Archivo no encontrado: {e}. Asegúrate que los archivos están en la raíz del repo con esos nombres.")
    st.stop()

# -------------------------
# 2) NORMALIZACIÓN BÁSICA (columnas)
# -------------------------
# Añadir área si no existe
if "area" not in df_cd.columns:
    df_cd["area"] = "CD"
if "area" not in df_cw.columns:
    df_cw["area"] = "CW"

# Unir datasets
df_all = pd.concat([df_cd, df_cw], ignore_index=True)

# Normalizar nombres de columnas: convertir a minúsculas y quitar espacios alrededor
df_all.columns = df_all.columns.str.strip()
# Además creamos una versión lowercase para búsquedas consistentes
df_all.rename(columns={c: c.strip() for c in df_all.columns}, inplace=True)

# Haremos también una versión con nombres lower para accesos cómodos
df_all.columns = [c.lower() for c in df_all.columns]

# Asegurar algunas columnas clave estén presentes (si no, crear vacías para evitar KeyError)
for col in ["maquina", "linea", "categoria", "date", "time"]:
    if col not in df_all.columns:
        df_all[col] = np.nan

# -------------------------
# 3) TRANSFORMAR LIMPIEZAS DE LÍMITES (formato ancho de 3 columnas por máquina)
# -------------------------
def parse_limits_wide(df_raw):
    """
    Recibe lim_raw (header=None) y devuelve df_limites con columnas:
    maquina (lower), variable (lower), limite_inferior (float), limite_superior (float)
    """
    lims = []
    ncols = df_raw.shape[1]
    # cada bloque = 3 columnas (variable, limite inferior, limite superior)
    bloques = ncols // 3
    for i in range(bloques):
        start = i * 3
        # nombre de máquina en la fila 0, columna start
        raw_name = df_raw.iloc[0, start]
        if pd.isna(raw_name):
            continue
        machine_name = str(raw_name).strip().lower()
        # obtener datos desde fila 1 hacia abajo
        block = df_raw.iloc[1:, start:start+3].copy()
        block.columns = ["variable", "limite_inferior", "limite_superior"]
        # eliminar filas totalmente vacías en variable
        for idx, row in block.iterrows():
            var = row["variable"]
            if pd.isna(var):
                continue
            lims.append({
                "maquina": machine_name,
                "variable": str(var).strip().lower(),
                "limite_inferior": pd.to_numeric(row["limite_inferior"], errors="coerce"),
                "limite_superior": pd.to_numeric(row["limite_superior"], errors="coerce")
            })
    if not lims:
        return pd.DataFrame(columns=["maquina", "variable", "limite_inferior", "limite_superior"])
    return pd.DataFrame(lims)

df_limites = parse_limits_wide(lim_raw)

# -------------------------
# 4) SIDEBAR - FILTROS
# -------------------------
st.sidebar.title("Filtros")

# Opciones para categoría / linea / maquina (usar valores únicos del df_all)
categorias = ["Todas"] + sorted(df_all["categoria"].dropna().unique().astype(str).tolist())
lineas = ["Todas"] + sorted(df_all["linea"].dropna().unique().astype(str).tolist())

# máquinas: combinar las de df_all y las de df_limites si faltan
maquinas_from_data = sorted(df_all["maquina"].dropna().unique().astype(str).tolist())
maquinas_from_limits = sorted(df_limites["maquina"].dropna().unique().astype(str).tolist())
maquinas = ["Todas"] + sorted(list(dict.fromkeys(maquinas_from_data + maquinas_from_limits)))

categoria_sel = st.sidebar.selectbox("Categoría", categorias)
linea_sel = st.sidebar.selectbox("Línea", lineas)
maquina_sel = st.sidebar.selectbox("Máquina", maquinas)

# Detectar métricas numéricas válidas (robusto)
exclude_cols = {"maquina", "linea", "categoria", "date", "time", "area", "status", "serial_number", "model"}
metricas = []
for c in df_all.columns:
    if c.lower() in exclude_cols:
        continue
    if pd.api.types.is_numeric_dtype(df_all[c]):
        if df_all[c].notna().sum() > 5 and df_all[c].nunique() > 1:
            metricas.append(c)
metricas = sorted(metricas)

if not metricas:
    st.error("No se detectaron métricas numéricas válidas en el dataset.")
    st.stop()

metrica_sel = st.sidebar.selectbox("Métrica", metricas)

# Rango de fechas (si existe columna date)
df_all["date"] = pd.to_datetime(df_all["date"], errors="coerce")
fechas_validas = df_all["date"].dropna()
if len(fechas_validas) == 0:
    fecha_min = fecha_max = datetime.date.today()
else:
    fecha_min = fechas_validas.min().date()
    fecha_max = fechas_validas.max().date()

rango_fechas = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max])

mostrar_tabs = st.sidebar.checkbox("Mostrar gráficas avanzadas", value=True)

# -------------------------
# 5) APLICAR FILTROS
# -------------------------
df_filt = df_all.copy()
if categoria_sel != "Todas":
    df_filt = df_filt[df_filt["categoria"].astype(str) == categoria_sel]
if linea_sel != "Todas":
    df_filt = df_filt[df_filt["linea"].astype(str) == linea_sel]
if maquina_sel != "Todas":
    # comparaciones insensibles a mayúsculas
    df_filt = df_filt[df_filt["maquina"].astype(str).str.lower() == maquina_sel.lower()]

# aplicar rango de fechas
df_filt = df_filt[(df_filt["date"] >= pd.to_datetime(rango_fechas[0])) & (df_filt["date"] <= pd.to_datetime(rango_fechas[-1]))]

# Mostrar título
st.title("Dashboard CD / CW")
st.subheader(f"{linea_sel} • {categoria_sel} • {maquina_sel}")
st.markdown(f"**Métrica:** {metrica_sel}")

if df_filt.empty:
    st.warning("No hay registros para los filtros seleccionados.")
    st.stop()

# -------------------------
# 6) BUSCAR LÍMITES (heurísticas)
# -------------------------
lim_row = pd.DataFrame()
if maquina_sel != "Todas":
    # clave directa: maquina
    key = maquina_sel.strip().lower()
    cand = df_limites[(df_limites["maquina"] == key) & (df_limites["variable"] == metrica_sel.lower())]
    if not cand.empty:
        lim_row = cand
    else:
        # intentar buscar por combinaciones: linea_categoria por si en tu naming está así (e.g. fvt7_cd)
        if linea_sel != "Todas" and categoria_sel != "Todas":
            key2 = f"{linea_sel.strip().lower()}_{categoria_sel.strip().lower()}"
            cand2 = df_limites[(df_limites["maquina"] == key2) & (df_limites["variable"] == metrica_sel.lower())]
            if not cand2.empty:
                lim_row = cand2
        # último intento: buscar solo por variable en todo df_limites (si hay un único match)
        if lim_row.empty:
            cand3 = df_limites[df_limites["variable"] == metrica_sel.lower()]
            if len(cand3) == 1:
                lim_row = cand3

# -------------------------
# 7) GRÁFICA PRINCIPAL (Plotly) con límites si existen
# -------------------------
fig = go.Figure()
# Asegurar que x tenga nombre; si date no sirve, usar índice
x = df_filt["date"] if "date" in df_filt.columns else df_filt.index

fig.add_trace(go.Scatter(x=x, y=df_filt[metrica_sel], mode="lines+markers", name=metrica_sel))

if not lim_row.empty:
    li = lim_row.iloc[0].get("limite_inferior", np.nan)
    ls = lim_row.iloc[0].get("limite_superior", np.nan)
    if pd.notna(ls):
        fig.add_hline(y=ls, line_dash="dash", line_color="red", annotation_text="USL")
    if pd.notna(li):
        fig.add_hline(y=li, line_dash="dot", line_color="green", annotation_text="LSL")

fig.update_layout(title=f"Tendencia: {metrica_sel}", xaxis_title="Fecha", yaxis_title=metrica_sel, template="plotly_white", height=520)
st.plotly_chart(fig, use_container_width=True)

# -------------------------
# 8) KPIs y métricas rápidas
# -------------------------
c1, c2, c3 = st.columns(3)
c1.metric("Registros", len(df_filt))
c2.metric("Promedio", f"{df_filt[metrica_sel].mean():.3f}")
c3.metric("Std Dev", f"{df_filt[metrica_sel].std():.3f}")

# -------------------------
# 9) Gráficas avanzadas (opcionales)
# -------------------------
if mostrar_tabs:
    tabs = st.tabs(["Histograma", "Boxplot por Máquina", "Control X-MR", "Pareto Status", "Heatmap (métricas)"])

    # Histograma
    with tabs[0]:
        st.subheader("Histograma")
        fig_h = px.histogram(df_filt, x=metrica_sel, nbins=25, title=f"Distribución de {metrica_sel}")
        # dibujar líneas de límite si existen
        if not lim_row.empty:
            if pd.notna(li := lim_row.iloc[0].get("limite_inferior", np.nan)):
                fig_h.add_vline(x=li, line_dash="dash", line_color="green")
            if pd.notna(ls := lim_row.iloc[0].get("limite_superior", np.nan)):
                fig_h.add_vline(x=ls, line_dash="dash", line_color="red")
        st.plotly_chart(fig_h, use_container_width=True)

    # Boxplot por máquina (si hay más de una máquina en el filtro)
    with tabs[1]:
        st.subheader("Boxplot por Máquina")
        df_box = df_all.copy()
        if linea_sel != "Todas":
            df_box = df_box[df_box["linea"] == linea_sel]
        if categoria_sel != "Todas":
            df_box = df_box[df_box["categoria"] == categoria_sel]
        if df_box.empty:
            st.info("No hay datos para boxplot en la combinación seleccionada.")
        else:
            fig_b = px.box(df_box, x="maquina", y=metrica_sel, points="outliers", title=f"Boxplot {metrica_sel} por máquina")
            st.plotly_chart(fig_b, use_container_width=True)

    # Control X-MR
    with tabs[2]:
        st.subheader("Control Chart (X-MR)")
        if len(df_filt) >= 4:
            df_cc = df_filt.sort_values("date").copy()
            df_cc["mr"] = df_cc[metrica_sel].diff().abs()
            fig_x = px.line(df_cc, x="date", y=metrica_sel, title="X Chart")
            fig_mr = px.line(df_cc, x="date", y="mr", title="MR Chart")
            st.plotly_chart(fig_x, use_container_width=True)
            st.plotly_chart(fig_mr, use_container_width=True)
        else:
            st.info("Se requieren al menos 4 puntos para X-MR.")

    # Pareto Status
    with tabs[3]:
        st.subheader("Pareto - Status")
        if "status" in df_filt.columns:
            df_stat = df_filt["status"].fillna("UNKNOWN").value_counts().reset_index()
            df_stat.columns = ["status", "count"]
            fig_p = px.bar(df_stat, x="status", y="count", title="Pareto de Status")
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.info("No existe columna 'status' en los datos.")

    # Heatmap de métricas (por fecha, promedio diario)
    with tabs[4]:
        st.subheader("Heatmap (promedio diario de métricas)")
        numeric = [c for c in df_all.columns if pd.api.types.is_numeric_dtype(df_all[c])]
        if numeric:
            df_hm = df_filt.copy()
            if "date" in df_hm.columns:
                df_hm = df_hm.groupby("date")[numeric].mean().fillna(0)
                # limitar columnas si son muchas
                if df_hm.shape[1] > 30:
                    top_cols = df_hm.var().sort_values(ascending=False).head(30).index
                    df_hm = df_hm[top_cols]
                fig_hm = px.imshow(df_hm.T, labels=dict(x="Fecha", y="Métrica", color="Valor"), aspect="auto", origin="lower")
                st.plotly_chart(fig_hm, use_container_width=True)
            else:
                st.info("No hay columna 'date' para agrupar por día.")
        else:
            st.info("No hay columnas numéricas para heatmap.")

# -------------------------
# 10) Tabla y descarga
# -------------------------
st.markdown("### Datos filtrados (muestra)")
cols_show = ["date", "time", "maquina", "linea", "categoria", metrica_sel]
cols_show = [c for c in cols_show if c in df_filt.columns]
st.dataframe(df_filt[cols_show].head(500))

csv_bytes = df_filt.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Descargar (CSV) datos filtrados", csv_bytes, "datos_filtrados.csv", "text/csv")
