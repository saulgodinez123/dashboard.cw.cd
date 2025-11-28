import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard CD/CW", layout="wide")

# --------------------------------------
# FUNCIÓN PARA DETECTAR NOMBRES DE COLUMNAS
# --------------------------------------
def detectar_columna(posibles, columnas):
    for p in posibles:
        p = p.lower()
        for col in columnas:
            if col.lower() == p:
                return col
    return None


# --------------------------------------
# CARGA DE ARCHIVOS
# --------------------------------------
@st.cache_data
def load_data():
    df_cd = pd.read_csv("CD_unificado.csv")
    df_cw = pd.read_csv("CW_unificado.csv")
    lim = pd.read_excel("Limites en tablas (2).xlsx")

    # Detectamos nombres reales de columnas
    columnas_cd = df_cd.columns
    columnas_cw = df_cw.columns

    col_maquina = detectar_columna(["maquina", "machine", "equipo"], columnas_cd)
    col_var     = detectar_columna(["variable", "var", "tag", "nombre"], columnas_cd)
    col_valor   = detectar_columna(["valor", "value", "val"], columnas_cd)
    col_time    = detectar_columna(["timestamp", "fecha", "time", "datetime"], columnas_cd)

    if col_maquina is None or col_var is None or col_valor is None:
        st.error("No encuentro columnas de maquina, variable o valor en tus CSV. Revisa el nombre exacto.")
        st.stop()

    # Renombramos columnas a estándar
    df_cd = df_cd.rename(columns={
        col_maquina: "maquina",
        col_var: "variable",
        col_valor: "valor",
        col_time: "timestamp" if col_time else None
    })

    df_cw = df_cw.rename(columns={
        col_maquina: "maquina",
        col_var: "variable",
        col_valor: "valor",
        col_time: "timestamp" if col_time else None
    })

    df_cd["tipo"] = "CD"
    df_cw["tipo"] = "CW"

    df = pd.concat([df_cd, df_cw], ignore_index=True)

    # Convertimos timestamp
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    return df, lim


df, lim = load_data()


# --------------------------------------
# PROCESAR LÍMITES
# --------------------------------------
lim.columns = lim.columns.str.lower().str.strip()

# Formato de 8 columnas CD + CW
lim_cd = lim.iloc[:, [0, 1, 2, 3]].copy()
lim_cd.columns = ["maquina", "variable", "lim_inf", "lim_sup"]
lim_cd["tipo"] = "CD"

lim_cw = lim.iloc[:, [4, 5, 6, 7]].copy()
lim_cw.columns = ["maquina", "variable", "lim_inf", "lim_sup"]
lim_cw["tipo"] = "CW"

lim_clean = pd.concat([lim_cd, lim_cw], ignore_index=True)


# --------------------------------------
# SIDEBAR
# --------------------------------------
st.sidebar.header("Filtros")

tipo_select = st.sidebar.multiselect(
    "Tipo de datos",
    options=["CD", "CW"],
    default=["CD", "CW"]
)

df_filtered = df[df["tipo"].isin(tipo_select)]

maquinas = sorted(df_filtered["maquina"].dropna().unique())
maquina_select = st.sidebar.selectbox("Selecciona máquina", maquinas)

df_filtered = df_filtered[df_filtered["maquina"] == maquina_select]
lim_filtered = lim_clean[lim_clean["maquina"] == maquina_select]

variables = sorted(df_filtered["variable"].dropna().unique())
vars_select = st.sidebar.multiselect(
    "Variables",
    variables,
    default=variables
)

df_filtered = df_filtered[df_filtered["variable"].isin(vars_select)]
lim_filtered = lim_filtered[lim_filtered["variable"].isin(vars_select)]


# --------------------------------------
# GRAFICAR
# --------------------------------------
st.title("Dashboard CD / CW — Líneas con límites")

if df_filtered.empty:
    st.warning("No hay datos con esos filtros.")
    st.stop()

# Unión (solo por variable y tipo para evitar KeyError)
plot_df = df_filtered.merge(
    lim_filtered,
    on=["variable", "tipo"],
    how="left"
)

for var in vars_select:
    temp = plot_df[plot_df["variable"] == var]

    st.subheader(f"{maquina_select} — {var}")

    fig = px.line(temp, x="timestamp", y="valor", markers=True)

    if temp["lim_sup"].notna().any():
        fig.add_hline(y=temp["lim_sup"].iloc[0], line_dash="dash", annotation_text="Límite Sup")

    if temp["lim_inf"].notna().any():
        fig.add_hline(y=temp["lim_inf"].iloc[0], line_dash="dash", annotation_text="Límite Inf")

    st.plotly_chart(fig, use_container_width=True)
