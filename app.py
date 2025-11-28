import streamlit as st
import pandas as pd
import plotly.express as px
import os

# ============================
# CARGA DE ARCHIVOS
# ============================
@st.cache_data
def load_data():
    # Buscar automáticamente cualquier Excel en la carpeta
    archivos = [f for f in os.listdir() if f.lower().endswith(".xlsx")]

    if len(archivos) == 0:
        st.error("No se encontró ningún archivo .xlsx en el directorio.")
        return None
    
    archivo = archivos[0]  # toma el primero
    df = pd.read_excel(archivo)

    return df

df = load_data()

if df is None:
    st.stop()

st.title("Dashboard CD / CW")

# ============================
# OBTENER OPCIONES DINÁMICAS
# ============================

# Buscar columna que identifique estación (FVT100, FVT7, etc)
col_estacion = None
for col in df.columns:
    if "fvt" in col.lower() or "estacion" in col.lower():
        col_estacion = col
        break

if col_estacion is None:
    st.error("No se encontró columna de estación (FVT...).")
    st.stop()

# CD / CW
col_cd_cw = None
for col in df.columns:
    if col.lower() in ["cd/cw", "mode", "tipo", "cdcw"]:
        col_cd_cw = col
        break

if col_cd_cw is None:
    st.error("No se encontró columna CD/CW.")
    st.stop()

# Métricas = todas las columnas numéricas excepto las de identificación
metric_columns = df.select_dtypes(include="number").columns.tolist()

# ============================
# SIDEBAR
# ============================
with st.sidebar:
    st.header("Filtros")

    filtro_estacion = st.selectbox("Estación", ["Todas"] + sorted(df[col_estacion].dropna().unique().tolist()))
    filtro_cd_cw = st.selectbox("CD/CW", ["Todas"] + sorted(df[col_cd_cw].dropna().unique().tolist()))
    filtro_metrica = st.selectbox("Métrica", metric_columns)

# ============================
# FILTRAR DATOS
# ============================
df_filtro = df.copy()

if filtro_estacion != "Todas":
    df_filtro = df_filtro[df_filtro[col_estacion] == filtro_estacion]

if filtro_cd_cw != "Todas":
    df_filtro = df_filtro[df_filtro[col_cd_cw] == filtro_cd_cw]

# ============================
# VALIDAR SI HAY DATOS
# ============================
if df_filtro.empty:
    st.warning("No hay registros para los filtros seleccionados.")
    st.stop()

# ============================
# EJEMPLO DE GRÁFICA
# ============================
st.subheader(f"Distribución de la métrica: {filtro_metrica}")

fig = px.histogram(
    df_filtro,
    x=filtro_metrica,
    nbins=20,
    title=f"Histograma de {filtro_metrica}"
)

st.plotly_chart(fig, use_container_width=True)

# Mostrar tabla filtrada
st.dataframe(df_filtro)
