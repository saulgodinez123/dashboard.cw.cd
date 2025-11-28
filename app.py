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
