import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Dashboard CD & CW", layout="wide")

# =========================================================
# 1. Cargar Datos
# =========================================================
@st.cache_data
def load_csv(path):
    df = pd.read_csv(path)
    
    # Crear timestamp combinando Date + Time
    if "Date" in df.columns and "Time" in df.columns:
        df["timestamp"] = pd.to_datetime(df["Date"] + " " + df["Time"], errors="coerce")
    else:
        st.warning(f"El archivo {path} no tiene columnas Date/Time correctamente definidas.")
        df["timestamp"] = pd.NaT

    # Mantener datos esenciales
    if "maquina" not in df.columns:
        st.error(f"El archivo {path} NO contiene la columna 'maquina'.")
        st.stop()

    # Hacer formato largo (variable–valor)
    id_cols = ["timestamp", "maquina", "linea", "categoria"]
    id_cols = [c for c in id_cols if c in df.columns]

    var_cols = [c for c in df.columns if c not in id_cols]

    long_df = df.melt(id_vars=id_cols, value_vars=var_cols,
                      var_name="variable", value_name="valor")

    return long_df


@st.cache_data
def load_limits():
    try:
        lim = pd.read_excel("Limites en tablas (2).xlsx")

        lim.columns = lim.columns.astype(str)
        lim = lim.dropna(how="all")

        # Normalizar a formato largo usable
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

        lim_df = pd.DataFrame(rows)

        return lim_df

    except Exception as e:
        st.error(f"Error cargando límites: {e}")
        return pd.DataFrame()


# =========================================================
# 2. Carga real de archivos
# =========================================================
st.sidebar.header("Carga de datos")

cd_df = load_csv("CD_unificado.csv")
cw_df = load_csv("CW_unificado.csv")
lim_df = load_limits()

df = pd.concat([cd_df, cw_df], ignore_index=True)

# =========================================================
# 3. Filtros en Sidebar
# =========================================================
st.sidebar.header("Filtros")

tipo_select = st.sidebar.multiselect(
    "Seleccionar tipo (CD / CW)",
    options=["CD", "CW"],
    default=["CD", "CW"]
)

# Filtrar por substring en columna maquina
if tipo_select:
    df = df[df["maquina"].str.contains("|".join(tipo_select), case=False, na=False)]

maquinas = sorted(df["maquina"].unique())

maquina_select = st.sidebar.multiselect(
    "Seleccionar máquinas",
    options=maquinas,
    default=maquinas
)

df = df[df["maquina"].isin(maquina_select)]

# Variables dinámicas según la máquina escogida
variables = sorted(df["variable"].unique())

var_select = st.sidebar.multiselect(
    "Seleccionar variables",
    options=variables,
    default=variables
)

df = df[df["variable"].isin(var_select)]

# =========================================================
# 4. Gráfica
# =========================================================
st.title("Dashboard CD / CW - Gráficas con Límites")

if df.empty:
    st.warning("No hay datos para mostrar con estos filtros.")
    st.stop()

# Unir límites si existen
if not lim_df.empty:
    df = df.merge(lim_df, how="left", on=["maquina", "variable"])

# Gráfica Altair
chart = (
    alt.Chart(df)
    .mark_line()
    .encode(
        x="timestamp:T",
        y="valor:Q",
        color="variable:N",
        tooltip=["timestamp", "maquina", "variable", "valor", "LSL", "USL"]
    )
    .interactive()
)

st.altair_chart(chart, use_container_width=True)

# Líneas de control si existen
if "LSL" in df.columns and df["LSL"].notna().any():
    st.subheader("Límites aplicados")
    st.dataframe(df[["maquina", "variable", "LSL", "USL"]].drop_duplicates())

st.success("Dashboard cargado correctamente ✔")
