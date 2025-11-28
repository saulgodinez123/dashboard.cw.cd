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
# FUNCIÓN PARA NORMALIZAR NOMBRES DE VARIABLES
# --------------------------------
def normalizar_variable(v):
    return v.replace("_","").replace(" ","").strip().lower()

# --------------------------------
# IDENTIFICAR VARIABLES
# --------------------------------
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
    long_df["timestamp"] = long_df["Date"].astype(str) + " " + df["Time"].astype(str)
    return long_df

cd_df = melt_df(cd_raw, vars_cd)
cw_df = melt_df(cw_raw, vars_cw)

# --------------------------------
# UI STREAMLIT
# --------------------------------
st.title("📊 Dashboard de Límites CD / CW")

tipo = st.sidebar.selectbox("Tipo de datos", ["CD", "CW"])
df = cd_df if tipo=="CD" else cw_df

# Selección de máquina
maquinas = sorted(df["maquina"].unique())
maq = st.sidebar.selectbox("Máquina", maquinas)
df_m = df[df["maquina"] == maq]

# Selección de variable
variables = sorted(df_m["variable"].unique())
var = st.sidebar.selectbox("Variable", variables)
df_v = df_m[df_m["variable"] == var].copy()

# Normalizar nombre para buscar en tabla de límites
var_norm = normalizar_variable(var)

# --------------------------------
# EXTRAER LÍMITES
# --------------------------------
lim = limites_df[
    (limites_df["maquina"].str.lower() == maq.lower()) &
    (limites_df["variable"].str.lower() == var_norm) &
    (limites_df["tipo"] == tipo)
]

lim_inf = lim["lim_inf"].values[0] if not lim.empty else None
lim_sup = lim["lim_sup"].values[0] if not lim.empty else None

# --------------------------------
# MARCAR PUNTOS FUERA DE LÍMITES
# --------------------------------
df_v["fuera"] = False
if lim_inf is not None:
    df_v.loc[df_v["valor"] < lim_inf, "fuera"] = True
if lim_sup is not None:
    df_v.loc[df_v["valor"] > lim_sup, "fuera"] = True

# --------------------------------
# TABLA DE DATOS
# --------------------------------
st.subheader("📄 Datos filtrados")
st.dataframe(df_v)

# --------------------------------
# GRÁFICO DE CONTROL
# --------------------------------
st.subheader("📈 Gráfico de Control (Shewhart Chart)")

fig = px.line(
    df_v,
    x="timestamp",
    y="valor",
    markers=False,
    title=f"Control Chart — {maq} / {var}"
)

# Media
media = df_v["valor"].mean()
fig.add_hline(y=media, line_dash="solid", line_color="blue",
              annotation_text="Media", annotation_position="top left")

# Límites
if lim_inf is not None:
    fig.add_hline(y=lim_inf, line_dash="dot", line_color="red",
                  annotation_text="Límite Inferior")

if lim_sup is not None:
    fig.add_hline(y=lim_sup, line_dash="dot", line_color="red",
                  annotation_text="Límite Superior")

# Relleno de banda
if lim_inf is not None and lim_sup is not None:
    fig.add_shape(
        type="rect",
        x0=df_v["timestamp"].min(),
        x1=df_v["timestamp"].max(),
        y0=lim_inf,
        y1=lim_sup,
        fillcolor="green",
        opacity=0.15,
        layer="below",
        line_width=0
    )

# Puntos fuera de control (rojos)
df_fuera = df_v[df_v["fuera"] == True]
fig.add_scatter(
    x=df_fuera["timestamp"],
    y=df_fuera["valor"],
    mode="markers",
    marker=dict(color="red", size=10),
    name="Fuera de control"
)

st.plotly_chart(fig, use_container_width=True)
