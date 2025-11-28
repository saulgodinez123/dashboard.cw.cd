import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

# ===============================
# CARGA DE ARCHIVOS
# ===============================
df_cd = pd.read_csv("CD_unificado.csv")
df_cw = pd.read_csv("CW_unificado.csv")
df_limites = pd.read_excel("Limites en tablas (1).xlsx")

# Unifica data
df_cd["area"] = "CD"
df_cw["area"] = "CW"
df_all = pd.concat([df_cd, df_cw], ignore_index=True)

# ===============================
# LIMPIEZA DE TABLA DE LÍMITES
# ===============================
# Estructura esperada:
# columna0 = maquina
# columna1 = variable/métrica
# columna2 = Límite inferior
# columna3 = Límite superior

df_limites.columns = ["maquina", "variable", "LimiteInferior", "LimiteSuperior"]

# ===============================
# FILTROS
# ===============================
st.sidebar.title("Filtros")

lineas = df_all["linea"].dropna().unique()
categorias = df_all["categoria"].dropna().unique()

linea_sel = st.sidebar.selectbox("Línea", lineas)
categoria_sel = st.sidebar.selectbox("Categoría", categorias)

maquinas_filtradas = df_all[
    (df_all["linea"] == linea_sel) &
    (df_all["categoria"] == categoria_sel)
]["maquina"].dropna().unique()

maquina_sel = st.sidebar.selectbox("Máquina", maquinas_filtradas)

# Detecta métricas numéricas
metricas = [
    col for col in df_all.columns
    if col not in ["maquina", "linea", "categoria", "Date", "Time", "area"]
    and df_all[col].dtype in ["float64", "int64"]
]

metrica_sel = st.sidebar.selectbox("Métrica", metricas)

# ===============================
# RANGO DE FECHAS
# ===============================
df_all["Date"] = pd.to_datetime(df_all["Date"], errors="coerce")

fechas_validas = df_all["Date"].dropna()

fecha_min = fechas_validas.min().date()
fecha_max = fechas_validas.max().date()

rango_fechas = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max])

# ===============================
# FILTRO PRINCIPAL
# ===============================
df_filt = df_all[
    (df_all["linea"] == linea_sel) &
    (df_all["categoria"] == categoria_sel) &
    (df_all["maquina"] == maquina_sel)
].copy()

df_filt = df_filt[
    (df_filt["Date"] >= pd.to_datetime(rango_fechas[0])) &
    (df_filt["Date"] <= pd.to_datetime(rango_fechas[-1]))
]

# ===============================
# BUSCAR LÍMITES
# ===============================
limite_row = df_limites[
    (df_limites["maquina"] == maquina_sel) &
    (df_limites["variable"] == metrica_sel)
]

# ===============================
# TÍTULO
# ===============================
st.title(f"Dashboard – {linea_sel} / {categoria_sel} / {maquina_sel}")
st.subheader(f"Métrica: **{metrica_sel}**")

if df_filt.empty:
    st.error("⚠ No hay datos con estos filtros.")
    st.stop()

# ===============================
# GRAFICO PRINCIPAL CON LÍMITES
# ===============================
fig1, ax1 = plt.subplots()
ax1.plot(df_filt["Date"], df_filt[metrica_sel], label="Valor")

# Agrega líneas de límites si existen
if not limite_row.empty:
    ax1.axhline(limite_row.iloc[0]["LimiteSuperior"], color="red", linestyle="--", label="Límite Superior")
    ax1.axhline(limite_row.iloc[0]["LimiteInferior"], color="green", linestyle="--", label="Límite Inferior")

ax1.set_title("Tendencia de la métrica")
ax1.set_xlabel("Fecha")
ax1.set_ylabel(metrica_sel)
ax1.legend()
st.pyplot(fig1)

# ===============================
# GRAFICO 2 – HISTOGRAMA
# ===============================
fig2, ax2 = plt.subplots()
ax2.hist(df_filt[metrica_sel], bins=20)
ax2.set_title("Distribución de valores (Histograma)")
ax2.set_xlabel(metrica_sel)
ax2.set_ylabel("Frecuencia")
st.pyplot(fig2)

# ===============================
# GRAFICO 3 – BOXPLOT
# ===============================
fig3, ax3 = plt.subplots()
ax3.boxplot(df_filt[metrica_sel].dropna())
ax3.set_title("Variabilidad (Boxplot)")
ax3.set_ylabel(metrica_sel)
st.pyplot(fig3)

# ===============================
# GRAFICO 4 – DISPERSIÓN VS TIEMPO
# ===============================
fig4, ax4 = plt.subplots()
ax4.scatter(df_filt["Date"], df_filt[metrica_sel], alpha=0.7)
ax4.set_title("Dispersión de mediciones")
ax4.set_xlabel("Fecha")
ax4.set_ylabel(metrica_sel)
st.pyplot(fig4)

# ===============================
# TABLA FINAL
# ===============================
st.subheader("Datos filtrados")
st.dataframe(df_filt[["Date", "Time", "maquina", "linea", "categoria", metrica_sel]])
