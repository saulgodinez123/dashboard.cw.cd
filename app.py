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
