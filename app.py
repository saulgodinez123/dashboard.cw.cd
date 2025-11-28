import streamlit as st
import pandas as pd
import numpy as np

# ... (El resto del código de configuración de Streamlit y la función load_production_data se mantiene igual)

# 2. Función para cargar y transformar la tabla de límites (Excel)
@st.cache_data
def load_and_process_limits(file_path):
    """Carga el Excel de límites con encabezados multinivel y lo transforma a formato largo."""
    try:
        # Usamos header=[0, 1] para leer los encabezados en dos niveles
        df_limites_wide = pd.read_excel(file_path, header=[0, 1])
        st.success("Datos de límites cargados correctamente.")

        all_limits = []
        # Identificamos los pares de columnas por el primer nivel (FVT7_CD, FVT7_CW, etc.)
        machines = df_limites_wide.columns.get_level_values(0).unique()

        for machine_id in machines:
            # Selecciona las columnas correspondientes a cada máquina
            subset = df_limites_wide[machine_id].copy()
            
            # 💡 FIX ROBUSTO: Filtra y elimina las columnas cuyo nombre en el nivel 1 sea NaN 
            # (estas son las columnas en blanco que causan el error de 4 vs 3 elementos).
            subset = subset.loc[:, subset.columns.notna()]
            
            # --- Validación (Opcional, pero buena práctica) ---
            if len(subset.columns) != 3:
                st.warning(f"Advertencia en {machine_id}: Tras la limpieza, se encontraron {len(subset.columns)} columnas. Se esperaban 3. Verifique el formato de esta sección en el Excel.")
                # Intentamos tomar solo las primeras 3 si hay más de 3
                if len(subset.columns) > 3:
                    subset = subset.iloc[:, :3]
                else:
                    st.info(f"Saltando {machine_id} debido a un formato de columna irrecuperable.")
                    continue

            # Renombra las 3 columnas del segundo nivel para estandarizar
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
        # Si el error persiste, al menos ahora reportamos la excepción original.
        st.error(f"Error crítico al leer el Excel de límites (Verifique la primera fila): {e}")
        return pd.DataFrame()

# ... (El resto del código de unión y visualización se mantiene igual)
