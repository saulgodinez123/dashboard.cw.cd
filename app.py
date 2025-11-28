import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

#-----------------------------------------------------------
# CARGA DE ARCHIVOS
#-----------------------------------------------------------

@st.cache_data
def load_data():
    cw = pd.read_csv("CW_unificado.csv", encoding="latin-1")
    cd = pd.read_csv("CD_unificado.csv", encoding="latin-1")
    limites = pd.read_excel("Limites en tablas (1).xlsx")
    return cw, cd, limites

cw, cd, limites = load_data()

st.title("📊 Dashboard CD / CW con Límites de Parámetros")

#-----------------------------------------------------------
# LIMPIEZA BÁSICA
#-----------------------------------------------------------
# Convertir fechas
for df in [cw, cd]:
    for col in ["Date", "Time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

#-----------------------------------------------------------
# SELECCIÓN DE DATASET
#-----------------------------------------------------------
st.sidebar.header("Filtros")
dataset = st.sidebar.selectbox("Seleccionar dataset", ["CW", "CD"])

df = cw if dataset == "CW" else cd

#-----------------------------------------------------------
# FILTROS DINÁMICOS SEGÚN COLUMNAS EXISTENTES
#-----------------------------------------------------------

if "Model" in df.columns:
    modelo = st.sidebar.multiselect("Modelo", df["Model"].dropna().unique())
    if modelo:
        df = df[df["Model"].isin(modelo)]

if "maquina" in df.columns:
    maq = st.sidebar.multiselect("Máquina", df["maquina"].dropna().unique())
    if maq:
        df = df[df["maquina"].isin(maq)]

# Filtrar por fechas (si existen)
if "Date" in df.columns:
    min_d = df["Date"].min()
    max_d = df["Date"].max()
    fecha_filtro = st.sidebar.date_input("Rango de fecha", [min_d, max_d])
    df = df[(df["Date"] >= pd.to_datetime(fecha_filtro[0])) &
            (df["Date"] <= pd.to_datetime(fecha_filtro[1]))]

#-----------------------------------------------------------
# SELECCIÓN DE PARÁMETRO
#-----------------------------------------------------------

parametros_numericos = df.select_dtypes(include="number").columns.tolist()

param = st.selectbox("Selecciona un parámetro para graficar", parametros_numericos)

#-----------------------------------------------------------
# OBTENER LÍMITES DESDE EL EXCEL
#-----------------------------------------------------------

def get_limits(param):
    """Busca límites del parámetro en el Excel"""
    row = limites[limites["Parametro"] == param]

    if row.empty:
        return None, None

    try:
        low = float(row["LSL"].values[0])
        high = float(row["USL"].values[0])
    except:
        low, high = None, None

    return low, high

lsl, usl = get_limits(param)

#-----------------------------------------------------------
# MÉTRICAS RÁPIDAS
#-----------------------------------------------------------

col1, col2, col3 = st.columns(3)
col1.metric("Promedio", f"{df[param].mean():.2f}")
col2.metric("Mínimo", f"{df[param].min():.2f}")
col3.metric("Máximo", f"{df[param].max():.2f}")

#-----------------------------------------------------------
# GRAFICAR
#-----------------------------------------------------------

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["Date"] if "Date" in df.columns else df.index,
    y=df[param],
    mode="lines+markers",
    name=param,
    line=dict(width=1)
))

# LÍMITES EN LA GRÁFICA
if lsl is not None:
    fig.add_hline(y=lsl, line_dash="dot", line_color="red", annotation_text="LSL")

if usl is not None:
    fig.add_hline(y=usl, line_dash="dot", line_color="red", annotation_text="USL")

fig.update_layout(
    title=f"Evolución del parámetro: {param}",
    xaxis_title="Fecha",
    yaxis_title=param,
    height=500
)

st.plotly_chart(fig, use_container_width=True)

#-----------------------------------------------------------
# HISTOGRAMA
#-----------------------------------------------------------

st.subheader("Distribución del Parámetro")

hist = px.histogram(df, x=param, nbins=50)

if lsl is not None:
    hist.add_vline(x=lsl, line_dash="dot", line_color="red")

if usl is not None:
    hist.add_vline(x=usl, line_dash="dot", line_color="red")

st.plotly_chart(hist, use_container_width=True)

#-----------------------------------------------------------
# TABLA FINAL
#-----------------------------------------------------------

st.subheader("Datos filtrados")
st.dataframe(df.tail(300))
