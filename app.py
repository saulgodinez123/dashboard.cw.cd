import streamlit as st
import pandas as pd
import sys
import os
from io import StringIO, BytesIO

st.set_page_config(page_title="Dashboard - Límites", layout="wide")

expected_cols = ["maquina", "variable", "LimiteInferior", "LimiteSuperior"]

def normalize_df_limites(df: pd.DataFrame) -> pd.DataFrame:
    """
    Intenta normalizar df para que tenga exactamente las columnas:
    ["maquina", "variable", "LimiteInferior", "LimiteSuperior"]

    Realiza varios intentos automáticos y, si no puede, lanza ValueError.
    """
    cols = df.columns.tolist()
    n_actual = len(cols)

    # Caso ideal
    if n_actual == len(expected_cols):
        df = df.copy()
        df.columns = expected_cols
        return df

    # Intento 1: quitar columnas "Unnamed" típicas (índice incluido al guardar CSV)
    unnamed = [c for c in cols if str(c).startswith("Unnamed") or str(c).strip() == ""]
    if unnamed and (n_actual - len(unnamed)) == len(expected_cols):
        df = df.drop(columns=unnamed).copy()
        df.columns = expected_cols
        return df

    # Intento 2: si la primera columna parece un índice numérico 0..n-1 y sobra una columna
    try:
        first_col = df.iloc[:, 0]
        if pd.api.types.is_integer_dtype(first_col) or pd.api.types.is_float_dtype(first_col):
            # Comprobar si los primeros valores son 0,1,2,...
            sample = first_col.dropna().iloc[:10].astype(int).tolist()
            if sample == list(range(len(sample))):
                df2 = df.iloc[:, 1:].copy()
                if df2.shape[1] == len(expected_cols):
                    df2.columns = expected_cols
                    return df2
    except Exception:
        pass

    # Intento 3: mapear por palabras clave en nombres de columnas (ignorando mayúsculas y espacios)
    cleaned = [str(c).strip() for c in cols]
    mapped = []
    for c in cleaned:
        c_low = c.lower().replace(" ", "").replace("_", "")
        if "maquina" in c_low or "maquin" in c_low or "machine" in c_low:
            mapped.append("maquina")
        elif "variable" in c_low or "var" == c_low:
            mapped.append("variable")
        elif "inferior" in c_low or "min" in c_low:
            mapped.append("LimiteInferior")
        elif "superior" in c_low or "max" in c_low:
            mapped.append("LimiteSuperior")
        else:
            mapped.append(None)
    if all(m is not None for m in mapped) and len(mapped) == len(expected_cols):
        df2 = df.copy()
        df2.columns = mapped
        return df2

    # No se pudo normalizar automáticamente
    raise ValueError(
        f"No se pueden asignar las columnas esperadas {expected_cols}. "
        f"El DataFrame tiene {n_actual} columnas. Columnas actuales: {cols}."
    )

def load_csv_from_uploaded_or_default(uploaded_file):
    """
    Lee CSV desde el archivo subido por el usuario o desde rutas por defecto.
    Devuelve un DataFrame o None si no se encontró ninguno.
    """
    if uploaded_file is not None:
        try:
            # Pandas detectará correctamente si es bytes o buffer
            return pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Error al leer el archivo subido: {e}")
            return None

    # Intentar rutas por defecto
    candidates = ["data/limites.csv", "limites.csv", "./data/limites.csv"]
    for path in candidates:
        if os.path.exists(path):
            try:
                return pd.read_csv(path)
            except Exception as e:
                st.error(f"Error al leer {path}: {e}")
                return None
    return None

# --- Interfaz ---
st.title("Dashboard - Configuración de límites")

st.markdown("Sube el CSV de límites o deja que la app busque ./data/limites.csv o ./limites.csv")

uploaded = st.file_uploader("Sube el CSV de límites (opcional)", type=["csv"])

df_limites = load_csv_from_uploaded_or_default(uploaded)

if df_limites is None:
    st.info("No se ha cargado ningún CSV aún. Sube un archivo o coloca ./data/limites.csv en el repositorio.")
    st.stop()

st.markdown("## Vista previa del CSV original")
with st.expander("Mostrar CSV original"):
    st.write("shape:", df_limites.shape)
    st.write(df_limites.head())

# Intentar normalizar automáticamente
normalized = None
error_msg = None
try:
    normalized = normalize_df_limites(df_limites)
except Exception as exc:
    error_msg = str(exc)

if normalized is not None:
    st.success("El DataFrame se normalizó correctamente a las columnas esperadas.")
    st.write("shape:", normalized.shape)
    st.write("columns:", normalized.columns.tolist())
    st.dataframe(normalized.head())
    # Aquí continúa el resto de la lógica de tu app usando `normalized` como df_limites
    df_limites = normalized
    # Ejemplo simple: mostrar conteo por máquina
    st.markdown("### Conteo por máquina")
    try:
        st.bar_chart(df_limites["maquina"].value_counts())
    except Exception:
        st.info("No se pudo graficar conteo por máquina (revisa los valores).")
else:
    st.error("No se pudo normalizar automáticamente el DataFrame.")
    st.write("Detalle del intento:", error_msg)
    st.markdown("### Información para depuración")
    st.write("shape:", df_limites.shape)
    st.write("columns:", df_limites.columns.tolist())
    st.write(df_limites.head())

    # UX: permitir al usuario mapear manualmente las columnas
    st.markdown("---")
    st.markdown("Puedes mapear manualmente las columnas actuales a las columnas esperadas.")
    cols = df_limites.columns.tolist()
    mapping = {}
    cols_with_none = ["<NINGUNA>"] + cols
    for target in expected_cols:
        mapping[target] = st.selectbox(f"Columna para '{target}'", cols_with_none, key=target)

    if st.button("Aplicar mapeo manual"):
        # Validaciones
        chosen = [v for v in mapping.values() if v != "<NINGUNA>"]
        if len(chosen) != len(expected_cols):
            st.error("Debes seleccionar una columna real para cada campo (no dejar '<NINGUNA>').")
        elif len(set(chosen)) != len(chosen):
            st.error("Hay columnas repetidas en el mapeo. Cada columna debe usarse una sola vez.")
        else:
            # Renombrar
            rename_dict = {mapping[target]: target for target in expected_cols}
            try:
                df_mapped = df_limites.rename(columns=rename_dict).copy()
                # Asegurar que ahora exactamente las columnas esperadas existan y en el orden correcto
                df_mapped = df_mapped[expected_cols]
                st.success("Mapeo aplicado con éxito.")
                st.write("shape:", df_mapped.shape)
                st.write("columns:", df_mapped.columns.tolist())
                st.dataframe(df_mapped.head())
                # Asignar para uso posterior
                df_limites = df_mapped
            except Exception as e:
                st.error(f"Error al aplicar el mapeo: {e}")

    st.stop()

# Aquí continúa el resto de tu app que depende de df_limites ya normalizado.
# Reemplaza / amplía la lógica siguiente con lo que tu app necesite.

st.markdown("### Datos finales preparados")
st.write("shape:", df_limites.shape)
st.write("columns:", df_limites.columns.tolist())
st.dataframe(df_limites.head())
