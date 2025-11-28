import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Producción", layout="wide")

# -------------------------
# 1. Cargar datos
# -------------------------
@st.cache_data
def load_data():
    cd = pd.read_csv("CD_unificado.csv")
    cw = pd.read_csv("CW_unificado.csv")
    limites = pd.read_excel("Limites en tablas (2).xlsx")

    # Normalizar columnas
    limites.columns = [
        "CD_maquina", "CD_variable", "CD_lim_inf", "CD_lim_sup",
        "CW_maquina", "CW_variable", "CW_lim_inf", "CW_lim_sup"
    ]

    # Convertir = a tipo máquina
    limites_cd = limites[["CD_maquina", "CD_variable", "CD_lim_inf", "CD_lim_sup"]].rename(
        columns={"CD_maquina": "maquina", "CD_variable": "variable",
                 "CD_lim_inf": "lim_inf", "CD_lim_sup": "lim_sup"}
    )
    limites_cw = limites[["CW_maquina", "CW_variable", "CW_lim_inf", "CW_lim_sup"]].rename(
        columns={"CW_maquina": "maquina", "CW_variable": "variable",
                 "CW_lim_inf": "lim_inf", "CW_lim_sup": "lim_sup"}
    )

    limites_total = pd.concat([limites_cd.assign(tipo="CD"),
                               limites_cw.assign(tipo="CW")])

    return cd, cw, limites_total


cd_df, cw_df, limites_df = load_data()

st.title("📊 Dashboard de Control de Producción (CD / CW)")

# -------------------------
# 2. Selecciones de usuario
# -------------------------
tipo = st.sidebar.selectbox("Selecciona tipo de dato", ["CD", "CW"])

if tipo == "CD":
    df = cd_df
else:
    df = cw_df

maquinas = sorted(df["maquina"].unique())
maquina_select = st.sidebar.selectbox("Selecciona línea de producción", maquinas)

vars_maquina = sorted(df[df["maquina"] == maquina_select]["variable"].unique())
variable_select = st.sidebar.selectbox("Selecciona variable", vars_maquina)

# -------------------------
# 3. Filtrar datos
# -------------------------
filtro = df[(df["maquina"] == maquina_select) & (df["variable"] == variable_select)]

# Obtener límites
lim = limites_df[
    (limites_df["maquina"] == maquina_select) &
    (limites_df["variable"] == variable_select) &
    (limites_df["tipo"] == tipo)
]

if lim.empty:
    st.warning("⚠ No existen límites de control definidos para esta variable.")
    lim_inf = None
    lim_sup = None
else:
    lim_inf = lim["lim_inf"].values[0]
    lim_sup = lim["lim_sup"].values[0]

# -------------------------
# 4. Mostrar tabla
# -------------------------
st.subheader("📄 Datos filtrados")
st.dataframe(filtro)

# -------------------------
# 5. Gráfica
# -------------------------
st.subheader("📈 Gráfica de la variable")

fig = px.line(filtro, x="timestamp", y="valor", title=f"{maquina_select} - {variable_select}")

# Límites de control
if lim_inf is not None:
    fig.add_hline(y=lim_inf, line_dash="dot", annotation_text="Límite Inferior", opacity=0.7)

if lim_sup is not None:
    fig.add_hline(y=lim_sup, line_dash="dot", annotation_text="Límite Superior", opacity=0.7)

st.plotly_chart(fig, use_container_width=True)
