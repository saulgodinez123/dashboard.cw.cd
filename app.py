import pandas as pd
from jupyter_dash import JupyterDash
from dash import Dash, dcc, html, Input, Output, dash_table
import plotly.express as px

# ============================
#      LECTURA DEL ARCHIVO
# ============================

def cargar_archivo():
    try:
        # Usa engine openpyxl porque tu archivo tiene MUCHAS columnas
        df = pd.read_excel("MANT.xlsx", engine="openpyxl")

        # Limpieza automática de nombres de columnas
        df.columns = (
            df.columns.astype(str)
            .str.replace("\n", "_")
            .str.replace(" ", "_")
            .str.replace("-", "_")
            .str.replace("__", "_")
        )

        # Manejar columnas duplicadas
        df = df.loc[:, ~df.columns.duplicated()]

        return df

    except Exception as e:
        print("Error al cargar archivo:", e)
        return pd.DataFrame()


df = cargar_archivo()

# ============================
#       APP DASH
# ============================

app = JupyterDash(__name__)

app.layout = html.Div([

    html.H1("Dashboard CD / CW", style={"textAlign": "center"}),

    html.Div([
        html.Label("Selecciona Modelo:"),
        dcc.Dropdown(
            id="filtro_modelo",
            options=[{"label": m, "value": m} for m in sorted(df["Model"].unique())] if "Model" in df.columns else [],
            placeholder="Modelo"
        )
    ]),

    html.Div([
        html.Label("Selecciona Línea:"),
        dcc.Dropdown(
            id="filtro_linea",
            options=[{"label": m, "value": m} for m in sorted(df["linea"].unique())] if "linea" in df.columns else [],
            placeholder="Línea"
        )
    ]),

    html.Div([
        html.Label("Selecciona Categoría:"),
        dcc.Dropdown(
            id="filtro_categoria",
            options=[{"label": m, "value": m} for m in sorted(df["categoria"].unique())] if "categoria" in df.columns else [],
            placeholder="Categoría"
        )
    ]),

    html.Br(),

    html.Div(id="mensaje_error", style={"color": "red", "fontWeight": "bold"}),

    dash_table.DataTable(
        id="tabla_filtrada",
        page_size=20,
        style_table={"overflowX": "scroll"},
        style_cell={"textAlign": "left", "minWidth": "150px"}
    )
])

# ============================
# CALLBACK DE FILTRO
# ============================

@app.callback(
    Output("tabla_filtrada", "data"),
    Output("tabla_filtrada", "columns"),
    Output("mensaje_error", "children"),
    Input("filtro_modelo", "value"),
    Input("filtro_linea", "value"),
    Input("filtro_categoria", "value")
)
def actualizar_tabla(modelo, linea, categoria):

    if df.empty:
        return [], [], "⚠ No se pudo leer el archivo MANT.xlsx"

    df_filtrado = df.copy()

    if modelo:
        df_filtrado = df_filtrado[df_filtrado["Model"] == modelo]

    if linea:
        df_filtrado = df_filtrado[df_filtrado["linea"] == linea]

    if categoria:
        df_filtrado = df_filtrado[df_filtrado["categoria"] == categoria]

    if df_filtrado.empty:
        return [], [], "⚠ No hay registros para los filtros seleccionados."

    return (
        df_filtrado.to_dict("records"),
        [{"name": c, "id": c} for c in df_filtrado.columns],
        ""
    )


# ============================
# EJECUCIÓN
# ============================

if __name__ == "__main__":
    app.run_server(debug=True, mode="inline")

