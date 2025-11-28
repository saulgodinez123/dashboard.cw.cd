import streamlit as st
import pandas as pd
import numpy as np

# Configuración básica de la aplicación
st.set_page_config(layout="wide", page_title="Dashboard de Monitoreo de Producción")

st.title("📊 MultiVarX - Dashboard de Límites de Calidad de Manufactura")

# 1. Función para cargar datos de producción (CSV)
@st.cache_data
def load_production_data(file_path):
    """Carga los archivos CSV de producción (CD y CW)."""
    try:
        df = pd.read_csv(file_path)
        # Asumiendo que hay una columna de tiempo o índice en los datos
        st.success(f"Datos de {file_path} cargados correctamente. Filas: {len(df)}")
        return df
    except FileNotFoundError:
        st.error(f"Error: El archivo {file_path} no fue encontrado.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al leer {file_path}: {e}")
        return pd.DataFrame()

# 2. Función para cargar y transformar la tabla de límites (Excel)
@st.cache_data
def load_and_process_limits(file_path):
    """Carga el Excel de límites con encabezados multinivel y lo transforma a formato largo."""
    try:
        # Usamos header=[0, 1] para leer los encabezados en dos niveles (FVTx_CD, Variable/Limite)
        df_limites_wide = pd.read_excel(file_path, header=[0, 1])
        st.success("Datos de límites cargados correctamente.")

        # Limpieza y transformación a formato largo
        all_limits = []
        # Identificamos los pares de columnas por el primer nivel (FVT7_CD, FVT7_CW, etc.)
        machines = df_limites_wide.columns.get_level_values(0).unique()

        for machine_id in machines:
            # Selecciona las 3 columnas correspondientes a cada máquina (FVT7_CD, FVT7_CW, etc.)
            subset = df_limites_wide[machine_id].copy()
            
            # Renombra las columnas del segundo nivel para estandarizar
            subset.columns = ['Variable', 'Limite_Inferior', 'Limite_Superior']
            
            # Elimina filas donde 'Variable' es nulo
            subset = subset.dropna(subset=['Variable'])
            
            # Agrega la columna de identificación de la máquina
            subset['Maquina_Tipo'] = machine_id
            
            all_limits.append(subset)

        # Concatena todos los subconjuntos en un solo DataFrame de formato largo
        df_limites_long = pd.concat(all_limits, ignore_index=True)
        return df_limites_long
        
    except FileNotFoundError:
        st.error(f"Error: El archivo {file_path} no fue encontrado.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al leer el Excel de límites. Verifica la estructura de las cabeceras: {e}")
        return pd.DataFrame()

# --- Rutas de Archivos (Ajustar según tu estructura de GitHub) ---
CD_FILE = 'CD_unificado.csv'
CW_FILE = 'CW_unificado.csv'
LIMITS_FILE = 'Limites en tablas (1).xlsx'

# --- Carga de Datos ---
df_cd = load_production_data(CD_FILE)
df_cw = load_production_data(CW_FILE)
df_limites = load_and_process_limits(LIMITS_FILE)

# --- Unión de Datos de Producción (si tienen la misma estructura) ---
# Una práctica común es unir los datos de CD y CW en un solo marco
if not df_cd.empty and not df_cw.empty:
    df_unificado = pd.concat([df_cd.assign(Tipo='CD'), df_cw.assign(Tipo='CW')], ignore_index=True)
    st.subheader("Datos Unificados de Producción")
    st.dataframe(df_unificado.head(5))
else:
    df_unificado = pd.DataFrame()

# --- Visualización de Datos de Límites Transformados ---
if not df_limites.empty:
    st.subheader("Tabla de Límites (Formato Largo para Merge)")
    st.dataframe(df_limites.head(10))

# --- Sección de Desarrollo del Dashboard ---
st.subheader("Desarrollo: Validación y Visualización de Variables")

if not df_unificado.empty and not df_limites.empty:
    # Este es el punto de partida para tu dashboard:
    # 1. Selecciona una Maquina/Tipo y una Variable.
    # 2. Busca sus límites en df_limites.
    # 3. Filtra y grafica los datos en df_unificado, comparándolos con los límites.
    
    # Ejemplo Sencillo de Interacción
    available_machines = df_limites['Maquina_Tipo'].unique()
    if available_machines.size > 0:
        selected_machine = st.selectbox("Selecciona una Maquina (Ejemplo):", available_machines)
        
        # Filtra las variables para la máquina seleccionada
        limits_for_machine = df_limites[df_limites['Maquina_Tipo'] == selected_machine]
        available_variables = limits_for_machine['Variable'].unique()

        # Usamos una variable de ejemplo para mostrar la lógica
        if 'Get Angle1' in available_variables:
             variable_to_check = 'Get Angle1'
             limit_row = limits_for_machine[limits_for_machine['Variable'] == variable_to_check].iloc[0]
             
             lower = limit_row['Limite_Inferior']
             upper = limit_row['Limite_Superior']
             
             # En la práctica, necesitarías una columna de Maquina + Tipo para un 'merge' completo.
             # Por ahora, mostramos la lógica.
             st.write(f"**Límites para {selected_machine} - {variable_to_check}:** Inferior={lower}, Superior={upper}")
             
             # Aquí iría el código para filtrar df_unificado y graficar con Plotly/Matplotlib
             # donde los límites superior e inferior se muestran como líneas de control.
             
        else:
             st.info("Selecciona otra variable de tu interés para continuar el desarrollo.")
    
# --- Fin del Archivo app.py ---
