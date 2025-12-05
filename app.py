import pandas as pd
import numpy as np

# =========================
# CARGA Y PREPARACIÓN DE DATOS
# =========================

def cargar_datos(path):
    df = pd.read_excel(path)
    
    # Normalizar nombres de columnas
    df.columns = df.columns.str.strip().str.replace(" ", "_").str.upper()

    # Estandarización básica
    if "FECHA" in df:
        df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce")

    # Eliminar duplicados
    df = df.drop_duplicates()

    return df


# =========================
# LIMPIEZA DE OUTLIERS POR REGLA IQR
# =========================

def limpiar_outliers(df, columna, factor=1.5):
    Q1 = df[columna].quantile(0.25)
    Q3 = df[columna].quantile(0.75)
    IQR = Q3 - Q1
    low = Q1 - factor * IQR
    high = Q3 + factor * IQR
    df_limpio = df[(df[columna] >= low) & (df[columna] <= high)]
    return df_limpio


# =========================
# MÉTRICOS GENERALES DEL PROCESO
# =========================

def metricos_generales(df):
    return {
        "total_registros": len(df),
        "variables_unicas": df["VARIABLE"].nunique(),
        "categorias_unicas": df["CATEGORIA"].nunique() if "CATEGORIA" in df else None,
        "min_valor": df["VALOR"].min(),
        "max_valor": df["VALOR"].max(),
        "promedio_global": df["VALOR"].mean()
    }


# =========================
# ANÁLISIS ESTADÍSTICO POR VARIABLE
# =========================

def analizar_variables(df):
    resultados = []

    for variable in df["VARIABLE"].unique():
        df_var = df[df["VARIABLE"] == variable]

        resultados.append({
            "Variable": variable,
            "Total": len(df_var),
            "Promedio": df_var["VALOR"].mean(),
            "STD": df_var["VALOR"].std(),
            "Min": df_var["VALOR"].min(),
            "Max": df_var["VALOR"].max()
        })

    return pd.DataFrame(resultados)


# =========================
# ANÁLISIS CON LÍMITES LSL – USL
# =========================

def analizar_limites(df, categoria=None, filtro=None):
    df_filtrado = df.copy()

    if categoria:
        df_filtrado = df_filtrado[df_filtrado["CATEGORIA"] == categoria]

    if filtro:
        for col, val in filtro.items():
            df_filtrado = df_filtrado[df_filtrado[col] == val]

    resultados = []

    for variable in df_filtrado["VARIABLE"].unique():
        df_var = df_filtrado[df_filtrado["VARIABLE"] == variable]
        total_registros = len(df_var)

        promedio = df_var["VALOR"].mean()
        minimo = df_var["VALOR"].min()
        maximo = df_var["VALOR"].max()

        lsl = df_var["LSL"].iloc[0] if "LSL" in df_var else None
        usl = df_var["USL"].iloc[0] if "USL" in df_var else None

        fuera = df_var[(df_var["VALOR"] < lsl) | (df_var["VALOR"] > usl)]
        fuera_count = len(fuera)

        porcentaje_fuera = (fuera_count / total_registros * 100) if total_registros > 0 else 0

        resultados.append({
            "Variable": variable,
            "Promedio": promedio,
            "Min": minimo,
            "Max": maximo,
            "LSL": lsl,
            "USL": usl,
            "Valores_fuera": fuera_count,
            "Total_registros": total_registros,
            "Porcentaje_fuera": porcentaje_fuera
        })

    return pd.DataFrame(resultados)


# =========================
# EXPORTAR RESULTADOS
# =========================

def exportar_resultados(df_metricos, df_limites, salida="resultados.xlsx"):
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        df_metricos.to_excel(writer, sheet_name="Metricos_generales", index=False)
        df_limites.to_excel(writer, sheet_name="Analisis_limites", index=False)


# =========================
# PIPELINE COMPLETO PARA EJECUCIÓN DIRECTA
# =========================

def ejecutar_pipeline(path_excel, categoria=None, filtro=None, salida="resultados.xlsx"):
    df = cargar_datos(path_excel)

    metricos = pd.DataFrame([metricos_generales(df)])
    analisis_limites = analizar_limites(df, categoria=categoria, filtro=filtro)

    exportar_resultados(metricos, analisis_limites, salida=salida)

    return {
        "metricos_generales": metricos,
        "analisis_limites": analisis_limites
    }


# =========================
# EJEMPLO DE USO
# =========================

if __name__ == "__main__":
    resultados = ejecutar_pipeline(
        "data.xlsx",
        categoria="MECANIZADO",
        filtro={"TURNO": "A"},
        salida="resultados_proceso.xlsx"
    )

    print("\n--- MÉTRICOS GENERALES ---\n")
    print(resultados["metricos_generales"])

    print("\n--- ANÁLISIS DE LÍMITES ---\n")
    print(resultados["analisis_limites"])
