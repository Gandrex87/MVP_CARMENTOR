# # utils/bigquery_tool.py
# Situación Actual: Tu función finalizar_y_presentar_node ahora calcula y guarda en el estado filtros_inferidos uno de estos dos escenarios para el Modo 1:
# modo_adquisicion_recomendado = "Contado" y un valor en precio_max_contado_recomendado.
# modo_adquisicion_recomendado = "Financiado" y un valor en cuota_max_calculada.
# En utils/bigquery_search.py


import logging
import traceback
from typing import Optional, List, Dict, Any
from google.cloud import bigquery

# Definiciones de tipo (pueden estar al inicio del módulo)
FiltrosDict = Dict[str, Any] 
PesosDict = Dict[str, float]

# Constantes (asegúrate de que estén definidas y sean correctas)
MIN_MAX_RANGES = {
    "estetica": (1.0, 10.0),
    "premium": (1.0, 10.0),
    "singular": (1.0, 10.0),
    "altura_libre_suelo": (79.0, 314.0), 
    "batalla": (1650.0, 4035.0),        
    "indice_altura_interior": (0.9, 2.7), 
    "ancho": (1410.0, 2164.0)          
}
PENALTY_PUERTAS_BAJAS = -0.15 

def buscar_coches_bq( # Renombrada para claridad
    filtros: Optional[FiltrosDict],
    pesos: Optional[PesosDict], 
    k: int = 7
) -> list[dict]:
    
    if not filtros: filtros = {}
    if not pesos: pesos = {} # Necesario para .get()

    try:
        client = bigquery.Client()
    except Exception as e_auth:
        logging.error(f"Error al inicializar cliente BigQuery: {e_auth}")
        return []

    # Desempaquetar Min/Max (todos necesarios para la CTE ScaledData)
    min_est, max_est = MIN_MAX_RANGES["estetica"]
    min_prem, max_prem = MIN_MAX_RANGES["premium"]
    min_sing, max_sing = MIN_MAX_RANGES["singular"]
    min_alt, max_alt = MIN_MAX_RANGES["altura_libre_suelo"]
    min_bat, max_bat = MIN_MAX_RANGES["batalla"]
    min_ind, max_ind = MIN_MAX_RANGES["indice_altura_interior"]
    min_anc, max_anc = MIN_MAX_RANGES["ancho"]

    # --- Parámetros Iniciales (solo pesos para el score y flags) ---
    params = [
        # Añadiremos los @peso_... dinámicamente según los score_calculation_terms
        bigquery.ScalarQueryParameter("penalizar_puertas", "BOOL", bool(filtros.get("penalizar_puertas_bajas", False))),
        bigquery.ScalarQueryParameter("k", "INT64", k) # Parámetro k siempre se necesita
    ]
    
    score_calculation_terms = []

    # # --- SECCIÓN PARA PRUEBA PASO A PASO DEL SCORE ---
    # # Descomenta un bloque a la vez para probar
    
    # 1. Solo Estética
    score_calculation_terms.append(f"estetica_scaled * @peso_estetica")
    params.append(bigquery.ScalarQueryParameter("peso_estetica", "FLOAT64", float(pesos.get("estetica",0.0))))

    #2. Añadir Premium
    score_calculation_terms.append(f"premium_scaled * @peso_premium")
    params.append(bigquery.ScalarQueryParameter("peso_premium", "FLOAT64", float(pesos.get("premium",0.0))))
    
    #3. Añadir Singular
    score_calculation_terms.append(f"singular_scaled * @peso_singular")
    params.append(bigquery.ScalarQueryParameter("peso_singular", "FLOAT64", float(pesos.get("singular",0.0))))

    # 4. Añadir Altura Libre Suelo
    score_calculation_terms.append(f"altura_scaled * @peso_altura")
    params.append(bigquery.ScalarQueryParameter("peso_altura", "FLOAT64", float(pesos.get("altura_libre_suelo",0.0))))
    
    # 5. Añadir Batalla
    score_calculation_terms.append(f"batalla_scaled * @peso_batalla")
    params.append(bigquery.ScalarQueryParameter("peso_batalla", "FLOAT64", float(pesos.get("batalla",0.0))))

    # 6. Añadir Índice Altura Interior
    score_calculation_terms.append(f"indice_altura_scaled * @peso_indice_altura")
    params.append(bigquery.ScalarQueryParameter("peso_indice_altura", "FLOAT64", float(pesos.get("indice_altura_interior",0.0))))
    
    # 7. Añadir Ancho
    score_calculation_terms.append(f"ancho_scaled * @peso_ancho")
    params.append(bigquery.ScalarQueryParameter("peso_ancho", "FLOAT64", float(pesos.get("ancho",0.0))))

    # 8. Añadir Tracción
    score_calculation_terms.append(f"traccion_scaled * @peso_traccion")
    params.append(bigquery.ScalarQueryParameter("peso_traccion", "FLOAT64", float(pesos.get("traccion",0.0))))

    # 9. Añadir Reductoras
    score_calculation_terms.append(f"reductoras_scaled * @peso_reductoras")
    params.append(bigquery.ScalarQueryParameter("peso_reductoras", "FLOAT64", float(pesos.get("reductoras",0.0))))

    # 10. Penalización por puertas (siempre se añade el término, el parámetro @penalizar_puertas controla su efecto)
    score_calculation_terms.append("puertas_penalty")
    # El parámetro @penalizar_puertas ya se añadió al inicio
    # # --- FIN SECCIÓN PASO A PASO ---


    # Construir la parte del SELECT para las características escaladas en CTE
    scaled_features_sql = f"""
        COALESCE(SAFE_DIVIDE(COALESCE(estetica, {min_est}) - {min_est}, NULLIF({max_est} - {min_est}, 0)), 0) AS estetica_scaled,
        COALESCE(SAFE_DIVIDE(COALESCE(premium, {min_prem}) - {min_prem}, NULLIF({max_prem} - {min_prem}, 0)), 0) AS premium_scaled,
        COALESCE(SAFE_DIVIDE(COALESCE(singular, {min_sing}) - {min_sing}, NULLIF({max_sing} - {min_sing}, 0)), 0) AS singular_scaled,
        COALESCE(SAFE_DIVIDE(COALESCE(altura_libre_suelo, {min_alt}) - {min_alt}, NULLIF({max_alt} - {min_alt}, 0)), 0) AS altura_scaled,
        COALESCE(SAFE_DIVIDE(COALESCE(batalla, {min_bat}) - {min_bat}, NULLIF({max_bat} - {min_bat}, 0)), 0) AS batalla_scaled,
        COALESCE(SAFE_DIVIDE(COALESCE(indice_altura_interior, {min_ind}) - {min_ind}, NULLIF({max_ind} - {min_ind}, 0)), 0) AS indice_altura_scaled,
        COALESCE(SAFE_DIVIDE(COALESCE(ancho, {min_anc}) - {min_anc}, NULLIF({max_anc} - {min_anc}, 0)), 0) AS ancho_scaled,
        CASE WHEN traccion = 'ALL' THEN 1.0 WHEN traccion = 'RWD' THEN 0.5 ELSE 0.0 END AS traccion_scaled,
        (CASE WHEN COALESCE(reductoras, FALSE) THEN 1.0 ELSE 0.0 END) AS reductoras_scaled,
        (CASE WHEN @penalizar_puertas = TRUE AND puertas <= 3 THEN {PENALTY_PUERTAS_BAJAS} ELSE 0.0 END) AS puertas_penalty
    """

    # Construir la parte del cálculo del score total
    score_total_sql = " + ".join(score_calculation_terms)
    if not score_calculation_terms: # Si todos los términos están comentados
        score_total_sql = "0" # Score default para que SQL no falle

    sql = f"""
    WITH ScaledData AS (
        SELECT
            *,
            {scaled_features_sql}
        FROM
            `thecarmentor-mvp2.web_cars.match_coches_pruebas`
    )
    SELECT 
      nombre, precio_compra_contado, tipo_carroceria, tipo_mecanica, 
      premium, singular, estetica, plazas, puertas, ancho, altura_libre_suelo, batalla, indice_altura_interior,
      traccion, reductoras,
      ( {score_total_sql} ) AS score_total
    FROM ScaledData
    WHERE 1=1 
    """

    # --- Aplicar Filtros Dinámicamente al WHERE ---
    sql_where_clauses = []

    # Transmisión
    transmision_val = filtros.get("transmision_preferida")
    if isinstance(transmision_val, str):
        if transmision_val.lower() == 'automático': sql_where_clauses.append("cambio_automatico = TRUE")
        elif transmision_val.lower() == 'manual': sql_where_clauses.append("cambio_automatico = FALSE")

    # Filtros numéricos mínimos
    numeric_filters_map = {
        "estetica_min": ("estetica", "FLOAT64"),
        "premium_min": ("premium", "FLOAT64"),
        "singular_min": ("singular", "FLOAT64"),
    }
    for key, (column, dtype) in numeric_filters_map.items():
        value = filtros.get(key)
        if value is not None:
            sql_where_clauses.append(f"COALESCE({column}, 0) >= @{key}") 
            params.append(bigquery.ScalarQueryParameter(key, dtype, float(value)))
    
    # Plazas mínimas
    plazas_min_val = filtros.get("plazas_min")
    if plazas_min_val is not None and isinstance(plazas_min_val, int) and plazas_min_val > 0:
        sql_where_clauses.append(f"plazas >= @plazas_min") 
        params.append(bigquery.ScalarQueryParameter("plazas_min", "INT64", plazas_min_val))

    # Tipos de mecánica
    tipos_mecanica_str = filtros.get("tipo_mecanica")
    if isinstance(tipos_mecanica_str, list) and tipos_mecanica_str:
        sql_where_clauses.append(f"tipo_mecanica IN UNNEST(@tipos_mecanica)")
        params.append(bigquery.ArrayQueryParameter("tipos_mecanica", "STRING", tipos_mecanica_str))

    # Tipos de carrocería
    tipos_carroceria = filtros.get("tipo_carroceria")
    if isinstance(tipos_carroceria, list) and tipos_carroceria:
        sql_where_clauses.append(f"tipo_carroceria IN UNNEST(@tipos_carroceria)")
        params.append(bigquery.ArrayQueryParameter("tipos_carroceria", "STRING", tipos_carroceria))

    # Filtro Económico (Este es el bloque corregido de antes)
    modo_adq_rec = filtros.get("modo_adquisicion_recomendado")
    precio_a_filtrar = filtros.get("precio_max_contado_recomendado") if modo_adq_rec == "Contado" else filtros.get("pago_contado")
    cuota_a_filtrar = filtros.get("cuota_max_calculada") if modo_adq_rec == "Financiado" else filtros.get("cuota_max")

    if precio_a_filtrar is not None:
        sql_where_clauses.append(f"COALESCE(precio_compra_contado, 999999999) <= @precio_maximo")
        params.append(bigquery.ScalarQueryParameter("precio_maximo", "FLOAT64", float(precio_a_filtrar))) 
    elif cuota_a_filtrar is not None:
        sql_where_clauses.append(f"COALESCE(precio_compra_contado, 0) * 1.35 / 96.0 <= @cuota_maxima") 
        params.append(bigquery.ScalarQueryParameter("cuota_maxima", "FLOAT64", float(cuota_a_filtrar)))

    # Añadir todas las cláusulas WHERE al SQL
    if sql_where_clauses:
        sql += "\n      AND " + "\n      AND ".join(sql_where_clauses)

    # Orden y Límite
    sql += "\n    ORDER BY score_total DESC, precio_compra_contado ASC" 
    sql += "\n    LIMIT @k"
    # El parámetro @k ya se añadió al inicio junto con @penalizar_puertas
    
    print("--- 🧠 SQL Query (Paso a Paso) ---\n", sql) 
    print("\n--- 📦 Parameters (Paso a Paso) ---\n", [(p.name, getattr(p, 'value', getattr(p, 'values', None))) for p in params]) 

    try:
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        query_job = client.query(sql, job_config=job_config)
        df = query_job.result().to_dataframe() 
        logging.info(f"✅ (Paso a Paso) BigQuery query ejecutada, {len(df)} resultados obtenidos.")
        return df.to_dict(orient="records")
    except Exception as e:
        logging.error(f"❌ (Paso a Paso) Error al ejecutar la query en BigQuery: {e}")
        traceback.print_exc()
        return []