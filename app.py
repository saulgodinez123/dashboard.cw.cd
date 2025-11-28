import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard CD/CW", layout="wide")

# --------------------------------------------------------
# 1️⃣ CARGA DE DATOS
# --------------------------------------------------------
@st.cache_data
def load_data():
    df_all = pd.read_excel("MANT.xlsx")
    df_lim = pd.read_excel("LIM.xlsx", header=None)   # sin encabezados
    return df_all, df_lim

df_all, df_lim_raw = load_data()

st.title("📊 Dashboard CD / CW")


# --------------------------------------------------------
# 2️⃣ PARSEAR LIM.xlsx EN FORMATO CORRECTO
# --------------------------------------------------------
def transformar_limites(df_raw):

    limites_final = []

    # Cada máquina usa 3 columnas: variable, limite inferior, limite superior
    num_cols = df_raw.shape[1]
    grupos = num_cols // 3

    for i in range(grupos):

        col_start = i * 3
        col_var = col_start
        col_low = col_start + 1
        col_high = col_start + 2

        # Nombre de la máquina (está en fila 0)
        maquina = str(df_raw.iloc[0, col_var]).strip()

        # Valores desde la fila 1 hacia abajo
        variables = df_raw.iloc[1:, col_var]
        lows = df_raw.iloc[1:, col_low]
        highs = df_raw.iloc[1:, col_high]

        for var, lo, hi in zip(variables, lows, highs):

            if pd.isna(var):
                continue

            limites_final.append({
                "maquina": maquina,
                "variable": str(var).strip(),
                "LimiteInferior": lo,
                "LimiteSuperior": hi
            })

    return pd.DataFrame(limites_final)


df_limites = transformar_limites(df_lim_raw)


# --------------------------------------------------------
# 3️⃣ FILTROS
# --------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    area = st.selectbox("Área", ["Todas"] + sorted(df_all["area"].dropna().unique()))

with col2:
    maquina = st.selectbox("Máquina", ["Todas"] + sorted(df_all["maquina"].dropna().unique()))

with col3:
    variable = st.selectbox("Variable", ["Todas"] + sorted(df_all["Variable"].dropna().unique()))

# Detectar métricas numéricas válidas
metricas = []
for c in df_all.columns:
    if pd.api.types.is_numeric_dtype(df_all[c]) and df_all[c].count() > 5 and df_all[c].nunique() > 1:
        if c not in ["LimiteInferior", "LimiteSuperior"]:
            metricas.append(c)

with col4:
    metrica = st.selectbox("Métrica", metricas)


# --------------------------------------------------------
# 4️⃣ APLICAR FILTROS
# --------------------------------------------------------
df_filt = df_all.copy()

if area != "Todas":
    df_filt = df_filt[df_filt["area"] == area]

if maquina != "Todas":
    df_filt = df_filt[df_filt["maquina"] == maquina]

if variable != "Todas":
    df_filt = df_filt[df_filt["Variable"] == variable]

if df_filt.empty:
    st.warning("⚠️ No hay datos con los filtros seleccionados.")
    st.stop()

# --------------------------------------------------------
# 5️⃣ UNIR MÉTRICOS CON LÍMITES
# --------------------------------------------------------
df_merge = pd.merge(
    df_filt,
    df_limites,
    left_on=["maquina", "Variable"],
    right_on=["maquina", "variable"],
    how="left"
)

# --------------------------------------------------------
# 6️⃣ GRÁFICA PRINCIPAL
# --------------------------------------------------------
st.subheader(f"📈 Gráfica: {metrica}")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df_merge["Date"],
    y=df_merge[metrica],
    mode="lines+markers",
    name=metrica
))

# Límites
if df_merge["LimiteInferior"].notna().any():
    fig.add_trace(go.Scatter(
        x=df_merge["Date"],
        y=df_merge["LimiteInferior"],
        mode="lines",
        name="Límite Inferior",
        line=dict(dash="dot")
    ))

if df_merge["LimiteSuperior"].notna().any():
    fig.add_trace(go.Scatter(
        x=df_merge["Date"],
        y=df_merge["LimiteSuperior"],
        mode="lines",
        name="Límite Superior",
        line=dict(dash="dot")
    ))

fig.update_layout(
    height=500,
    template="plotly_white",
    xaxis_title="Fecha",
    yaxis_title=metrica
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------
# 7️⃣ TABLA
# --------------------------------------------------------
st.subheader("📄 Datos filtrados")
st.dataframe(df_merge, use_container_width=True)
