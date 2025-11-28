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
# NORMALIZADOR DE VARIABLES
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

# --------------------------------
# UI STREAMLIT
# --------------------------------
st.title("📊 Dashboard de Límites CD / CW")

tipo = st.sidebar.selectbox("Tipo de datos", ["CD", "CW"])
df = cd_df if tipo == "CD" else cw_df

# Selección de máquina
maquinas = sorted(df["maquina"].unique())
maq = st.sidebar.selectbox("Máquina", maquinas)
df_m = df[df["maquina"] == maq]

# Selección de variable
variables = sorted(df_m["variable"].unique())
var = st.sidebar.selectbox("Variable", variables)
df_v = df_m[df_m["variable"] == var].copy()

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
# MARCAR PUNTOS FUERA
# --------------------------------
df_v["fuera"] = False
if lim_inf is not None:
    df_v.loc[df_v["valor"] < lim_inf, "fuera"] = True
if lim_sup is not None:
    df_v.loc[df_v["valor"] > lim_sup, "fuera"] = True

# --------------------------------
# KPI CARDS
# --------------------------------
st.subheader("📌 Indicadores clave (KPI)")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Promedio", f"{df_v['valor'].mean():.2f}")

with col2:
    st.metric("Último valor", f"{df_v['valor'].iloc[-1]:.2f}")

with col3:
    fuera_pct = df_v["fuera"].mean() * 100
    st.metric("% Fuera de límites", f"{fuera_pct:.1f}%")

# --------------------------------
# TABS DE VISUALIZACIÓN
# --------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Control Chart", "Histograma", "Boxplot", "Scatter", "Por hora"]
)

# --------------------------------
# CONTROL CHART
# --------------------------------
with tab1:
    st.subheader("📈 Gráfico de Control")

    fig = px.line(df_v, x="timestamp", y="valor", title=f"{maq} — {var}")

    # Media
    media = df_v["valor"].mean()
    fig.add_hline(y=media, line_dash="solid", line_color="blue",
                  annotation_text="Media")

    # Límites
    if lim_inf is not None:
        fig.add_hline(y=lim_inf, line_dash="dot", line_color="red",
                      annotation_text="Límite Inferior")
    if lim_sup is not None:
        fig.add_hline(y=lim_sup, line_dash="dot", line_color="red",
                      annotation_text="Límite Superior")

    # Banda
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

    # Puntos fuera
    df_fuera = df_v[df_v["fuera"] == True]
    fig.add_scatter(
        x=df_fuera["timestamp"],
        y=df_fuera["valor"],
        mode="markers",
        marker=dict(color="red", size=10),
        name="Fuera de control"
    )

    st.plotly_chart(fig, use_container_width=True)

# --------------------------------
# HISTOGRAMA
# --------------------------------
with tab2:
    st.subheader("📊 Histograma")

    fig_hist = px.histogram(df_v, x="valor", nbins=30)

    if lim_inf is not None:
        fig_hist.add_vline(x=lim_inf, line_color="red")
    if lim_sup is not None:
        fig_hist.add_vline(x=lim_sup, line_color="red")

    st.plotly_chart(fig_hist, use_container_width=True)

# --------------------------------
# BOXPLOT
# --------------------------------
with tab3:
    st.subheader("📦 Boxplot")

    fig_box = px.box(df_v, y="valor", points="outliers")
    st.plotly_chart(fig_box, use_container_width=True)

# --------------------------------
# SCATTER
# --------------------------------
with tab4:
    st.subheader("🔵 Dispersión")

    fig_scatter = px.scatter(df_v, x="timestamp", y="valor", opacity=0.7)

    if lim_inf is not None:
        fig_scatter.add_hline(y=lim_inf, line_color="red", line_dash="dot")
    if lim_sup is not None:
        fig_scatter.add_hline(y=lim_sup, line_color="red", line_dash="dot")

    st.plotly_chart(fig_scatter, use_container_width=True)

# --------------------------------
# PROMEDIO POR HORA
# --------------------------------
with tab5:
    st.subheader("🕒 Promedio por hora")

    try:
        df_v["hour"] = pd.to_datetime(df_v["Time"], format="%H:%M:%S").dt.hour
        df_hour = df_v.groupby("hour")["valor"].mean().reset_index()

        fig_hour = px.bar(df_hour, x="hour", y="valor", title="Promedio por hora")
        st.plotly_chart(fig_hour, use_container_width=True)

    except:
        st.info("Formato de hora no reconocido.")
