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
    limites = pd.read_excel("Limites.xlsx")  # Renómbralo según el archivo real
    return cw, cd, limites

cw, cd, limites = load_data()

st.title("📊 Dashboard CD / CW con Límites")


#-----------------------------------------------------------
# LIMPIEZA
#-----------------------------------------------------------

def clean_datetime(df):
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if "Time" in df.columns:
        df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    return df

cw = clean_datetime(cw)
cd = clean_datetime(cd)


#-----------------------------------------------------------
# SELECCIÓN DE DATASET
#-----------------------------------------------------------
st.sidebar.header("Filtros")
dataset = st.sidebar.selectbox("Seleccionar dataset", ["CW", "CD"])
df = cw if dataset == "CW" else cd


#-----------------------------------------------------------
# FILTROS DINÁMICOS
#-----------------------------------------------------------

# Filtro Model
if "Model" in df.columns:
    modelos = df["Model"].dropna().unique().tolist()
    sel_model = st.sidebar.multiselect("Modelo", modelos)
    if sel_model:
        df = df[df["Model"].isin(sel_model)]

# Filtro máquina en CD
if "maquina" in df.columns:
    maquinas = df["maquina"].dropna().unique().tolist()
    sel_maq = st.sidebar.multiselect("Máquina", maquinas)
    if sel_maq:
        df = df[df["maquina"].isin(sel_maq)]

# Filtro fecha
if "Date" in df.columns:
    df = df.dropna(subset=["Date"])

    if not df.empty:
        min_d = df["Date"].min().date()
        max_d = df["Date"].max().date()

        fecha = st.sidebar.date_input(
            "Rango de fecha",
            (min_d, max_d)
        )

        if isinstance(fecha, tuple) and len(fecha) == 2:
            df = df[
                (df["Date"].dt.date >= fecha[0])
                & (df["Date"].dt.date <= fecha[1])
            ]


#-----------------------------------------------------------
# PARÁMETROS NUMÉRICOS
#-----------------------------------------------------------
parametros_numericos = df.select_dtypes(include="number").columns.tolist()

if not parametros_numericos:
    st.error("No hay parámetros numéricos en este dataset")
    st.stop()

param = st.selectbox("Selecciona un parámetro para graficar", parametros_numericos)


#-----------------------------------------------------------
# LECTURA INTELIGENTE DE LÍMITES
#-----------------------------------------------------------

def get_limits(param):
    # Buscar columna que contiene el nombre del parámetro
    posibles_columnas_nombre = ["Parametro", "Parameter", "Variable", "Test", "Nombre"]

    col_param = None
    for c in posibles_columnas_nombre:
        if c in limites.columns:
            col_param = c
            break

    if col_param is None:
        st.error("No se encontró una columna de nombre de parámetro en el archivo de límites.")
        return None, None

    # Buscar columnas de límites
    posibles_lsl = ["LSL", "Limite inferior", "Lower Limit", "Min", "LSL Value"]
    posibles_usl = ["USL", "Limite superior", "Upper Limit", "Max", "USL Value"]

    col_lsl = next((c for c in posibles_lsl if c in limites.columns), None)
    col_usl = next((c for c in posibles_usl if c in limites.columns), None)

    if col_lsl is None or col_usl is None:
        st.error("No se encontraron columnas de límites en el archivo.")
        return None, None

    # Buscar coincidencia exacta del parámetro
    fila = limites[limites[col_param] == param]

    if fila.empty:
        return None, None

    return float(fila[col_lsl].iloc[0]), float(fila[col_usl].iloc[0])


lsl, usl = get_limits(param)


#-----------------------------------------------------------
# KPIs
#-----------------------------------------------------------
col1, col2, col3 = st.columns(3)
col1.metric("Promedio", f"{df[param].mean():.2f}")
col2.metric("Mínimo", f"{df[param].min():.2f}")
col3.metric("Máximo", f"{df[param].max():.2f}")


#-----------------------------------------------------------
# GRÁFICA — SERIE DE TIEMPO
#-----------------------------------------------------------
st.subheader("📈 Tendencia del parámetro")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df["Date"] if "Date" in df.columns else df.index,
    y=df[param],
    mode="lines+markers",
    name=param
))

# Dibujar límites
if lsl is not None:
    fig.add_hline(y=lsl, line_dash="dot", line_color="red", annotation_text="LSL")

if usl is not None:
    fig.add_hline(y=usl, line_dash="dot", line_color="red", annotation_text="USL")

fig.update_layout(
    height=500,
    xaxis_title="Fecha",
    yaxis_title=param
)

st.plotly_chart(fig, use_container_width=True)


#-----------------------------------------------------------
# HISTOGRAMA
#-----------------------------------------------------------
st.subheader("📊 Distribución del parámetro")

hist = px.histogram(df, x=param, nbins=50)

if lsl is not None:
    hist.add_vline(x=lsl, line_dash="dot", line_color="red")
if usl is not None:
    hist.add_vline(x=usl, line_dash="dot", line_color="red")

st.plotly_chart(hist, use_container_width=True)


#-----------------------------------------------------------
# TABLA FINAL
#-----------------------------------------------------------
st.subheader("📄 Datos filtrados")
st.dataframe(df.tail(300))
