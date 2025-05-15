# utils/bq_logger.py
import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from google.cloud import bigquery

# Configura tu dataset y tabla de BigQuery
PROJECT_ID = "thecarmentor-mvp2" # proyecto de GCP
DATASET_ID = "web_cars"          # dataset de BigQuery
TABLE_ID = "historial_busquedas_agente" # El nombre de tabla

TABLE_FULL_ID = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

def log_busqueda_a_bigquery(
    id_conversacion: str,
    preferencias_usuario_obj: Optional[Any], # PerfilUsuario
    filtros_aplicados_obj: Optional[Any],    # FiltrosInferidos
    economia_usuario_obj: Optional[Any],     # EconomiaUsuario
    pesos_aplicados_dict: Optional[Dict[str, float]],
    tabla_resumen_criterios_md: Optional[str],
    coches_recomendados_list: Optional[List[Dict[str, Any]]],
    num_coches_devueltos: int,
    sql_query_ejecutada: Optional[str],
    sql_params_list: Optional[List[Dict[str, Any]]] # Lista de {"name":..., "value":..., "type":...}
):
    """Guarda la información de una búsqueda finalizada en BigQuery."""
    try:
        client = bigquery.Client(project=PROJECT_ID)
        
        # Convertir objetos Pydantic y dicts a JSON strings
        # Usar model_dump_json para Pydantic, json.dumps para dicts/lists
        prefs_json = preferencias_usuario_obj.model_dump_json(indent=2) if hasattr(preferencias_usuario_obj, "model_dump_json") else None
        filtros_json = filtros_aplicados_obj.model_dump_json(indent=2) if hasattr(filtros_aplicados_obj, "model_dump_json") else None
        econ_json = economia_usuario_obj.model_dump_json(indent=2) if hasattr(economia_usuario_obj, "model_dump_json") else None
        pesos_json = json.dumps(pesos_aplicados_dict, indent=2) if pesos_aplicados_dict else None
        if coches_recomendados_list is not None: # Chequear si la lista es None
            coches_json = json.dumps(coches_recomendados_list, indent=2) # json.dumps([]) produce "[]"
        else:
            coches_json = None # Si la lista original era None, el JSON es None
        params_json = json.dumps(sql_params_list, indent=2) if sql_params_list else None

        row_to_insert = {
            "id_conversacion": id_conversacion,
            "timestamp_busqueda": datetime.now(timezone.utc).isoformat(),
            "preferencias_usuario_json": prefs_json,
            "filtros_aplicados_json": filtros_json,
            "economia_usuario_json": econ_json,
            "pesos_aplicados_json": pesos_json,
            "tabla_resumen_criterios_md": tabla_resumen_criterios_md,
            "coches_recomendados_json": coches_json,
            "num_coches_devueltos": num_coches_devueltos,
            "sql_query_ejecutada": sql_query_ejecutada,
            "sql_params_json": params_json,
        }
        
        # Quitar claves con valor None para no intentar insertar NULLs en campos no nullable (si aplica)
        # O asegurarse que la tabla BQ permita NULLs para estos campos STRING JSON
        row_to_insert_cleaned = {k: v for k, v in row_to_insert.items() if v is not None}

        errors = client.insert_rows_json(TABLE_FULL_ID, [row_to_insert_cleaned])
        if not errors:
            logging.info(f"Log de búsqueda para conversación '{id_conversacion}' insertado en BigQuery.")
            print(f"INFO (BQ Logger) ► Log para '{id_conversacion}' guardado en BQ.")
        else:
            logging.error(f"Errores al insertar log en BigQuery para '{id_conversacion}': {errors}")
            print(f"ERROR (BQ Logger) ► Errores al guardar log en BQ: {errors}")

    except Exception as e:
        logging.error(f"Error en la función log_busqueda_a_bigquery para '{id_conversacion}': {e}")
        print(f"ERROR (BQ Logger) ► Fallo general en log_busqueda_a_bigquery: {e}")
        traceback.print_exc()