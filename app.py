import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard CD/CW", layout="wide")

# --------------------------------------------------------
# 1️⃣ CARGA DE DATOS
# --------------------------------------------------------
@st.cache_data
def load_data():
    df_all = pd.read_excel("MANT.xlsx")
    df_lim = pd.read_excel("LIM.xlsx")
    return df_all, df_lim

df_all, df_limites = load_data()

st.title("📊 Dashboard CD / CW")

# --------------------------------------------------------
# 2️⃣ LIMPIEZA BÁSICA DE DATAFRAMES
# --------------------------------------------------------
df_all.columns = df_all.columns.str.strip()
df_limites.columns = df_limites.columns.str.strip()

# Asegurar nombres correctos en límites
df_limites.columns = ["maquina", "variable", "LimiteInferior", "LimiteSuperior"]

# --------------------------------------------------------
# 3️⃣ FILTROS LATERALES
# --------------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    area = st.selectbox("Área:", ["Todas"] + sorted(df_all["area"].dropna().unique().tolist()))

with col2:
    maquina = st.selectbox("Máquina:", ["Todas"] + sorted(df_all["maquina"].dropna().unique().tolist()))

with col3:
    variable_usuario = st.selectbox("Variable:", ["Todas"] + sorted(df_all["Variable"].dropna().unique().tolist()))

# --------------------------------------------------------
# 4️⃣ DETECCIÓN DE MÉTRICAS VÁLIDAS
# --------------------------------------------------------
metricas = []

for col in df_all.columns:
    if col in ["maquina", "linea", "categoria", "Date", "Time", "area", "Variable"]:
        continue
    
    if pd.api.types.is_numeric_dtype(df_all[col]):
        if df_all[col].notna().sum() > 5 and df_all[col].nunique() > 1:
            metricas.append(col)

if not metricas:
    st.error("❌ No se encontraron métricas numéricas válidas.")
    st.stop()

metrica = st.selectbox("Métrica:", metricas)

# --------------------------------------------------------
# 5️⃣ APLICAR FILTROS AL DATAFRAME
# --------------------------------------------------------
df_filt = df_all.copy()

if area != "Todas":
    df_filt = df_filt[df_filt["area"] == area]

if maquina != "Todas":
    df_filt = df_filt[df_filt["maquina"] == maquina]

if variable_usuario != "Todas":
    df_filt = df_filt[df_filt["Variable"] == variable_usuario]

if df_filt.empty:
    st.warning("⚠️ No hay registros para los filtros seleccionados.")
    st.stop()

# --------------------------------------------------------
# 6️⃣ UNIR MÉTRICOS CON LIMITES CORRECTOS
# --------------------------------------------------------
df_merge = pd.merge(
    df_filt,
    df_limites,
    left_on=["maquina", "Variable"],
    right_on=["maquina", "variable"],
    how="left"
)

# --------------------------------------------------------
# 7️⃣ GRÁFICA PRINCIPAL (MÉTRICA + LÍMITES)
# --------------------------------------------------------
st.subheader(f"📈 Gráfica de {metrica}")

fig = go.Figure()

# Línea real
fig.add_trace(go.Scatter(
    x=df_merge["Date"], 
    y=df_merge[metrica],
    mode="lines+markers",
    name=metrica,
    line=dict(width=2)
))

# Límites
if df_merge["LimiteInferior"].notna().any():
    fig.add_trace(go.Scatter(
        x=df_merge["Date"],
        y=df_merge["LimiteInferior"],
        mode="lines",
        name="Límite Inferior",
        line=dict(dash="dash")
    ))

if df_merge["LimiteSuperior"].notna().any():
    fig.add_trace(go.Scatter(
        x=df_merge["Date"],
        y=df_merge["LimiteSuperior"],
        mode="lines",
        name="Límite Superior",
        line=dict(dash="dash")
    ))

fig.update_layout(
    xaxis_title="Fecha",
    yaxis_title=metrica,
    height=500,
    template="plotly_white"
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------
# 8️⃣ TABLA FILTRADA
# --------------------------------------------------------
st.subheader("📄 Datos filtrados")
st.dataframe(df_filt, use_container_width=True)

