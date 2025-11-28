import streamlit as st
import pandas as pd

# Cargar archivos
df_cd = pd.read_csv('CD_unificado.csv')
df_cw = pd.read_csv('CW_unificado.csv')
df_limites = pd.read_excel('Limites en tablas (1).xlsx')

# Mostrar en streamlit
st.title("Visualización de Archivos de Producción")

st.header("Producción CD (CSV)")
st.dataframe(df_cd)

st.header("Producción CW (CSV)")
st.dataframe(df_cw)

st.header("Limites (XLSX)")
st.dataframe(df_limites)


import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Lee las bases, ajusta tus rutas
df_cd = pd.read_csv('CD_unificado.csv')
df_cw = pd.read_csv('CW_unificado.csv')
df_limites = pd.read_excel('Limites en tablas (1).xlsx')

# Unifica área para todo facilitar
df_cd["area"] = "CD"
df_cw["area"] = "CW"
df_all = pd.concat([df_cd, df_cw], ignore_index=True)

# Filtros principales
lineas = df_all['linea'].unique()
areas = df_all['area'].unique()
maquinas = df_all['maquina'].unique()
metricas = [c for c in df_all.columns if c not in ['maquina', 'linea', 'categoria', 'Date', 'Time', 'area']]

st.sidebar.title("Filtros")
linea_sel = st.sidebar.selectbox("Línea de producción", lineas)
area_sel = st.sidebar.selectbox("Área", areas)
maquina_sel = st.sidebar.selectbox("Máquina", df_all[(df_all['linea'] == linea_sel) & (df_all['area'] == area_sel)]['maquina'].unique())
metrica_sel = st.sidebar.selectbox("Métrica", metricas)

# Filtra la data
df_filt = df_all[
    (df_all['linea'] == linea_sel) &
    (df_all['area'] == area_sel) &
    (df_all['maquina'] == maquina_sel)
]

# Busca límites (ajusta nombres según tu excel)
limite_row = df_limites[
    (df_limites['maquina'] == maquina_sel) &
    (df_limites['area'] == area_sel) &
    (df_limites['linea'] == linea_sel)
].iloc[0]

# Visualización con límites
st.header(f"{linea_sel} / {area_sel} / {maquina_sel}")
st.write(f"Métrica: {metrica_sel}")

fig, ax = plt.subplots()
ax.plot(df_filt["Date"], df_filt[metrica_sel], label=metrica_sel)
ax.axhline(limite_row['LimiteSuperior'], color='red', linestyle='--', label="Limite superior")
ax.axhline(limite_row['LimiteInferior'], color='green', linestyle=':', label="Limite inferior")
ax.legend()
ax.set_xlabel("Fecha")
ax.set_ylabel(metrica_sel)
st.pyplot(fig)

# Visualiza la data filtrada, KPIs etc
st.dataframe(df_filt[[metrica_sel, "Date", "Time", "maquina", "linea", "categoria"]])
