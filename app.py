import streamlit as st
import pandas as pd
import numpy as np

# ======================================================
# 1. CARGA DE DATOS
# ======================================================
def cargar_datos(file):
    df = pd.read_excel(file)
    return df


# ======================================================
# 2. LIMPIEZA GENERAL
# ======================================================
def limpiar_dataframe(df):
    df = df.copy()
    df.columns = df.columns.str.strip()
    return df


# ======================================================
# 3. CÁLCULO DE LÍMITES
# ======================================================
def calcular_limites(df, columna, lsl, usl):
    df = df.copy()
    df["Fuera_de_Limites"] = (df[columna] < lsl) | (df[columna] > usl)
    return df


# ======================================================
# 4. PORCENTAJE FUERA DE LÍMITES (FILTRADO POR CATEGORÍA)
# ======================================================
def porcentaje_fuera(df, columna_categoria, columna_valor, lsl, usl):
    df = df.copy()
    
    df["Fuera"] = (df[columna_valor] < lsl) | (df[columna_valor] > usl)

    resumen = (
        df.groupby(columna_categoria)
        .agg(
            Total=("Fuera", "count"),
            Fuera_Limite=("Fuera", "sum")
        )
        .assign(Porcentaje=lambda x: x["Fuera_Limite"] / x["Total"])
    )

    return resumen.reset_index()


# ======================================================
# 5. PIPELINE PRINCIPAL
# ======================================================
def ejecutar_pipeline(file):
    df = cargar_datos(file)
    df = limpiar_dataframe(df)

    return df


# ======================================================
# 6. INTERFAZ STREAMLIT (DASHBOARD)
# ======================================================

st.title("Dashboard de Control de Proceso")

uploaded = st.file_uploader("Sube el archivo Excel con los datos", type=["xlsx"])

if uploaded:
    st.success("Archivo cargado correctamente ✔️")

    df = ejecutar_pipeline(uploaded)

    st.subheader("Vista previa del dataset")
    st.dataframe(df.head())

    # Selección de variables numéricas
    variables_numericas = df.select_dtypes(include=np.number).columns.tolist()

    st.subheader("Configuración del análisis")

    categoria = st.selectbox("Selecciona la categoría (agrupación):", df.columns)

    variable = st.selectbox("Selecciona la variable a analizar:", variables_numericas)

    col1, col2 = st.columns(2)
    with col1:
        lsl = st.number_input("LSL (límite inferior)", value=float(df[variable].min()))
    with col2:
        usl = st.number_input("USL (límite superior)", value=float(df[variable].max()))

    # Cálculo de porcentaje fuera
    resultado = porcentaje_fuera(df, categoria, variable, lsl, usl)

    st.subheader("Porcentaje fuera de límites")
    st.dataframe(resultado)

    # Guardar resultados
    nombre_salida = "resultados_proceso.xlsx"
    resultado.to_excel(nombre_salida, index=False)

    with open(nombre_salida, "rb") as f:
        st.download_button(
            label="📥 Descargar resultados",
            data=f,
            file_name=nombre_salida,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # GRÁFICOS
    st.subheader("Distribución de valores")
    st.bar_chart(df[variable])

    st.subheader("Valores fuera de límite por categoría")
    st.bar_chart(resultado.set_index(categoria)["Porcentaje"])

else:
    st.info("Por favor sube un archivo Excel para comenzar.")
