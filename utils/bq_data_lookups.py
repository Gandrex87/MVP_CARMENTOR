# utils/bq_data_lookups.py

import logging
import traceback
from typing import Optional, Dict, Any
from google.cloud import bigquery

# Ajusta la ruta de importación según tu estructura
from graph.perfil.state import InfoClimaUsuario # Necesitamos el modelo Pydantic

# Configura tu proyecto, dataset y tabla de BigQuery
PROJECT_ID = "thecarmentor-mvp2" # Reemplaza si es diferente
DATASET_ID = "web_cars"          # O el dataset donde está tu tabla
TABLE_ZONAS_CLIMAS_ID = "zonas_climas" # El nombre de tu tabla de zonas climáticas

TABLE_FULL_ID_ZONAS = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ZONAS_CLIMAS_ID}"

# Nombres de las columnas en tu tabla BQ que contienen los CPs para cada zona
COLUMNAS_ZONA = [
    "MUNICIPIO_ZBE",
    "ZONA_LLUVIAS",
    "ZONA_NIEBLAS",
    "ZONA_NIEVE",
    "ZONA_CLIMA_MONTA",
    "ZONA_GLP",
    "ZONA_GNV"
]

def obtener_datos_climaticos_por_cp(codigo_postal_str: str) -> Optional[InfoClimaUsuario]:
    """
    Consulta la tabla de zonas climáticas en BigQuery para un código postal dado.

    Args:
        codigo_postal_str: El código postal del usuario (como string).

    Returns:
        Un objeto InfoClimaUsuario con los flags booleanos correspondientes,
        o None si ocurre un error o el CP no produce datos.
    """
    logging.info(f"Buscando información climática para el CP: {codigo_postal_str} en {TABLE_FULL_ID_ZONAS}")
    
    if not codigo_postal_str or not codigo_postal_str.isdigit() or len(codigo_postal_str) != 5:
        logging.warning(f"CP inválido proporcionado para búsqueda climática: {codigo_postal_str}")
        return None

    try:
        client = bigquery.Client(project=PROJECT_ID)
        
        # Intentar convertir el CP a INTEGER para la query, ya que tus columnas BQ son INTEGER
        try:
            cp_int = int(codigo_postal_str)
        except ValueError:
            logging.warning(f"CP '{codigo_postal_str}' no es un entero válido para la query BQ.")
            return InfoClimaUsuario(codigo_postal_consultado=codigo_postal_str, cp_valido_encontrado=False)

        # Construir las partes del SELECT para la query dinámicamente
        select_parts = []
        for col_zona in COLUMNAS_ZONA:
            # Cada parte del SELECT verifica si el CP existe en la columna de zona correspondiente
            # y devuelve TRUE o FALSE para esa zona.
            select_parts.append(
                f"EXISTS(SELECT 1 FROM `{TABLE_FULL_ID_ZONAS}` WHERE {col_zona} = @cp_param) AS {col_zona}"
            )
        
        select_clause = ",\n       ".join(select_parts)
        
        sql = f"""
        SELECT
            {select_clause}
        """
        
        params = [
            bigquery.ScalarQueryParameter("cp_param", "INT64", cp_int),
        ]

        logging.debug(f"Ejecutando query de clima BQ: {sql} con params: {cp_int}")
        print(f"DEBUG (BQ Clima) ► Query: {sql}") # Para depuración
        print(f"DEBUG (BQ Clima) ► Params: {cp_int}") # Para depuración

        job_config = bigquery.QueryJobConfig(query_parameters=params)
        query_job = client.query(sql, job_config=job_config)
        
        results = list(query_job.result()) # Espera y obtiene los resultados

        if results and len(results) == 1:
            row = results[0] # Debería devolver una sola fila con todos los booleanos
            logging.info(f"Datos climáticos encontrados para CP {codigo_postal_str}: {dict(row)}")
            
            # Crear y devolver el objeto InfoClimaUsuario
            # Los nombres de campo en InfoClimaUsuario deben coincidir con COLUMNAS_ZONA
            clima_data = {col: bool(getattr(row, col, False)) for col in COLUMNAS_ZONA}
            clima_data["cp_valido_encontrado"] = True # Se procesó, aunque todos pudieran ser False
            clima_data["codigo_postal_consultado"] = codigo_postal_str
            return InfoClimaUsuario(**clima_data)
        else:
            logging.warning(f"No se encontró una fila de resultados única para el CP {codigo_postal_str} o la query devolvió múltiples filas.")
            # Devolver un objeto con defaults (todos False) pero indicando que el CP se consultó
            return InfoClimaUsuario(codigo_postal_consultado=codigo_postal_str, cp_valido_encontrado=False)

    except Exception as e:
        logging.error(f"Error al obtener datos climáticos para CP {codigo_postal_str} de BigQuery: {e}")
        traceback.print_exc()
        # En caso de error, devolver un objeto indicando que no se pudo procesar
        return InfoClimaUsuario(codigo_postal_consultado=codigo_postal_str, cp_valido_encontrado=False)

# --- Ejemplo de uso (para probar en un notebook o localmente si tienes credenciales) ---
# if __name__ == "__main__":
#     # Configurar logging para ver los mensajes de la función
#     logging.basicConfig(level=logging.INFO)
#     test_cp = "28010" # Un CP de ejemplo
#     clima_info = obtener_datos_climaticos_por_cp(test_cp)
#     if clima_info:
#         print(f"\nInformación climática para {test_cp}:")
#         print(clima_info.model_dump_json(indent=2))
#     else:
#         print(f"No se pudo obtener información para {test_cp}")

#     test_cp_no_existente = "00000"
#     clima_info_no = obtener_datos_climaticos_por_cp(test_cp_no_existente)
#     if clima_info_no:
#         print(f"\nInformación climática para {test_cp_no_existente}:")
#         print(clima_info_no.model_dump_json(indent=2))
#     else:
#         print(f"No se pudo obtener información para {test_cp_no_existente}")
