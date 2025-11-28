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
    limites_total["variable_norm"] = limites_total["variable"].str.replace("_", "").str.replace(" ", "").str.lower()

    return cd, cw, limites_total


cd_raw, cw_raw, limites_df = load_data()

# --------------------------------
# NORMALIZADOR
# --------------------------------
def normalizar_variable(v):
    return v.replace("_", "").replace(" ", "").strip().lower()

# --------------------------------
# IDENTIFICAR VARIABLES
# --------------------------------
vars_cd = [c for c in cd_raw.columns if "Get_Angle" in c or "Get Angle" in c]
vars_cw = [c for c in cw_raw.columns if "Get_Angle" in c or "Get Angle" in c]

# --------------------------------
# FORMATO LONG
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

cd_df["valor"] = pd.to_numeric(cd_df["valor"], errors="coerce")
cw_df["valor"] = pd.to_numeric(cw_df["valor"], errors="coerce")

# --------------------------------
# UI
# --------------------------------
st.title("📊 Dashboard de Límites CD / CW")

tipo = st.sidebar.selectbox("Tipo de datos", ["CD", "CW"])
df = cd_df if tipo == "CD" else cw_df

maquinas = sorted(df["maquina"].unique())
maq = st.sidebar.selectbox("Máquina", maquinas)
df_m = df[df["maquina"] == maq]

variables = sorted(df_m["variable"].unique())
var = st.sidebar.selectbox("Variable", variables)
df_v = df_m[df_m["variable"] == var].copy()

df_v["valor"] = pd.to_numeric(df_v["valor"], errors="coerce")
df_v = df_v.dropna(subset=["valor"])

var_norm = normalizar_variable(var)

# --------------------------------
# OBTENER LÍMITES
# --------------------------------
lim = limites_df[
    (limites_df["maquina"].str.lower() == maq.lower()) &
    (limites_df["variable_norm"] == var_norm) &
    (limites_df["tipo"] == tipo)
]

lim_inf = lim["lim_inf"].values[0] if not lim.empty else None
lim_sup = lim["lim_sup"].values[0] if not lim.empty else None

# --------------------------------
# MARCAR FUERA DE LÍMITE
# --------------------------------
df_v["fuera"] = False
if lim_inf is not None:
    df_v.loc[df_v["valor"] < lim_inf, "fuera"] = True
if lim_sup is not None:
    df_v.loc[df_v["valor"] > lim_sup, "fuera"] = True

# --------------------------------
# KPIs
# --------------------------------
st.subheader("📌 Indicadores clave (KPI)")

col1, col2, col3 = st.columns(3)

promedio = df_v["valor"].mean() if not df_v.empty else 0
ultimo = df_v["valor"].iloc[-1] if not df_v.empty else 0
fuera_pct = df_v["fuera"].mean() * 100 if not df_v.empty else 0

col1.metric("Promedio", f"{promedio:.2f}")
col2.metric("Último valor", f"{ultimo:.2f}")
col3.metric("% Fuera de límites", f"{fuera_pct:.1f}%")

# --------------------------------
# GRÁFICAS
# --------------------------------
st.subheader("📈 Gráfico de Control")

fig = px.line(df_v, x="timestamp", y="valor", title=f"{maq} — {var}")

media = df_v["valor"].mean()
fig.add_hline(y=media, line_dash="solid", line_color="blue", annotation_text="Media")

if lim_inf is not None:
    fig.add_hline(y=lim_inf, line_dash="dot", line_color="red", annotation_text="Límite Inferior")
if lim_sup is not None:
    fig.add_hline(y=lim_sup, line_dash="dot", line_color="red", annotation_text="Límite Superior")

df_fuera = df_v[df_v["fuera"] == True]
fig.add_scatter(
    x=df_fuera["timestamp"],
    y=df_fuera["valor"],
    mode="markers",
    marker=dict(color="red", size=10),
    name="Fuera de control",
)

st.plotly_chart(fig, use_container_width=True)
