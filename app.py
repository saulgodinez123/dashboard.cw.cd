import streamlit as st
import pandas as pd
import altair as alt

# ====================================================
# CARGA DE DATOS
# ====================================================

@st.cache_data
def load_data():
    # Cargar CD y CW
    df_cd = pd.read_csv("CD_unificado.csv")
    df_cw = pd.read_csv("CW_unificado.csv")

    df_cd["tipo"] = "CD"
    df_cw["tipo"] = "CW"

    df = pd.concat([df_cd, df_cw], ignore_index=True)

    # Estandarizar nombres de columnas
    df.columns = df.columns.str.lower()

    # Asegurar nombres esperados
    # Columnas mínimas necesarias: maquina, variable, valor, timestamp, tipo
    expected_cols = ["maquina", "variable", "valor", "timestamp", "tipo"]
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        st.error(f"Faltan columnas en los CSV: {missing}")
        st.stop()

    # Convertir timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    # Cargar límites
    lim = pd.read_excel("Limites en tablas (2).xlsx")
    lim.columns = lim.columns.str.lower()

    # Columnas mínimas en límites
    expected_lim = ["maquina", "variable", "lim_inf", "lim_sup", "tipo"]
    missing_lim = [c for c in expected_lim if c not in lim.columns]
    if missing_lim:
        st.error(f"Faltan columnas en el archivo de límites: {missing_lim}")
        st.stop()

    return df, lim


df, lim = load_data()

# ====================================================
# INTERFAZ DE USUARIO
# ====================================================

st.title("Dashboard CD & CW – Líneas de Producción")

st.markdown("""
Este dashboard permite visualizar variables de proceso para las líneas CD y CW,
además de sus límites de control configurados.
""")

# -------- Selección CD o CW (múltiple) --------
tipo_select = st.multiselect(
    "Selecciona tipo (CD y/o CW):",
    options=["CD", "CW"],
    default=["CD", "CW"]
)

df_tipo = df[df["tipo"].isin(tipo_select)]

# -------- Selección de máquina --------
maquinas = sorted(df_tipo["maquina"].unique())

if len(maquinas) == 0:
    st.error("No hay máquinas disponibles para los filtros seleccionados.")
    st.stop()

maquina_select = st.selectbox("Selecciona la máquina:", maquinas)

df_maquina = df_tipo[df_tipo["maquina"] == maquina_select]

# -------- Selección automática de variables --------
variables_disponibles = sorted(df_maquina["variable"].unique())

variables_select = st.multiselect(
    "Variables a visualizar:",
    options=variables_disponibles,
    default=variables_disponibles   # ACTIVAR TODAS AUTOMÁTICAMENTE
)

df_vars = df_maquina[df_maquina["variable"].isin(variables_select)]

# ====================================================
# GRÁFICA
# ====================================================
st.subheader("Gráfica de variables seleccionadas")

if df_vars.empty:
    st.warning("No hay datos disponibles con la selección actual.")
else:
    chart = alt.Chart(df_vars).mark_line().encode(
        x=alt.X("timestamp:T", title="Fecha/Hora"),
        y=alt.Y("valor:Q", title="Valor"),
        color="variable:N",
        tooltip=["timestamp:T", "variable:N", "valor:Q"]
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

# ====================================================
# MOSTRAR LÍMITES
# ====================================================
st.subheader("Límites de Control")

lim_sel = lim[
    (lim["maquina"] == maquina_select) &
    (lim["variable"].isin(variables_select)) &
    (lim["tipo"].isin(tipo_select))
]

if len(lim_sel) > 0:
    st.dataframe(lim_sel)
else:
    st.info("No hay límites configurados para esta selección.")

# ====================================================
# DESCARGA DE DATOS FILTRADOS
# ====================================================
st.subheader("Descargar datos filtrados")

def convert_df(df):
    return df.to_csv(index=False).encode("utf-8")

csv_download = convert_df(df_vars)

st.download_button(
    label="📥 Descargar CSV",
    data=csv_download,
    file_name=f"{maquina_select}_datos_filtrados.csv",
    mime="text/csv"
)

# ====================================================
# FIN DEL DASHBOARD
# ====================================================

