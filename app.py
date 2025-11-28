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

    limites_total = pd.concat([limites_cd, limites_cw], ignore_index=True)
    # normalized variable name to help matching
    limites_total["variable_norm"] = limites_total["variable"].astype(str).str.replace("_","").str.replace(" ","").str.lower()

    return cd, cw, limites_total

cd_raw, cw_raw, limites_df = load_data()

# --------------------------------
# NORMALIZADOR DE VARIABLES
# --------------------------------
def normalizar_variable(v):
    return str(v).replace("_", "").replace(" ", "").strip().lower()

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

cd_df = melt_df(cd_raw, vars_cd) if len(vars_cd)>0 else pd.DataFrame(columns=["maquina","Date","Time","variable","valor","timestamp"])
cw_df = melt_df(cw_raw, vars_cw) if len(vars_cw)>0 else pd.DataFrame(columns=["maquina","Date","Time","variable","valor","timestamp"])

# ensure numeric
cd_df["valor"] = pd.to_numeric(cd_df["valor"], errors="coerce")
cw_df["valor"] = pd.to_numeric(cw_df["valor"], errors="coerce")

# --------------------------------
# UI STREAMLIT
# --------------------------------
st.title("📊 Dashboard de Límites CD / CW")

tipo = st.sidebar.selectbox("Tipo de datos", ["CD", "CW"])
df = cd_df if tipo == "CD" else cw_df

# Selección de máquina
maquinas = sorted(df["maquina"].dropna().unique())
if not maquinas:
    st.error("No se encontraron máquinas en los datos. Revisa tus CSVs.")
    st.stop()

maq = st.sidebar.selectbox("Máquina", maquinas)
df_m = df[df["maquina"] == maq]

# SELECCIÓN DE VARIABLE BASADA EN LÍMITES (prioriza límites)
vars_limite = limites_df[
    (limites_df["maquina"].astype(str).str.lower() == str(maq).lower()) &
    (limites_df["tipo"] == tipo)
]["variable"].unique()

# fallback a variables en datos si límites no tienen nada
if len(vars_limite) == 0:
    vars_limite = df_m["variable"].dropna().unique()

vars_limite = sorted(vars_limite)
var = st.sidebar.selectbox("Variable", vars_limite)

# Filtrar usando el nombre (normalizar al comparar)
df_v = df_m[df_m["variable"].astype(str).str.lower() == str(var).lower()].copy()
# keep original Time/Date columns present in your CSVs
df_v["valor"] = pd.to_numeric(df_v["valor"], errors="coerce")
df_v = df_v.dropna(subset=["valor"])

# --------------------------------
# EXTRAER LÍMITES (usando variable normalizada)
# --------------------------------
var_norm = normalizar_variable(var)
lim = limites_df[
    (limites_df["maquina"].astype(str).str.lower() == str(maq).lower()) &
    (limites_df["variable_norm"] == var_norm) &
    (limites_df["tipo"] == tipo)
]

lim_inf = lim["lim_inf"].values[0] if not lim.empty else None
lim_sup = lim["lim_sup"].values[0] if not lim.empty else None

# --------------------------------
# MARCAR OUTLIERS / FUERA DE LÍMITES (cuento correcto)
# --------------------------------
# safe default masks
if df_v.empty:
    mask_out = pd.Series([], dtype=bool)
else:
    if (lim_inf is None) and (lim_sup is None):
        # no limits -> none out
        mask_out = pd.Series([False]*len(df_v), index=df_v.index)
    elif (lim_inf is None):
        mask_out = df_v["valor"] > lim_sup
    elif (lim_sup is None):
        mask_out = df_v["valor"] < lim_inf
    else:
        mask_out = (df_v["valor"] < lim_inf) | (df_v["valor"] > lim_sup)

df_v["fuera"] = mask_out
count_out = int(mask_out.sum()) if len(mask_out)>0 else 0
pct_out = (count_out / len(df_v) * 100) if len(df_v)>0 else 0.0

# --------------------------------
# KPIs (muestra count + %)
# --------------------------------
st.subheader("📌 Indicadores clave (KPI)")

col1, col2, col3 = st.columns(3)

promedio = df_v["valor"].mean() if not df_v.empty else 0.0
ultimo = df_v["valor"].iloc[-1] if not df_v.empty else 0.0

col1.metric("Promedio", f"{promedio:.2f}")
col2.metric("Último valor", f"{ultimo:.2f}")
col3.metric("Fuera de límites", f"{count_out} pts ({pct_out:.1f}%)")

# --------------------------------
# GRÁFICAS
# --------------------------------
st.subheader("📈 Gráfico de Control")

if df_v.empty:
    st.warning("No hay datos válidos para esta variable.")
else:
    fig = px.line(df_v, x="timestamp", y="valor", title=f"{maq} — {var}", markers=False)
    # add media
    media = df_v["valor"].mean()
    fig.add_hline(y=media, line_dash="solid", annotation_text="Media", annotation_position="top left")
    # add limits if exist
    if lim_inf is not None:
        fig.add_hline(y=lim_inf, line_dash="dot", annotation_text="Límite Inferior", annotation_position="bottom left")
    if lim_sup is not None:
        fig.add_hline(y=lim_sup, line_dash="dot", annotation_text="Límite Superior", annotation_position="top left")
    # highlight outliers
    df_out = df_v[df_v["fuera"]]
    if not df_out.empty:
        fig.add_scatter(x=df_out["timestamp"], y=df_out["valor"], mode="markers", marker=dict(color="red", size=10), name="Fuera de límites")
    st.plotly_chart(fig, use_container_width=True)

    # show outliers table for inspection
    if not df_out.empty:
        st.markdown("#### ⚠ Valores fuera de límites")
        st.dataframe(df_out.reset_index(drop=True))

# --------------------------------
# HISTOGRAMA, BOXPLOT, SCATTER y POR HORA (opcional)
# --------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["Histograma", "Boxplot", "Scatter", "Promedio por hora"])

with tab1:
    if df_v.empty:
        st.info("No hay datos para histograma.")
    else:
        fig_hist = px.histogram(df_v, x="valor", nbins=30, title="Histograma")
        if lim_inf is not None:
            fig_hist.add_vline(x=lim_inf, line_color="red")
        if lim_sup is not None:
            fig_hist.add_vline(x=lim_sup, line_color="red")
        st.plotly_chart(fig_hist, use_container_width=True)

with tab2:
    if df_v.empty:
        st.info("No hay datos para boxplot.")
    else:
        fig_box = px.box(df_v, y="valor", points="outliers", title="Boxplot")
        st.plotly_chart(fig_box, use_container_width=True)

with tab3:
    if df_v.empty:
        st.info("No hay datos para scatter.")
    else:
        fig_sc = px.scatter(df_v, x="timestamp", y="valor", title="Scatter")
        if lim_inf is not None:
            fig_sc.add_hline(y=lim_inf, line_color="red", line_dash="dot")
        if lim_sup is not None:
            fig_sc.add_hline(y=lim_sup, line_color="red", line_dash="dot")
        st.plotly_chart(fig_sc, use_container_width=True)

with tab4:
    if df_v.empty:
        st.info("No hay datos para agrupar por hora.")
    else:
        try:
            df_v["hour"] = pd.to_datetime(df_v["Time"], format="%H:%M:%S", errors="coerce").dt.hour
            df_hour = df_v.groupby("hour", as_index=False)["valor"].mean().dropna()
            fig_hour = px.bar(df_hour, x="hour", y="valor", title="Promedio por hora")
            st.plotly_chart(fig_hour, use_container_width=True)
        except Exception:
            st.info("Formato de Time no reconocido para agrupación por hora.")

# --------------------------------
# Tabla de datos y límites aplicados
# --------------------------------
st.markdown("### 📋 Datos filtrados")
st.dataframe(df_v.reset_index(drop=True))

st.markdown("### 📘 Límites aplicados (según Excel)")
if not lim.empty:
    st.dataframe(lim.reset_index(drop=True))
else:
    st.info("No se encontraron límites para esta selección.")
