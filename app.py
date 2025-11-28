import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard CD/CW", layout="wide")

# --------------------------------
# CARGA DE DATOS
# --------------------------------
@st.cache_data
def load_data():
    cd = pd.read_csv("CD_unificado.csv")
    cw = pd.read_csv("CW_unificado.csv")

    limites = pd.read_excel("Limites en tablas (2).xlsx")
    limites.columns = [
        "CD_maquina","CD_variable","CD_lim_inf","CD_lim_sup",
        "CW_maquina","CW_variable","CW_lim_inf","CW_lim_sup"
    ]

    # convertir limites CD
    limites_cd = limites[["CD_maquina","CD_variable","CD_lim_inf","CD_lim_sup"]].rename(
        columns={"CD_maquina":"maquina","CD_variable":"variable",
                 "CD_lim_inf":"lim_inf","CD_lim_sup":"lim_sup"}
    )
    limites_cd["tipo"] = "CD"

    # convertir limites CW
    limites_cw = limites[["CW_maquina","CW_variable","CW_lim_inf","CW_lim_sup"]].rename(
        columns={"CW_maquina":"maquina","CW_variable":"variable",
                 "CW_lim_inf":"lim_inf","CW_lim_sup":"lim_sup"}
    )
    limites_cw["tipo"] = "CW"

    limites_total = pd.concat([limites_cd, limites_cw])

    return cd, cw, limites_total


cd_raw, cw_raw, limites_df = load_data()

# --------------------------------
# PREPARAR LISTA DE VARIABLES
# --------------------------------
vars_cd = [c for c in cd_raw.columns if "Get_Angle" in c or "Get Angle" in c]
vars_cw = [c for c in cw_raw.columns if "Get_Angle" in c or "Get Angle" in c]


# --------------------------------
# FUNCIÓN PARA FORMATO LONG
# --------------------------------
def melt_df(df, variables, tipo):
    long_df = df.melt(
        id_vars=["maquina","Date","Time"],
        value_vars=variables,
        var_name="variable",
        value_name="valor"
    )
    long_df["timestamp"] = long_df["Date"].astype(str) + " " + long_df["Time"].astype(str)
    long_df["tipo"] = tipo
    return long_df

cd_df = melt_df(cd_raw, vars_cd, "CD")
cw_df = melt_df(cw_raw, vars_cw, "CW")


# --------------------------------
# SIDEBAR UI
# --------------------------------
st.sidebar.title("Filtros")

tipo_sel = st.sidebar.multiselect(
    "Selecciona tipo de datos",
    ["CD", "CW"],
    default=["CD"]  # por defecto CD
)

# unir según selección
if tipo_sel == ["CD"]:
    df = cd_df
elif tipo_sel == ["CW"]:
    df = cw_df
else:
    df = pd.concat([cd_df, cw_df])

# máquinas según la selección
maquinas = sorted(df["maquina"].unique())

maq_select = st.sidebar.multiselect(
    "Máquinas",
    maquinas,
    default=maquinas[:2]  # las primeras 2 por default
)

df = df[df["maquina"].isin(maq_select)]

# variables disponibles
variables = sorted(df["variable"].unique())

var_select = st.sidebar.selectbox("Variable", variables)


# --------------------------------
# FILTRO FINAL
# --------------------------------
df_plot = df[df["variable"] == var_select]


# --------------------------------
# OBTENER LÍMITES (solo si CD o CW seleccionados individualmente)
# Si es ambos, no se ponen límites
# --------------------------------
lim_inf = None
lim_sup = None

if len(tipo_sel) == 1:
    tipo_actual = tipo_sel[0]

    lim_match = limites_df[
        (limites_df["tipo"] == tipo_actual) &
        (limites_df["maquina"].isin(maq_select)) &
        (limites_df["variable"] == var_select.replace("_","").replace(" ",""))
    ]

    if not lim_match.empty:
        lim_inf = lim_match["lim_inf"].iloc[0]
        lim_sup = lim_match["lim_sup"].iloc[0]


# --------------------------------
# TABLA
# --------------------------------
st.subheader("📄 Datos filtrados")
st.dataframe(df_plot)


# --------------------------------
# GRÁFICA
# --------------------------------
fig = px.line(
    df_plot,
    x="timestamp",
    y="valor",
    color="tipo",     # CD / CW
    line_group="maquina",
    title=f"Comportamiento de {var_select} para máquinas seleccionadas"
)

if lim_inf is not None:
    fig.add_hline(y=lim_inf, line_dash="dot", annotation_text="Límite Inferior")

if lim_sup is not None:
    fig.add_hline(y=lim_sup, line_dash="dot", annotation_text="Límite Superior")

st.plotly_chart(fig, use_container_width=True)

