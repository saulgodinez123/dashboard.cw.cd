# app.py
import streamlit as st
import pandas as pd
import altair as alt
import re

st.set_page_config(page_title="Dashboard CD/CW (robusto)", layout="wide")


# ---------------------------
# Helpers
# ---------------------------
def normalize_name(s: str) -> str:
    """Lower, remove non-alnum and underscores -> used to match variable names between sources."""
    if pd.isna(s):
        return ""
    s = str(s).lower()
    s = re.sub(r"[^0-9a-z]+", "", s)
    return s


def find_datetime_columns(cols):
    """Return (date_col, time_col) if found among possible names."""
    possible_date = ["date", "day-month-year", "day_month_year", "fecha", "fecha_hora", "daymonthyear"]
    possible_time = ["time", "hour_min_seg", "hour_min_seg", "hora", "hour", "time_stamp", "hora_min_seg"]
    date_col = None
    time_col = None
    for c in cols:
        cn = c.lower()
        if cn in possible_date and date_col is None:
            date_col = c
        if cn in possible_time and time_col is None:
            time_col = c
    # also if there's a single datetime-like column name
    for c in cols:
        cn = c.lower()
        if date_col is None and ("timestamp" in cn or "date_time" in cn or "datetime" in cn):
            date_col = c
            time_col = None
            break
    return date_col, time_col


def detect_variable_columns(df, exclude_cols):
    """Return list of columns considered variables:
       - not in exclude_cols
       - numeric (at least 50% convertible to numeric)
    """
    vars_candidates = []
    for c in df.columns:
        if c in exclude_cols:
            continue
        # try convert to numeric, compute fraction non-null
        conv = pd.to_numeric(df[c], errors="coerce")
        frac_numeric = conv.notna().mean()
        if frac_numeric >= 0.5:
            vars_candidates.append(c)
    return vars_candidates


# ---------------------------
# Load data (with caching)
# ---------------------------
@st.cache_data
def load_data():
    # Cargar archivos (asumimos que están en la raíz del repo)
    cd = pd.read_csv("CD_unificado.csv", low_memory=False)
    cw = pd.read_csv("CW_unificado.csv", low_memory=False)

    # Forzar columnas lowercase for easier matching
    cd.columns = [c.strip() for c in cd.columns]
    cw.columns = [c.strip() for c in cw.columns]

    # Add tipo
    cd["tipo"] = "CD"
    cw["tipo"] = "CW"

    # keep raw
    return cd, cw


# ---------------------------
# Start
# ---------------------------
st.title("📊 Dashboard CD & CW — robusto (auto-detección)")

st.markdown(
    "Este script detecta automáticamente las columnas de variables (numéricas), crea "
    "`timestamp` a partir de `date` + `time` si están presentes, y transforma las tablas a formato long."
)

cd_raw, cw_raw = load_data()

# show columns quickly (helpful)
with st.expander("👁️ Ver columnas detectadas (CD)"):
    st.write(cd_raw.columns.tolist())
with st.expander("👁️ Ver columnas detectadas (CW)"):
    st.write(cw_raw.columns.tolist())

# ---------------------------
# Normalize column names to lowercase single words for internal use
# ---------------------------
cd = cd_raw.copy()
cw = cw_raw.copy()

# Find sensible id columns present
common_id_candidates = [
    "maquina", "machine", "linea", "line", "serial_number", "serial", "model", "date", "time",
    "day-month-year", "hour_min_seg", "timestamp", "fecha", "hora"
]

def choose_column_by_names(df, possible_names):
    for n in possible_names:
        for c in df.columns:
            if c.lower() == n:
                return c
    return None

# Try to find 'maquina' column in both frames
maquina_col_cd = choose_column_by_names(cd, ["maquina", "machine", "line", "linea"])
maquina_col_cw = choose_column_by_names(cw, ["maquina", "machine", "line", "linea"])

if not maquina_col_cd or not maquina_col_cw:
    # If one missing, try to inform user and stop
    st.error("No se encontró una columna con el nombre 'maquina' (o 'machine' / 'line' / 'linea') en uno de los CSV. "
             "Por favor verifica el nombre exacto de la columna que identifica la máquina en cada CSV.")
    st.stop()

# Date/time detection
date_cd, time_cd = find_datetime_columns(cd.columns)
date_cw, time_cw = find_datetime_columns(cw.columns)

# If timestamp present as single column, treat accordingly
# Prepare copies and standardize id column names
cd_proc = cd.copy()
cw_proc = cw.copy()

cd_proc = cd_proc.rename(columns={maquina_col_cd: "maquina"})
cw_proc = cw_proc.rename(columns={maquina_col_cw: "maquina"})

# timestamp creation function
def create_timestamp_column(df, date_col, time_col):
    if date_col and (date_col in df.columns):
        if time_col and (time_col in df.columns):
            # combine
            ts = pd.to_datetime(df[date_col].astype(str) + " " + df[time_col].astype(str), errors="coerce")
            df["timestamp"] = ts
        else:
            # maybe single datetime column or only date
            ts = pd.to_datetime(df[date_col].astype(str), errors="coerce")
            df["timestamp"] = ts
    else:
        # try to build from other names if exist
        # fallback: try any column that looks like timestamp
        for c in df.columns:
            if "timestamp" in c.lower() or "date_time" in c.lower() or "datetime" in c.lower():
                df["timestamp"] = pd.to_datetime(df[c], errors="coerce")
                return df
        # no timestamp
        df["timestamp"] = pd.NaT
    return df

cd_proc = create_timestamp_column(cd_proc, date_cd, time_cd)
cw_proc = create_timestamp_column(cw_proc, date_cw, time_cw)

# ---------------------------
# Detect variable columns automatically (numeric-ish)
# ---------------------------
# Exclude common non-variable columns
exclude_base = set(["maquina", "tipo", "timestamp","date","time","serial_number","serial","model","status",
                    "hour","yield","ref","start_boot","power_up","powerup","setboard","totalTime","total_time",
                    "linea","categoria","check pn renessas","mac","said"])

# Add any 'unnamed' columns to exclude
for c in list(cd_proc.columns) + list(cw_proc.columns):
    if c.lower().startswith("unnamed"):
        exclude_base.add(c)

vars_cd = detect_variable_columns(cd_proc, exclude_base)
vars_cw = detect_variable_columns(cw_proc, exclude_base)

# If none detected, try a fallback: detect columns with 'get' or 'angle' in name
if len(vars_cd) == 0:
    vars_cd = [c for c in cd_proc.columns if re.search(r"get|angle|encoder|touch|audio|screen|lcd|rssi", c.lower())]
if len(vars_cw) == 0:
    vars_cw = [c for c in cw_proc.columns if re.search(r"get|angle|encoder|touch|audio|screen|lcd|rssi", c.lower())]

if len(vars_cd) == 0 and len(vars_cw) == 0:
    st.error("No se detectaron columnas de variables numéricas en ninguno de los CSV. "
             "Revise los archivos o indique qué columnas son variables.")
    st.stop()

# ---------------------------
# Melt to long format
# ---------------------------
def melt_to_long(df, var_cols, tipo_label):
    # ensure columns exist
    var_cols = [c for c in var_cols if c in df.columns]
    id_vars = [c for c in ["maquina","timestamp"] if c in df.columns]
    if len(var_cols) == 0:
        return pd.DataFrame(columns=["maquina","variable","valor","timestamp","tipo"])
    long = df.melt(id_vars=id_vars, value_vars=var_cols, var_name="variable", value_name="valor")
    long["tipo"] = tipo_label
    # try convert valor to numeric
    long["valor"] = pd.to_numeric(long["valor"], errors="coerce")
    # ensure timestamp exists
    if "timestamp" not in long.columns:
        long["timestamp"] = pd.NaT
    return long

cd_long = melt_to_long(cd_proc, vars_cd, "CD")
cw_long = melt_to_long(cw_proc, vars_cw, "CW")

# concat both
all_long = pd.concat([cd_long, cw_long], ignore_index=True)

# Normalize variable names (for matching with limits)
all_long["variable_norm"] = all_long["variable"].astype(str).apply(normalize_name)

# ---------------------------
# Load limites Excel and normalize
# ---------------------------
try:
    limites = pd.read_excel("Limites en tablas (2).xlsx", engine="openpyxl")
except Exception as e:
    st.error(f"No se pudo leer 'Limites en tablas (2).xlsx': {e}")
    st.stop()

# Normalize limite columns: try to find columns automatically
lim_cols = [c.strip() for c in limites.columns]
limites.columns = lim_cols

# Heuristics to find columns in limites
# Look for CD_* and CW_* structure or generic columns
# We'll try possible names
def find_lim_col(df_cols, possible):
    for p in possible:
        for c in df_cols:
            if c.lower().strip() == p:
                return c
    return None

# Try common names
cd_machine_col = find_lim_col(lim_cols, ["cd_maquina","cd maquina","cd_maquina","maquina_cd","maquina"])
cw_machine_col = find_lim_col(lim_cols, ["cw_maquina","cw maquina","cw_maquina","maquina_cw","maquina"])
# fallback: use first column for machine if nothing matches
if not cd_machine_col:
    cd_machine_col = lim_cols[0]
if not cw_machine_col:
    # try to pick one further in list
    if len(lim_cols) > 4:
        cw_machine_col = lim_cols[4]
    else:
        cw_machine_col = lim_cols[0]

# Attempt to locate variable and lim_inf/lim_sup for cd and cw
# We'll create a normalized dataframe with columns: maquina, variable, lim_inf, lim_sup, tipo
lim_rows = []

# Try to detect pattern 8 columns (as you described earlier)
if len(lim_cols) >= 8:
    try:
        # assume structure: CD_maquina, CD_variable, CD_lim_inf, CD_lim_sup, CW_maquina, CW_variable, CW_lim_inf, CW_lim_sup
        cd_m = lim_cols[0]
        cd_v = lim_cols[1]
        cd_li = lim_cols[2]
        cd_ls = lim_cols[3]
        cw_m = lim_cols[4]
        cw_v = lim_cols[5]
        cw_li = lim_cols[6]
        cw_ls = lim_cols[7]

        for _, r in limites.iterrows():
            # CD row
            m = r.get(cd_m)
            v = r.get(cd_v)
            li = r.get(cd_li)
            ls = r.get(cd_ls)
            if pd.notna(m) and pd.notna(v):
                lim_rows.append({
                    "maquina": str(m).strip(),
                    "variable": str(v).strip(),
                    "lim_inf": pd.to_numeric(li, errors="coerce"),
                    "lim_sup": pd.to_numeric(ls, errors="coerce"),
                    "tipo": "CD",
                    "variable_norm": normalize_name(v)
                })
            # CW row
            m2 = r.get(cw_m)
            v2 = r.get(cw_v)
            li2 = r.get(cw_li)
            ls2 = r.get(cw_ls)
            if pd.notna(m2) and pd.notna(v2):
                lim_rows.append({
                    "maquina": str(m2).strip(),
                    "variable": str(v2).strip(),
                    "lim_inf": pd.to_numeric(li2, errors="coerce"),
                    "lim_sup": pd.to_numeric(ls2, errors="coerce"),
                    "tipo": "CW",
                    "variable_norm": normalize_name(v2)
                })
    except Exception:
        # fallback below
        pass

# If no rows parsed, try generic rows: expect columns maquina, variable, lim_inf, lim_sup, tipo
if len(lim_rows) == 0:
    # Lowercase keys for detection
    low = [c.lower() for c in lim_cols]
    # attempt to detect
    col_maq = None
    col_var = None
    col_li = None
    col_ls = None
    col_tipo = None
    # heuristics
    for c in lim_cols:
        lc = c.lower()
        if "maquina" in lc or "machine" in lc:
            col_maq = c
        if "variable" in lc:
            col_var = c
        if "lim_inf" in lc or "liminf" in lc or "lower" in lc or "lim inferior" in lc:
            col_li = c
        if "lim_sup" in lc or "limsup" in lc or "upper" in lc or "lim superior" in lc:
            col_ls = c
        if "tipo" in lc or "cd" in lc and "cw" in lc:
            col_tipo = c
    # If we found at least maquina and variable
    if col_maq and col_var and col_li and col_ls:
        for _, r in limites.iterrows():
            lim_rows.append({
                "maquina": str(r.get(col_maq)).strip(),
                "variable": str(r.get(col_var)).strip(),
                "lim_inf": pd.to_numeric(r.get(col_li), errors="coerce"),
                "lim_sup": pd.to_numeric(r.get(col_ls), errors="coerce"),
                "tipo": str(r.get(col_tipo)).strip() if col_tipo else None,
                "variable_norm": normalize_name(r.get(col_var))
            })

lim_df = pd.DataFrame(lim_rows)
if lim_df.empty:
    st.warning("No se pudieron parsear límites desde el Excel con la heurística. Verifica el formato del archivo 'Limites en tablas (2).xlsx'.")
else:
    st.success(f"Se cargaron {len(lim_df)} reglas de límite desde el Excel.")

# ---------------------------
# UI: filtros
# ---------------------------
st.sidebar.header("Filtros")

tipo_sel = st.sidebar.multiselect("Selecciona tipo (CD y/o CW):", options=["CD", "CW"], default=["CD", "CW"])
# build filtered df
df_filtered = all_long[all_long["tipo"].isin(tipo_sel)]

# máquinas disponibles tras filtro
maquinas = sorted(df_filtered["maquina"].dropna().unique())
if len(maquinas) == 0:
    st.error("No hay máquinas disponibles para la selección de tipo. Revisa filtros/archivos.")
    st.stop()

maquina_select = st.sidebar.multiselect("Máquinas (varias):", maquinas, default=maquinas[:2])

df_m = df_filtered[df_filtered["maquina"].isin(maquina_select)]

# variables detected for the selected machines
vars_available = sorted(df_m["variable"].dropna().unique())

if len(vars_available) == 0:
    st.warning("No hay variables detectadas para la selección de máquina/tipo.")
    vars_available = []

variables_select = st.sidebar.multiselect("Variables a visualizar:", options=vars_available, default=vars_available)

# time range
min_ts = df_m["timestamp"].min()
max_ts = df_m["timestamp"].max()
if pd.notna(min_ts) and pd.notna(max_ts):
    time_range = st.sidebar.slider("Rango de tiempo", value=(min_ts, max_ts), min_value=min_ts, max_value=max_ts)
    df_m = df_m[(df_m["timestamp"] >= time_range[0]) & (df_m["timestamp"] <= time_range[1])]

# final dataset to plot
df_plot = df_m[df_m["variable"].isin(variables_select)].copy()

# ---------------------------
# Main area
# ---------------------------
st.subheader("Datos filtrados")
st.write(f"Registros: {len(df_plot)}")
st.dataframe(df_plot.head(200))

# ---------------------------
# Graficar (Altair)
# ---------------------------
st.subheader("Gráfica comparativa")
if df_plot.empty:
    st.info("No hay datos para mostrar con la selección actual.")
else:
    # Color by tipo if multiple selected, otherwise color by maquina or variable
    color_field = "tipo" if len(df_plot["tipo"].unique()) > 1 else "variable"
    chart = alt.Chart(df_plot).mark_line().encode(
        x=alt.X("timestamp:T", title="Timestamp"),
        y=alt.Y("valor:Q", title="Valor"),
        color=alt.Color(color_field + ":N", title=color_field.capitalize()),
        strokeDash="maquina:N",
        tooltip=["timestamp:T", "maquina:N", "tipo:N", "variable:N", "valor:Q"]
    ).interactive().properties(height=400)
    st.altair_chart(chart, use_container_width=True)

# ---------------------------
# Mostrar límites aplicables
# ---------------------------
st.subheader("Límites aplicables (matched)")

# normalize selected variables for matching
selected_norm = [normalize_name(v) for v in variables_select]

lim_match = lim_df = lim_df = lim_df = lim_df = lim_df = None  # placeholder to avoid lint
# build match
if not lim_df.empty:
    # match by maquina, tipo, variable_norm
    lim_match = lim_df = lim_df = pd.DataFrame()  # init
    lim_match_rows = []
    for maq in maquina_select:
        for vn in selected_norm:
            for _, r in lim_df.iterrows():
                pass  # placeholder
# We'll do a simpler construction using lim_df created earlier
if not lim_df.empty:
    lim_match = lim_df[
        (lim_df["maquina"].isin(maquina_select)) &
        (lim_df["variable_norm"].isin(selected_norm)) &
        (lim_df["tipo"].isin(tipo_sel))
    ]
else:
    lim_match = pd.DataFrame(columns=["maquina","variable","lim_inf","lim_sup","tipo"])

if lim_match.empty:
    st.info("No se encontraron límites aplicables para la selección (o el Excel no tiene coincidencias).")
else:
    st.dataframe(lim_match)

# ---------------------------
# CSV download
# ---------------------------
st.subheader("Descargar datos filtrados")
def convert_df_to_csv_bytes(df_):
    return df_.to_csv(index=False).encode("utf-8")

if not df_plot.empty:
    csv_bytes = convert_df_to_csv_bytes(df_plot)
    st.download_button("📥 Descargar CSV (datos filtrados)", csv_bytes, file_name="datos_filtrados.csv", mime="text/csv")
else:
    st.info("No hay datos para descargar con la selección actual.")

# ---------------------------
# Final notes
# ---------------------------
st.markdown("""
**Notas y recomendaciones**
- Si tus columnas de fecha o tiempo tienen nombres distintos, revisa los expanders arriba para ver los nombres detectados.
- Si necesitas que alguna columna concreta sea considerada 'maquina' o 'timestamp', indícamelo y ajusto el heurístico.
- Si el archivo de límites no se parseó correctamente, comparte una captura del Excel (cabeceras) y lo adapto exactamente.
""")
