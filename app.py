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
# FILTROS DINÁMICOS SEGÚN COLUMNAS EXISTENTES
#-----------------------------------------------------------

# FILTRO MODEL
if "Model" in df.columns:
    modelos = df["Model"].dropna().unique().tolist()
    selected_model = st.sidebar.multiselect("Modelo", modelos)
    if selected_model:
        df = df[df["Model"].isin(selected_model)]

# FILTRO MÁQUINA (solo CD)
if "maquina" in df.columns:
    maquinas = df["maquina"].dropna().unique().tolist()
    selected_maq = st.sidebar.multiselect("Máquina", maquinas)
    if selected_maq:
        df = df[df["maquina"].isin(selected_maq)]

# FILTRO FECHA
if "Date" in df.columns:

    # Convertir y quitar NaT
    df = df.dropna(subset=["Date"])

    if df.empty:
        st.warning("No hay fechas válidas en este dataset.")
    else:
        # Asegurar formato date()
        min_d = df["Date"].min().date()
        max_d = df["Date"].max().date()

        fecha_filtro = st.sidebar.date_input(
            "Rango de fecha",
            (min_d, max_d)
        )

        # Aplicar filtro date_input (siempre regresa tupla)
        if isinstance(fecha_filtro, tuple) and len(fecha_filtro) == 2:
            start_date, end_date = fecha_filtro
            df = df[
                (df["Date"].dt.date >= start_date) &
                (df["Date"].dt.date <= end_date)
            ]


#-----------------------------------------------------------
# SELECCIÓN DE PARÁMETRO
#-----------------------------------------------------------
parametros_numericos = df.select_dtypes(include="number").columns.tolist()

if not parametros_numericos:
    st.error("No hay parámetros numéricos disponibles para graficar.")
    st.stop()

param = st.selectbox("Selecciona un parámetro para graficar", parametros_numericos)


#-----------------------------------------------------------
# OBTENER LÍMITES DESDE EL EXCEL
#-----------------------------------------------------------
def get_limits(param):
    row = limites[limites["Parametro"] == param]
    if row.empty:
        return None, None

    try:
        lsl = float(row["LSL"].values[0])
        usl = float(row["USL"].values[0])
    except:
        lsl, usl = None, None

    return lsl, usl

lsl, usl = get_limits(param)


#-----------------------------------------------------------
# KPIs
#-----------------------------------------------------------
col1, col2, col3 = st.columns(3)
col1.metric("Promedio", f"{df[param].mean():.2f}")
col2.metric("Mínimo", f"{df[param].min():.2f}")
col3.metric("Máximo", f"{df[param].max():.2f}")


#-----------------------------------------------------------
# GRÁFICA SERIES DE TIEMPO
#-----------------------------------------------------------
st.subheader("📈 Tendencia del parámetro")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df["Date"] if "Date" in df.columns else df.index,
    y=df[param],
    mode="lines+markers",
    name=param
))

# Límites
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
