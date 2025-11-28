import streamlit as st
import pandas as pd
import plotly.express as px

# -------------------------------------------------------
# 1) CARGA DE DATOS
# -------------------------------------------------------

# Archivo con datos reales (por ejemplo CW.xlsx)
df = pd.read_excel("CW.xlsx")

# Archivo con los límites (como el ejemplo que diste)
df_limits = pd.read_excel("Tabla_Limites.xlsx")

# -------------------------------------------------------
# 2) LIMPIEZA Y FORMATO
# -------------------------------------------------------
# Asegurar nombres consistentes
df_limits.columns = ["Maquina", "Variable", "Limite_inferior", "Limite_superior"]

# -------------------------------------------------------
# 3) SIDEBAR: Selección de Máquina
# -------------------------------------------------------
st.sidebar.header("Filtros")

maquinas = sorted(df_limits["Maquina"].unique())
machine_selected = st.sidebar.selectbox("Selecciona la máquina:", maquinas)

# -------------------------------------------------------
# 4) VARIABLES DISPONIBLES PARA ESA MÁQUINA
# -------------------------------------------------------
variables_disponibles = df_limits[df_limits["Maquina"] == machine_selected]["Variable"].unique()

variable_selected = st.sidebar.selectbox("Selecciona la variable:", variables_disponibles)

# -------------------------------------------------------
# 5) OBTENER LÍMITES PARA LA VARIABLE SELECCIONADA
# -------------------------------------------------------
lim_inf = df_limits[
    (df_limits["Maquina"] == machine_selected) & 
    (df_limits["Variable"] == variable_selected)
]["Limite_inferior"].values[0]

lim_sup = df_limits[
    (df_limits["Maquina"] == machine_selected) & 
    (df_limits["Variable"] == variable_selected)
]["Limite_superior"].values[0]

# -------------------------------------------------------
# 6) FILTRAR DATOS REALES DEL CW
# -------------------------------------------------------
df_filtered = df[df["variable"] == variable_selected]

# -------------------------------------------------------
# 7) GRAFICAR DATOS + LÍMITES
# -------------------------------------------------------
st.subheader(f"Variable: {variable_selected} — Máquina: {machine_selected}")

if df_filtered.empty:
    st.warning("No hay datos para esta variable en CW.xlsx")
else:
    fig = px.line(df_filtered, x="timestamp", y="value", title=f"Comportamiento de {variable_selected}")

    # Agregar límites
    fig.add_hline(y=lim_inf, line_dash="dot", annotation_text="Límite inferior", annotation_position="bottom left")
    fig.add_hline(y=lim_sup, line_dash="dot", annotation_text="Límite superior", annotation_position="top left")

    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------
    # 8) SEMÁFORO
    # -------------------------------------------------------
    fuera_limites = df_filtered[(df_filtered["value"] < lim_inf) | (df_filtered["value"] > lim_sup)]

    if fuera_limites.empty:
        st.success("✅ Todos los valores están dentro de los límites")
    else:
        st.error(f"⚠️ {len(fuera_limites)} valores fuera de límites detectados")

        st.dataframe(fuera_limites)
