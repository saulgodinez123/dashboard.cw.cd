import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# =============================
#      CARGA DE ARCHIVOS
# =============================

st.title("📊 Dashboard de Límites CD / CW")

# Cargar bases originales
df = pd.read_excel("CD_unificado.xlsx")
df_limites = pd.read_excel("limites.xlsx")

# Normalizar nombres
df.columns = df.columns.str.strip()
df_limites.columns = df_limites.columns.str.strip()

# =============================
#   DETECTAR COLUMNA DE MÁQUINA EN LÍMITES
# =============================

col_maquina_lim = None
for col in df_limites.columns:
    # Detecta si una columna contiene nombres como:
    # CW, CD, FVT7_CW, FVT100_CD, etc.
    if df_limites[col].astype(str).str.contains("CW|CD|FVT", case=False).any():
        col_maquina_lim = col
        break

if col_maquina_lim is None:
    st.error("❌ No se encontró columna que contenga las máquinas en el archivo de límites.")
    st.stop()

st.sidebar.markdown("### Tipo de datos")
tipo_datos = st.sidebar.selectbox("Selecciona tipo:", ["CD", "CW"])

# =============================
#   SLIDERS DEPENDIENTES
# =============================

st.sidebar.markdown("### Máquina")
maquinas = sorted(df["maquina"].dropna().unique())
maquina = st.sidebar.selectbox("Selecciona máquina:", maquinas)

# Variables dentro de esa máquina
st.sidebar.markdown("### Variable")
variables = sorted(df[df["maquina"] == maquina]["variable"].dropna().unique())
variable = st.sidebar.selectbox("Selecciona variable:", variables)

st.markdown("## 📊 Dashboard de Límites")

# =============================
#   FILTRAR DATOS PRINCIPALES
# =============================

df_v = df[(df["maquina"] == maquina) & (df["variable"] == variable)].copy()
df_v = df_v.sort_values("fecha")

if df_v.empty:
    st.error("⚠ No hay datos disponibles para esta máquina y variable.")
    st.stop()

# =============================
#   FILTRAR LÍMITES
# =============================

df_lims = df_limites[
    (df_limites[col_maquina_lim].astype(str).str.strip() == maquina.strip()) &
    (df_limites["Variable"].astype(str).str.strip() == variable.strip())
]

if df_lims.empty:
    st.error("⚠ No se encontraron límites para esta máquina y variable.")
    st.stop()

lim_inf = df_lims["Limite inferior"].values[0]
lim_sup = df_lims["Limite superior"].values[0]

# =============================
#   CÁLCULO DE KPIs
# =============================

fuera = df_v[(df_v["valor"] < lim_inf) | (df_v["valor"] > lim_sup)]
pct_fuera = (len(fuera) / len(df_v)) * 100 if len(df_v) > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Promedio", f"{df_v['valor'].mean():.2f}")
col2.metric("Último valor", f"{df_v['valor'].iloc[-1]:.2f}")
col3.metric("% Fuera de límites", f"{pct_fuera:.1f}%")

# =============================
#         GRÁFICA
# =============================

st.markdown("### 📈 Gráfica de tendencia")

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(df_v["fecha"], df_v["valor"], label="Valor")
ax.axhline(lim_inf, color="red", linestyle="--", label="Límite inferior")
ax.axhline(lim_sup, color="red", linestyle="--", label="Límite superior")
ax.set_xlabel("Fecha")
ax.set_ylabel("Valor")
ax.legend()
st.pyplot(fig)

# =============================
#   TABLA DE DATOS
# =============================

st.markdown("### 📋 Datos filtrados")
st.dataframe(df_v)

# =============================
#   TABLA DE LÍMITES
# =============================

st.markdown("### 📘 Límites aplicados")
st.dataframe(df_lims)
