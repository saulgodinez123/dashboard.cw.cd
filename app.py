import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime

st.set_page_config(page_title="Dashboard CD / CW", layout="wide")

# ============================
#       CARGA DE BASES
# ============================

df_cd = pd.read_csv('CD_unificado.csv')
df_cw = pd.read_csv('CW_unificado.csv')

df_cd["area"] = "CD"
df_cw["area"] = "CW"

# Unifica CD + CW
df_all = pd.concat([df_cd, df_cw], ignore_index=True)

# ============================
#       CARGA DE LÍMITES
# ============================

df_limites = {}
excel_limites = pd.ExcelFile("Limites en tablas (1).xlsx")

# ============================================
#      GRÁFICAS ADICIONALES EN TABS
# ============================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Control Chart (X-MR)", 
    "Histograma con Límites", 
    "Boxplot (dispersión)",
    "Tendencia por Hora",
    "Pareto de Status"
])

# ------------------------------
# TAB 1 – CONTROL CHART (X-MR)
# ------------------------------
with tab1:
    st.subheader("Control Chart (X-MR)")

    if len(df_filt) > 3:
        df_cc = df_filt.sort_values("Date")
        df_cc["MR"] = df_cc[metrica_sel].diff().abs()

        fig, ax = plt.subplots(2, 1, figsize=(10, 7))

        # X Chart
        ax[0].plot(df_cc["Date"], df_cc[metrica_sel], marker="o")
        ax[0].set_title("X Chart")
        ax[0].grid(True)

        # MR Chart
        ax[1].plot(df_cc["Date"], df_cc["MR"], color="orange", marker="o")
        ax[1].set_title("MR Chart")
        ax[1].grid(True)

        st.pyplot(fig)
    else:
        st.warning("No hay suficientes datos para gráfica de control.")

# ------------------------------
# TAB 2 – HISTOGRAMA
# ------------------------------
with tab2:
    st.subheader("Histograma")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(df_filt[metrica_sel].dropna(), bins=20, alpha=0.7)

    # Límites si existen
    if not lim_row.empty:
        li = lim_row.iloc[0]["limite inferior"]
        ls = lim_row.iloc[0]["limite superior"]
        ax.axvline(li, color="green", linestyle="--", label="Límite inferior")
        ax.axvline(ls, color="red", linestyle="--", label="Límite superior")

    ax.set_xlabel(metrica_sel)
    ax.set_ylabel("Frecuencia")
    ax.legend()

    st.pyplot(fig)

# ------------------------------
# TAB 3 – BOXPLOT COMPARATIVO
# ------------------------------
with tab3:
    st.subheader("Boxplot de dispersión por máquina")

    df_box = df_all[
        (df_all["linea"] == linea_sel) &
        (df_all["categoria"] == categoria_sel)
    ]

    fig, ax = plt.subplots(figsize=(10, 5))
    df_box.boxplot(column=metrica_sel, by="maquina", ax=ax, grid=False, rot=45)

    ax.set_title(f"Dispersión de {metrica_sel} por máquina")
    ax.set_ylabel(metrica_sel)

    st.pyplot(fig)

# ------------------------------
# TAB 4 – TENDENCIA POR HORA
# ------------------------------
with tab4:
    st.subheader("Tendencia por Hora (promedio)")

    if "Hour" in df_filt.columns:
        df_temp = df_filt.copy()
        df_temp["Hour"] = pd.to_numeric(df_temp["Hour"], errors="coerce")

        df_hour = df_temp.groupby("Hour")[metrica_sel].mean().reset_index()

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(df_hour["Hour"], df_hour[metrica_sel], marker="o")
        ax.set_xlabel("Hora")
        ax.set_ylabel(metrica_sel)
        ax.grid(True)

        st.pyplot(fig)
    else:
        st.warning("No existe columna 'Hour' en los datos.")

# ------------------------------
# TAB 5 – PARETO DE STATUS
# ------------------------------
with tab5:
    st.subheader("Pareto de Status (fallas más comunes)")

    if "Status" in df_filt.columns:
        df_status = df_filt["Status"].value_counts().reset_index()
        df_status.columns = ["Status", "Count"]

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(df_status["Status"], df_status["Count"])
        ax.set_xticklabels(df_status["Status"], rotation=45, ha="right")
        ax.set_ylabel("Cantidad")

        st.pyplot(fig)
    else:
        st.warning("No existe columna Status en los datos.")


for sheet in excel_limites.sheet_names:
    df = excel_limites.parse(sheet)
    df.columns = df.columns.str.lower().str.strip()
    df_limites[sheet.lower()] = df


# ============================
#       FILTROS SIDEBAR
# ============================

st.sidebar.title("Filtros")

lineas = df_all['linea'].dropna().unique()
categorias = df_all['categoria'].dropna().unique()

linea_sel = st.sidebar.selectbox("Línea", lineas)
categoria_sel = st.sidebar.selectbox("Categoría", categorias)

maquinas_filtradas = df_all[
    (df_all["linea"] == linea_sel) &
    (df_all["categoria"] == categoria_sel)
]["maquina"].dropna().unique()

maquina_sel = st.sidebar.selectbox("Máquina", maquinas_filtradas)

# Lista de métricas numéricas
metricas = [
    col for col in df_all.columns
    if df_all[col].dtype in ["float64", "int64"]
    and col not in ["hour"]
]
metrica_sel = st.sidebar.selectbox("Métrica", metricas)

# FECHAS
fechas = pd.to_datetime(df_all['Date'], errors='coerce')
fechas_validas = fechas.dropna()

if len(fechas_validas) > 0:
    fecha_min, fecha_max = fechas_validas.min().date(), fechas_validas.max().date()
else:
    fecha_min = fecha_max = datetime.date.today()

rango_fechas = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max])


# ============================
#       FILTRO DE DATOS
# ============================

df_filt = df_all[
    (df_all['linea'] == linea_sel) &
    (df_all['categoria'] == categoria_sel) &
    (df_all['maquina'] == maquina_sel)
]

df_filt["Date"] = pd.to_datetime(df_filt["Date"], errors='coerce')

df_filt = df_filt[
    (df_filt["Date"] >= pd.to_datetime(rango_fechas[0])) &
    (df_filt["Date"] <= pd.to_datetime(rango_fechas[-1]))
]


# ============================
#       OBTENER LÍMITES
# ============================

# La hoja de límites es: ej. FTV7_CD → linea_sel_categoria_sel
clave_limite = f"{linea_sel}_{categoria_sel}".lower()

if clave_limite in df_limites:
    tabla_lim = df_limites[clave_limite]
    lim_row = tabla_lim[
        tabla_lim["variable"].str.lower() == metrica_sel.lower()
    ]
else:
    lim_row = pd.DataFrame()  # vacío si no existe hoja


# ============================
#       TÍTULO
# ============================

st.title(f"Dashboard de Calidad CD/CW")
st.subheader(f"{linea_sel} → {categoria_sel} → {maquina_sel}")
st.markdown(f"### Métrica: **{metrica_sel}**")


# ============================
#       GRÁFICA
# ============================

if not df_filt.empty:
    fig, ax = plt.subplots(figsize=(10, 4))

    ax.plot(df_filt["Date"], df_filt[metrica_sel], marker="o", linewidth=1, label=metrica_sel)

    # Dibujar límites si existen
    if not lim_row.empty:
        li = lim_row.iloc[0]["limite inferior"]
        ls = lim_row.iloc[0]["limite superior"]

        ax.axhline(ls, color="red", linestyle="--", label="Límite superior")
        ax.axhline(li, color="green", linestyle="--", label="Límite inferior")

    ax.set_xlabel("Fecha")
    ax.set_ylabel(metrica_sel)
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)

    st.pyplot(fig)
else:
    st.warning("⚠️ No hay datos filtrados para esta combinación.")


# ============================
#       TABLA DE DATOS
# ============================

st.write("### Datos filtrados")
st.dataframe(df_filt[["Date", "Time", "maquina", "linea", "categoria", metrica_sel]])
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Control Chart", 
    "Histograma", 
    "Boxplot", 
    "Tendencia por Hora",
    "Pareto de Status"
])

