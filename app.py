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

# columnas que SÍ son variables (Get_AngleX)
vars_cd = [c for c in cd_raw.columns if "Get_Angle" in c or "Get Angle" in c]
vars_cw = [c for c in cw_raw.columns if "Get_Angle" in c or "Get Angle" in c]

# --------------------------------
# CONVERTIR A FORMATO LONG
# --------------------------------

def melt_df(df, variables):
    long_df = df.melt(
        id_vars=["maquina","Date","Time"],
        value_vars=variables,
        var_name="variable",
        value_name="valor"
    )
    long_df["timestamp"] = long_df["Date"].astype(str) + " " + long_df["Time"].astype(str)
    return long_df

cd_df = melt_df(cd_raw, vars_cd)
cw_df = melt_df(cw_raw, vars_cw)

# --------------------------------
# UI STREAMLIT
# --------------------------------
st.title("📊 Dashboard de Límites CD / CW")

tipo = st.sidebar.selectbox("Tipo de datos", ["CD", "CW"])

df = cd_df if tipo=="CD" else cw_df

maquinas = sorted(df["maquina"].unique())
maq = st.sidebar.selectbox("Máquina", maquinas)

df_m = df[df["maquina"] == maq]

variables = sorted(df_m["variable"].unique())
var = st.sidebar.selectbox("Variable", variables)

df_v = df_m[df_m["variable"] == var]

# --------------------------------
# EXTRAER LÍMITES
# --------------------------------
lim = limites_df[
    (limites_df["maquina"] == maq) &
    (limites_df["variable"] == var.replace("_","").replace(" ","")) &
    (limites_df["tipo"] == tipo)
]

lim_inf = lim["lim_inf"].values[0] if not lim.empty else None
lim_sup = lim["lim_sup"].values[0] if not lim.empty else None

# --------------------------------
# TABLA DE DATOS
# --------------------------------
st.subheader("📄 Datos filtrados")
st.dataframe(df_v)

# --------------------------------
# GRAFICAR
# --------------------------------
fig = px.line(df_v, x="timestamp", y="valor",
              title=f"{maq} — {var}")

if lim_inf is not None:
    fig.add_hline(y=lim_inf, line_dash="dot",
                  annotation_text="Límite Inferior")

if lim_sup is not None:
    fig.add_hline(y=lim_sup, line_dash="dot",
                  annotation_text="Límite Superior")

st.plotly_chart(fig, use_container_width=True)
