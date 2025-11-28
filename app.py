import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Dashboard CD/CW", layout="wide")

# =========================================================
# 1. CARGA LIGERA DE DATOS
# =========================================================
@st.cache_data
def load_machine_csv(path):
    df = pd.read_csv(path)

    # Crear timestamp
    df["timestamp"] = pd.to_datetime(df["Date"] + " " + df["Time"], errors="coerce")

    # Seleccionar columnas clave
    id_cols = ["timestamp", "maquina"]
    id_cols = [c for c in id_cols if c in df.columns]

    # Variables = todo lo demás
    variable_cols = [c for c in df.columns if c not in id_cols]

    # Convertir a formato largo
    long_df = df.melt(
        id_vars=id_cols,
        value_vars=variable_cols,
        var_name="variable",
        value_name="valor"
    )

    return long_df


@st.cache_data
def load_limits():
    lim = pd.read_excel("Limites en tablas (2).xlsx")

    # Normalizar columnas a texto
    lim.columns = lim.columns.astype(str)

    rows = []

    for _, r in lim.iterrows():
        # CD
        if pd.notna(r.get("CD_maquina")):
            rows.append({
                "maquina": r.get("CD_maquina"),
                "variable": r.get("CD_variable"),
                "LSL": r.get("CD_LSL"),
                "USL": r.get("CD_USL")
            })

        # CW
        if pd.notna(r.get("CW_maquina")):
            rows.append({
                "maquina": r.get("CW_maquina"),
                "variable": r.get("CW_variable"),
                "LSL": r.get("CW_LSL"),
                "USL": r.get("CW_USL")
            })

    return pd.DataFrame(rows)


# =========================================================
# 2. CARGA REAL
# =========================================================
cd = load_machine_csv("CD_unificado.csv")
cw = load_machine_csv("CW_unificado.csv")
lim = load_limits()

df = pd.concat([cd, cw], ignore_index=True)

# =========================================================
# 3. FILTROS
# =========================================================

st.sidebar.header("Filtros")

# Detectar CD o CW desde la columna maquina
tipo = st.sidebar.multiselect(
    "Tipo de prueba:",
    ["CD", "CW"],
    default=["CD", "CW"]
)

df = df[df["maquina"].str.contains("|".join(tipo), case=False, na=False)]

# Filtrar por máquina
maquinas = sorted(df["maquina"].unique())
maq_sel = st.sidebar.selectbox("Selecciona la máquina:", maquinas)

df = df[df["maquina"] == maq_sel]

# Variables disponibles
vars_disp = sorted(df["variable"].unique())
vars_sel = st.sidebar.multiselect("Selecciona variables:", vars_disp, default=vars_disp[:5])

df = df[df["variable"].isin(vars_sel)]

# =========================================================
# 4. UNIR LÍMITES
# =========================================================
df = df.merge(lim, how="left", on=["maquina", "variable"])

# =========================================================
# 5. GRÁFICA (SÚPER LIGERA)
# =========================================================
st.header("Tendencia en el tiempo con límites")

chart = (
    alt.Chart(df)
    .mark_line()
    .encode(
        x="timestamp:T",
        y="valor:Q",
        color="variable:N"
    )
)

base = chart

# Línea LSL
if df["LSL"].notna().any():
    lsl_chart = (
        alt.Chart(df[df["LSL"].notna()])
        .mark_rule(color="red", strokeDash=[4,4])
        .encode(y="LSL:Q")
    )
    base = base + lsl_chart

# Línea USL
if df["USL"].notna().any():
    usl_chart = (
        alt.Chart(df[df["USL"].notna()])
        .mark_rule(color="red", strokeDash=[4,4])
        .encode(y="USL:Q")
    )
    base = base + usl_chart

st.altair_chart(base.interactive(), use_container_width=True)

# Mostrar tabla resumida
st.subheader("Límites encontrados")
st.dataframe(df[["variable", "LSL", "USL"]].drop_duplicates())
