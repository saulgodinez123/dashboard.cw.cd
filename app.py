import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import datetime

st.set_page_config(page_title="Dashboard CD / CW", layout="wide")

# -------------------------
# 1) CARGA DE DATOS
# -------------------------
df_cd = pd.read_csv("CD_unificado.csv")
df_cw = pd.read_csv("CW_unificado.csv")

df_cd["area"] = "CD"
df_cw["area"] = "CW"

df_all = pd.concat([df_cd, df_cw], ignore_index=True)

# Normalizar nombres de columnas principales para búsquedas (por si hay mayúsculas)
df_all.columns = df_all.columns.str.strip()

# -------------------------
# 2) CARGA DE LÍMITES (MULTI-HOJA)
# -------------------------
limites_path = "Limites en tablas (1).xlsx"
xls = pd.ExcelFile(limites_path)

# Diccionario: clave = nombre_de_hoja_lower (ej. 'fvt7_cd') -> dataframe con columnas normalizadas
df_limites_by_sheet = {}
for hoja in xls.sheet_names:
    df_sheet = xls.parse(hoja)
    # Normalizar nombres de columnas: quitar espacios y pasar a minúsculas
    df_sheet.columns = df_sheet.columns.str.strip().str.lower()
    # Asegurar que las columnas esperadas existan: 'variable', 'limite inferior', 'limite superior'
    # Si tienen nombres ligeramente distintos intentamos mapear
    cols = df_sheet.columns.tolist()
    # heurística para encontrar columnas
    # buscar columna que contenga 'variable' o 'var'
    var_col = next((c for c in cols if "variable" in c or "var" in c), None)
    li_col = next((c for c in cols if "limite" in c and "infer" in c), None)
    ls_col = next((c for c in cols if "limite" in c and "super" in c), None)
    # si no se detectan, tomar por posición
    if var_col is None and len(cols) >= 1:
        var_col = cols[0]
    if li_col is None and len(cols) >= 2:
        li_col = cols[1]
    if ls_col is None and len(cols) >= 3:
        ls_col = cols[2]
    # renombrar a estándar
    mapping = {}
    if var_col:
        mapping[var_col] = "variable"
    if li_col:
        mapping[li_col] = "limite_inferior"
    if ls_col:
        mapping[ls_col] = "limite_superior"
    df_sheet = df_sheet.rename(columns=mapping)
    # asegurar que existan las columnas finales
    if "variable" not in df_sheet.columns:
        st.warning(f"La hoja '{hoja}' no tiene columna de 'Variable' detectada. Revisa el formato.")
    if "limite_inferior" not in df_sheet.columns:
        df_sheet["limite_inferior"] = np.nan
    if "limite_superior" not in df_sheet.columns:
        df_sheet["limite_superior"] = np.nan
    # convertir límites a numéricos
    df_sheet["limite_inferior"] = pd.to_numeric(df_sheet["limite_inferior"], errors="coerce")
    df_sheet["limite_superior"] = pd.to_numeric(df_sheet["limite_superior"], errors="coerce")
    df_limites_by_sheet[hoja.strip().lower()] = df_sheet

# -------------------------
# 3) SIDEBAR - FILTROS
# -------------------------
st.sidebar.title("Filtros")

# Líneas, categorías, máquinas (asegurar orden estable)
lineas = sorted(df_all['linea'].dropna().unique().tolist())
categorias = sorted(df_all['categoria'].dropna().unique().tolist())

linea_sel = st.sidebar.selectbox("Línea", ["Todas"] + lineas)
categoria_sel = st.sidebar.selectbox("Categoría", ["Todas"] + categorias)

# Filtrar máquinas en base a selecciones previas
df_tmp = df_all.copy()
if linea_sel != "Todas":
    df_tmp = df_tmp[df_tmp["linea"] == linea_sel]
if categoria_sel != "Todas":
    df_tmp = df_tmp[df_tmp["categoria"] == categoria_sel]

maquinas = sorted(df_tmp["maquina"].dropna().unique().tolist())
maquina_sel = st.sidebar.selectbox("Máquina", ["Todas"] + maquinas)

# Detectar métricas numéricas (excluir columnas meta)
exclude_cols = {"maquina", "linea", "categoria", "date", "time", "area", "status", "serial_number", "model"}
numeric_cols = [c for c in df_all.columns if c.lower() not in exclude_cols and pd.api.types.is_numeric_dtype(df_all[c])]
numeric_cols = sorted(numeric_cols)
if not numeric_cols:
    st.error("No se encontraron columnas numéricas en el dataset.")
    st.stop()
metrica_sel = st.sidebar.selectbox("Métrica", numeric_cols)

# Rango de fechas
df_all['Date'] = pd.to_datetime(df_all['Date'], errors='coerce')
fechas_validas = df_all['Date'].dropna()
if len(fechas_validas) == 0:
    fecha_min = fecha_max = datetime.date.today()
else:
    fecha_min, fecha_max = fechas_validas.min().date(), fechas_validas.max().date()

rango_fechas = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max])

# Botones opcionales
mostrar_tabs = st.sidebar.checkbox("Mostrar gráficas avanzadas", value=True)

# -------------------------
# 4) FILTRAR DATAFRAME SEGÚN SELECCIÓN
# -------------------------
df_filt = df_all.copy()
if linea_sel != "Todas":
    df_filt = df_filt[df_filt["linea"] == linea_sel]
if categoria_sel != "Todas":
    df_filt = df_filt[df_filt["categoria"] == categoria_sel]
if maquina_sel != "Todas":
    df_filt = df_filt[df_filt["maquina"] == maquina_sel]

df_filt = df_filt[(df_filt["Date"] >= pd.to_datetime(rango_fechas[0])) & (df_filt["Date"] <= pd.to_datetime(rango_fechas[-1]))]

st.title("Dashboard CD / CW")
st.subheader(f"{linea_sel} • {categoria_sel} • {maquina_sel}")
st.markdown(f"**Métrica:** {metrica_sel}")

if df_filt.empty:
    st.warning("No hay registros para los filtros seleccionados.")
    st.stop()

# -------------------------
# 5) OBTENER LÍMITES PARA LA MÁQUINA Y MÉTRICA
# -------------------------
lim_row = pd.DataFrame()  # vacío por defecto
if maquina_sel != "Todas":
    # la clave de hoja debería ser, por ejemplo, "fvt7_cd"
    # Intentaremos buscar usando combinaciones posibles:
    posibles_claves = [
        f"{linea_sel}_{categoria_sel}".lower() if linea_sel != "Todas" and categoria_sel != "Todas" else None,
        maquina_sel.strip().lower(),
        f"{maquina_sel.strip().lower()}_{categoria_sel.strip().lower()}" if categoria_sel != "Todas" else None,
        f"{linea_sel.strip().lower()}_{maquina_sel.strip().lower()}" if linea_sel != "Todas" else None
    ]
    # remover Nones y duplicados
    posibles_claves = [k for k in posibles_claves if k]
    posibles_claves = list(dict.fromkeys(posibles_claves))
    for clave in posibles_claves:
        if clave in df_limites_by_sheet:
            tabla = df_limites_by_sheet[clave]
            # buscar métrica en la columna 'variable' (case-insensitive)
            if 'variable' in tabla.columns:
                lim_row = tabla[tabla['variable'].astype(str).str.lower() == metrica_sel.lower()]
                if not lim_row.empty:
                    break

# -------------------------
# 6) GRÁFICA PRINCIPAL (TENDENCIA) con límites si existen
# -------------------------
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(df_filt["Date"], df_filt[metrica_sel], marker='o', linewidth=1, label="Medición")

if not lim_row.empty:
    li = lim_row.iloc[0].get("limite_inferior", np.nan)
    ls = lim_row.iloc[0].get("limite_superior", np.nan)
    if pd.notna(ls):
        ax.axhline(ls, color='red', linestyle='--', label="Límite superior")
    if pd.notna(li):
        ax.axhline(li, color='green', linestyle='--', label="Límite inferior")

ax.set_xlabel("Fecha")
ax.set_ylabel(metrica_sel)
ax.set_title(f"Tendencia de {metrica_sel}")
ax.grid(alpha=0.3)
ax.legend()
st.pyplot(fig)

# -------------------------
# 7) KPIs simples
# -------------------------
col1, col2, col3 = st.columns(3)
col1.metric("Registros", len(df_filt))
col2.metric("Promedio", f"{df_filt[metrica_sel].mean():.3f}")
col3.metric("Desv. estándar", f"{df_filt[metrica_sel].std():.3f}")

# -------------------------
# 8) GRÁFICAS AVANZADAS EN TABS
# -------------------------
if mostrar_tabs:
    tabs = st.tabs(["Control X-MR", "Histograma", "Boxplot por Máquina", "Tendencia por Hora", "Pareto Status"])
    # TAB: X-MR
    with tabs[0]:
        st.subheader("Control Chart (X-MR)")
        if len(df_filt) >= 4:
            df_cc = df_filt.sort_values("Date").copy()
            df_cc["MR"] = df_cc[metrica_sel].diff().abs()
            fig_cc, (ax_x, ax_mr) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
            ax_x.plot(df_cc["Date"], df_cc[metrica_sel], marker='o')
            ax_x.set_title("X Chart")
            ax_x.grid(alpha=0.3)
            ax_mr.plot(df_cc["Date"], df_cc["MR"], color='orange', marker='o')
            ax_mr.set_title("MR Chart")
            ax_mr.grid(alpha=0.3)
            st.pyplot(fig_cc)
        else:
            st.info("Se requieren al menos 4 puntos para X-MR.")

    # TAB: HISTOGRAMA
    with tabs[1]:
        st.subheader("Histograma con límites")
        fig_h, ax_h = plt.subplots(figsize=(8, 4))
        ax_h.hist(df_filt[metrica_sel].dropna(), bins=25, alpha=0.7)
        if not lim_row.empty:
            if pd.notna(lim_row.iloc[0].get("limite_inferior")):
                ax_h.axvline(lim_row.iloc[0]["limite_inferior"], color='green', linestyle='--', label='Límite inferior')
            if pd.notna(lim_row.iloc[0].get("limite_superior")):
                ax_h.axvline(lim_row.iloc[0]["limite_superior"], color='red', linestyle='--', label='Límite superior')
            ax_h.legend()
        ax_h.set_xlabel(metrica_sel)
        ax_h.set_ylabel("Frecuencia")
        st.pyplot(fig_h)

    # TAB: BOXPLOT por máquina
    with tabs[2]:
        st.subheader("Boxplot por Máquina (misma línea/categoría)")
        df_box = df_all.copy()
        df_box = df_box[(df_box["linea"] == linea_sel) & (df_box["categoria"] == categoria_sel)]
        if not df_box.empty:
            fig_b, ax_b = plt.subplots(figsize=(12, 5))
            # preparar lista de valores por máquina en orden
            maquinas_order = sorted(df_box["maquina"].dropna().unique().tolist())
            data_to_plot = [df_box[df_box["maquina"] == m][metrica_sel].dropna().values for m in maquinas_order]
            ax_b.boxplot(data_to_plot, labels=maquinas_order, showfliers=False)
            ax_b.set_xticklabels(maquinas_order, rotation=45, ha='right')
            ax_b.set_ylabel(metrica_sel)
            ax_b.set_title(f"Boxplot de {metrica_sel} por máquina")
            st.pyplot(fig_b)
        else:
            st.info("No hay datos para boxplot.")

    # TAB: TENDENCIA POR HORA
    with tabs[3]:
        st.subheader("Tendencia por Hora (promedio)")
        if "Hour" in df_filt.columns or "Hour" in df_all.columns or "hour" in df_all.columns:
            # intentar diferentes nombres de columnas de hora
            hour_col = None
            for c in ["Hour", "hour", "Hour "]:
                if c in df_filt.columns:
                    hour_col = c
                    break
            if hour_col is None:
                st.info("No se encontró columna 'Hour' en los datos.")
            else:
                df_hour = df_filt.copy()
                df_hour[hour_col] = pd.to_numeric(df_hour[hour_col], errors='coerce')
                df_hour = df_hour.dropna(subset=[hour_col])
                df_hour_group = df_hour.groupby(hour_col)[metrica_sel].mean().reset_index()
                fig_h2, ax_h2 = plt.subplots(figsize=(8, 4))
                ax_h2.plot(df_hour_group[hour_col], df_hour_group[metrica_sel], marker='o')
                ax_h2.set_xlabel("Hour")
                ax_h2.set_ylabel(metrica_sel)
                ax_h2.grid(alpha=0.3)
                st.pyplot(fig_h2)
        else:
            st.info("No hay columna 'Hour' en los datos para este gráfico.")

    # TAB: PARETO de Status
    with tabs[4]:
        st.subheader("Pareto de Status")
        if "Status" in df_filt.columns:
            df_stat = df_filt["Status"].fillna("UNKNOWN").value_counts().reset_index()
            df_stat.columns = ["Status", "Count"]
            fig_p, ax_p = plt.subplots(figsize=(8, 4))
            ax_p.bar(df_stat["Status"], df_stat["Count"])
            ax_p.set_xticklabels(df_stat["Status"], rotation=45, ha='right')
            ax_p.set_ylabel("Count")
            st.pyplot(fig_p)
        else:
            st.info("No existe columna 'Status' en los datos.")

# -------------------------
# 9) TABLA Y DESCARGA
# -------------------------
st.markdown("### Datos filtrados")
st.dataframe(df_filt[["Date", "Time"] + ["maquina", "linea", "categoria", metrica_sel]].drop_duplicates().reset_index(drop=True))

csv_bytes = df_filt.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Descargar datos filtrados (CSV)", csv_bytes, "datos_filtrados.csv", "text/csv")

import seaborn as sns

st.subheader("Mapa de calor de métricas (Heatmap)")

# Copia solo las columnas numéricas
df_num = df_filt.select_dtypes(include=['float64', 'int64']).copy()

# Agregar fecha como index para verlo por día
df_num['Date'] = df_filt['Date']
df_num = df_num.groupby('Date').mean()  # promedio diario

# Si hay demasiadas columnas, limitar a las top 30 por varianza
if df_num.shape[1] > 30:
    var_top = df_num.var().sort_values(ascending=False).head(30).index
    df_num = df_num[var_top]
    st.info("Mostrando solo las 30 métricas con mayor variabilidad.")

# Crear figura
fig_hm, ax_hm = plt.subplots(figsize=(14, 6))
sns.heatmap(df_num.T, cmap="coolwarm", ax=ax_hm)

ax_hm.set_xlabel("Fecha")
ax_hm.set_ylabel("Métricas")
ax_hm.set_title("Heatmap de métricas numéricas")
plt.tight_layout()

st.pyplot(fig_hm)
