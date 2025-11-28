import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard CD/CW", layout="wide")

# -----------------------------
# CARGA DE ARCHIVOS
# -----------------------------
@st.cache_data
def load_data():
    df_cd = pd.read_csv("CD_unificado.csv")
    df_cw = pd.read_csv("CW_unificado.csv")
    lim = pd.read_excel("Limites en tablas (2).xlsx")

    # Estandarizamos nombres
    df_cd.columns = df_cd.columns.str.lower().str.strip()
    df_cw.columns = df_cw.columns.str.lower().str.strip()
    lim.columns = lim.columns.str.lower().str.strip()

    # Unimos CD y CW
    df_cd["tipo"] = "CD"
    df_cw["tipo"] = "CW"
    df = pd.concat([df_cd, df_cw], ignore_index=True)

    # Convertimos timestamp si existe
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    return df, lim

df, lim = load_data()

# -----------------------------
# PREPARAR LÍMITES
# -----------------------------
# Suponiendo el formato:
# columna 0: maquina_cd   / columna 4: maquina_cw
# columna 1: variable_cd  / columna 5: variable_cw
# columna 2: lim_inf_cd   / columna 6: lim_inf_cw
# columna 3: lim_sup_cd   / columna 7: lim_sup_cw

lim_cd = lim.iloc[:, [0, 1, 2, 3]].copy()
lim_cd.columns = ["maquina", "variable", "lim_inf", "lim_sup"]
lim_cd["tipo"] = "CD"

lim_cw = lim.iloc[:, [4, 5, 6, 7]].copy()
lim_cw.columns = ["maquina", "variable", "lim_inf", "lim_sup"]
lim_cw["tipo"] = "CW"

lim_clean = pd.concat([lim_cd, lim_cw], ignore_index=True)

# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.header("Filtros")

# Selección de tipo (CD/CW/Both)
tipo_select = st.sidebar.multiselect(
    "Tipo de datos",
    options=["CD", "CW"],
    default=["CD", "CW"]
)

df_filtered = df[df["tipo"].isin(tipo_select)]

# Máquinas dinámicas
maquinas = sorted(df_filtered["maquina"].dropna().unique())
maquina_select = st.sidebar.selectbox("Selecciona máquina", maquinas)

df_filtered = df_filtered[df_filtered["maquina"] == maquina_select]
lim_filtered = lim_clean[lim_clean["maquina"] == maquina_select]

# Variables automáticas
variables = sorted(df_filtered["variable"].dropna().unique())
vars_select = st.sidebar.multiselect(
    "Variables",
    options=variables,
    default=variables  # Todas seleccionadas automáticamente
)

df_filtered = df_filtered[df_filtered["variable"].isin(vars_select)]
lim_filtered = lim_filtered[lim_filtered["variable"].isin(vars_select)]

# -----------------------------
# GRÁFICOS
# -----------------------------
st.title("Dashboard CD / CW — Líneas de Tiempo con Límites")

if df_filtered.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

# Unimos límites por variable (NO por 'maquina' para evitar KeyError)
plot_df = df_filtered.merge(
    lim_filtered,
    on=["variable", "tipo"],
    how="left"
)

# Para cada variable, hacemos un gráfico
for var in vars_select:
    temp = plot_df[plot_df["variable"] == var]

    st.subheader(f"{maquina_select} — {var}")

    fig = px.line(
        temp,
        x="timestamp",
        y="valor",
        title=f"{var}",
        markers=True
    )

    # Agregamos límites si existen
    if temp["lim_sup"].notna().any():
        fig.add_hline(y=temp["lim_sup"].iloc[0], line_dash="dash", annotation_text="Límite Superior")

    if temp["lim_inf"].notna().any():
        fig.add_hline(y=temp["lim_inf"].iloc[0], line_dash="dash", annotation_text="Límite Inferior")

    st.plotly_chart(fig, use_container_width=True)
