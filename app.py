import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Cargar los archivos
df_cd = pd.read_csv('CD_unificado.csv')
df_cw = pd.read_csv('CW_unificado.csv')
df_limites = pd.read_excel('Limites en tablas (1).xlsx')

# Unifica todos los datos y agrega columna 'area'
df_cd["area"] = "CD"
df_cw["area"] = "CW"
df_all = pd.concat([df_cd, df_cw], ignore_index=True)

# Obtén filtros únicos
lineas = df_all['linea'].dropna().unique()
categorias = df_all['categoria'].dropna().unique()
maquinas = df_all['maquina'].dropna().unique()
metricas = [col for col in df_all.columns if col not in 
            ["maquina", "linea", "categoria", "Date", "Time", "area"] and df_all[col].dtype in ['float64', 'int64']]

st.sidebar.title("Filtros")
linea_sel = st.sidebar.selectbox("Línea de producción", lineas)
categoria_sel = st.sidebar.selectbox("Área/Categoría", categorias)
maquinas_filtradas = df_all[(df_all['linea'] == linea_sel) & (df_all['categoria'] == categoria_sel)]['maquina'].dropna().unique()
maquina_sel = st.sidebar.selectbox("Máquina", maquinas_filtradas)
metrica_sel = st.sidebar.selectbox("Métrica", metricas)
fechas = pd.to_datetime(df_all['Date'], errors='coerce').dropna()
fecha_min, fecha_max = fechas.min(), fechas.max()
rango_fechas = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max])

# Filtra data
df_filt = df_all[
    (df_all['linea'] == linea_sel) &
    (df_all['categoria'] == categoria_sel) &
    (df_all['maquina'] == maquina_sel)
]
df_filt["Date"] = pd.to_datetime(df_filt["Date"], errors='coerce')
df_filt = df_filt[(df_filt["Date"] >= pd.to_datetime(rango_fechas[0])) & (df_filt["Date"] <= pd.to_datetime(rango_fechas[-1]))]

# Buscar límites
limite_row = df_limites[
    (df_limites['maquina'] == maquina_sel) &
    (df_limites['categoria'] == categoria_sel) &
    (df_limites['linea'] == linea_sel)
]

st.title(f"Dashboard: {linea_sel} / {categoria_sel} / {maquina_sel}")
st.subheader(f"Métrica: {metrica_sel}")

# Gráfico y visualización de límites
if not df_filt.empty and not limite_row.empty:
    fig, ax = plt.subplots()
    ax.plot(df_filt["Date"], df_filt[metrica_sel], label=metrica_sel)
    ax.axhline(limite_row.iloc[0]['LimiteSuperior'], color='red', linestyle='--', label="Límite superior")
    ax.axhline(limite_row.iloc[0]['LimiteInferior'], color='green', linestyle=':', label="Límite inferior")
    ax.set_xlabel("Fecha")
    ax.set_ylabel(metrica_sel)
    ax.legend()
    st.pyplot(fig)
else:
    st.warning("No hay datos o límites disponibles para este filtro.")

st.dataframe(df_filt[["Date", "Time", "maquina", "linea", "categoria", metrica_sel]])
