# # utils/bigquery_tool.py
# Situación Actual: Tu función finalizar_y_presentar_node ahora calcula y guarda en el estado filtros_inferidos uno de estos dos escenarios para el Modo 1:
# modo_adquisicion_recomendado = "Contado" y un valor en precio_max_contado_recomendado.
# modo_adquisicion_recomendado = "Financiado" y un valor en cuota_max_calculada.
# En utils/bigquery_search.py


import logging
import traceback
from typing import Optional, List, Dict, Any , Tuple
from google.cloud import bigquery

# Definiciones de tipo (pueden estar al inicio del módulo)
FiltrosDict = Dict[str, Any] 
PesosDict = Dict[str, float]

# Definir aquí los rangos mínimos y máximos para cada característica
MIN_MAX_RANGES = {
    "estetica": (1.0, 10.0),
    "premium": (1.0, 10.0),
    "singular": (1.0, 10.0),
    "altura_libre_suelo": (79.0, 314.0), 
    "batalla": (1650.0, 4035.0),        
    "indice_altura_interior": (0.9, 2.7), 
    "ancho": (1410.0, 2164.0),
    "fiabilidad": (1.0, 10.0), # Asumiendo una escala de 1-10 para fiabilidad en BQ
    "durabilidad": (1.0, 10.0), # Asumiendo una escala de 1-10 para durabilidad en BQ
    "seguridad": (1.0, 10.0),   # Asumiendo una escala de 1-10 para seguridad en BQ
    "comodidad": (1.0, 10.0),   # Asumiendo una escala de 1-10 para comodidad en BQ
    "tecnologia": (1.0, 10.0),  # Asumiendo una escala de 1-10 para tecnologia en BQ
    "acceso_low_cost": (1.0, 10.0), # Asume una escala, donde más alto = más low_cost
    "deportividad": (1.0, 10.0),    # Asume una escala, donde más alto = más deportivo
}
PENALTY_PUERTAS_BAJAS = -0.15
# --- NUEVAS PENALIZACIONES (AJUSTA ESTOS VALORES) ---
PENALTY_LOW_COST_POR_COMODIDAD = -0.20 # Cuánto restar si es muy low-cost y se quiere confort
PENALTY_DEPORTIVIDAD_POR_COMODIDAD = -0.15 # Cuánto restar si es muy deportivo y se quiere confort
# --- UMBRALES PARA PENALIZACIÓN (AJUSTA ESTOS VALORES, 0-1 después de escalar) ---
UMBRAL_LOW_COST_PENALIZABLE = 0.7 # Penalizar si acceso_low_cost_scaled >= 0.7
UMBRAL_DEPORTIVIDAD_PENALIZABLE = 0.7 # Penalizar si deportividad_scaled >= 0.7

def buscar_coches_bq( # Renombrada para claridad
    filtros: Optional[FiltrosDict],
    pesos: Optional[PesosDict], 
    k: int = 7
) -> Tuple[List[Dict[str, Any]], str, List[Dict[str, Any]]]: #Devuelve: una tupla con (lista de coches, string SQL, lista de parámetros formateados).
    
    if not filtros: filtros = {}
    if not pesos: pesos = {} # Necesario para .get()

    try:
        client = bigquery.Client()
    except Exception as e_auth:
        logging.error(f"Error al inicializar cliente BigQuery: {e_auth}")
        return []

    # Pesos completos (incluyendo los nuevos ratings)
    pesos_completos = {
        "estetica": pesos.get("estetica", 0.0),
        "premium": pesos.get("premium", 0.0),
        "singular": pesos.get("singular", 0.0),
        "altura_libre_suelo": pesos.get("altura_libre_suelo", 0.0),
        "batalla": pesos.get("batalla", 0.0),
        "indice_altura_interior": pesos.get("indice_altura_interior", 0.0),
        "ancho": pesos.get("ancho", 0.0),
        "traccion": pesos.get("traccion", 0.0),
        "reductoras": pesos.get("reductoras", 0.0),
        # --- NUEVOS PESOS DE RATINGS (claves deben coincidir con compute_raw_weights) ---
        "rating_fiabilidad_durabilidad": pesos.get("rating_fiabilidad_durabilidad", 0.0),
        "rating_seguridad": pesos.get("rating_seguridad", 0.0),
        "rating_comodidad": pesos.get("rating_comodidad", 0.0),
        "rating_impacto_ambiental": pesos.get("rating_impacto_ambiental", 0.0), # Para después
       # "rating_costes_uso": pesos.get("rating_costes_uso", 0.0),             # Para después
        "rating_tecnologia_conectividad": pesos.get("rating_tecnologia_conectividad", 0.0), # Para después
    }
    
    # Flags de penalización (vienen en el dict 'filtros') --- FLAGS (DEBEN VENIR EN EL DICT 'filtros') ---
    penalizar_puertas_val = bool(filtros.get("penalizar_puertas_bajas", False))
    flag_penalizar_low_cost_comod = bool(filtros.get("flag_penalizar_low_cost_comodidad", False))
    flag_penalizar_deportividad_comod = bool(filtros.get("flag_penalizar_deportividad_comodidad", False))

    # Desempaquetar Min/Max (todos necesarios para la CTE ScaledData)
    min_est, max_est = MIN_MAX_RANGES["estetica"]
    min_prem, max_prem = MIN_MAX_RANGES["premium"]
    min_sing, max_sing = MIN_MAX_RANGES["singular"]
    min_alt, max_alt = MIN_MAX_RANGES["altura_libre_suelo"]
    min_bat, max_bat = MIN_MAX_RANGES["batalla"]
    min_ind, max_ind = MIN_MAX_RANGES["indice_altura_interior"]
    min_anc, max_anc = MIN_MAX_RANGES["ancho"]
    min_fiab, max_fiab = MIN_MAX_RANGES["fiabilidad"]
    min_durab, max_durab = MIN_MAX_RANGES["durabilidad"]
    min_seg, max_seg = MIN_MAX_RANGES["seguridad"]
    min_comod, max_comod = MIN_MAX_RANGES["comodidad"]
    min_tec, max_tec = MIN_MAX_RANGES["tecnologia"] 
    min_acc_lc, max_acc_lc = MIN_MAX_RANGES["acceso_low_cost"] # Necesario para penalización
    min_depor, max_depor = MIN_MAX_RANGES["deportividad"]    # Necesario para penalización

    sql = f"""
    WITH ScaledData AS (
        SELECT
            *,
            COALESCE(SAFE_DIVIDE(COALESCE(estetica, {min_est}) - {min_est}, NULLIF({max_est} - {min_est}, 0)), 0) AS estetica_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(premium, {min_prem}) - {min_prem}, NULLIF({max_prem} - {min_prem}, 0)), 0) AS premium_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(singular, {min_sing}) - {min_sing}, NULLIF({max_sing} - {min_sing}, 0)), 0) AS singular_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(altura_libre_suelo, {min_alt}) - {min_alt}, NULLIF({max_alt} - {min_alt}, 0)), 0) AS altura_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(batalla, {min_bat}) - {min_bat}, NULLIF({max_bat} - {min_bat}, 0)), 0) AS batalla_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(indice_altura_interior, {min_ind}) - {min_ind}, NULLIF({max_ind} - {min_ind}, 0)), 0) AS indice_altura_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(ancho, {min_anc}) - {min_anc}, NULLIF({max_anc} - {min_anc}, 0)), 0) AS ancho_scaled,
            -- CAMPOS ESCALADOS PARA NUEVOS RATINGS --
            COALESCE(SAFE_DIVIDE(COALESCE(fiabilidad, {min_fiab}) - {min_fiab}, NULLIF({max_fiab} - {min_fiab}, 0)), 0) AS fiabilidad_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(durabilidad, {min_durab}) - {min_durab}, NULLIF({max_durab} - {min_durab}, 0)), 0) AS durabilidad_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(seguridad, {min_seg}) - {min_seg}, NULLIF({max_seg} - {min_seg}, 0)), 0) AS seguridad_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(comodidad, {min_comod}) - {min_comod}, NULLIF({max_comod} - {min_comod}, 0)), 0) AS comodidad_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(tecnologia, {min_tec}) - {min_tec}, NULLIF({max_tec} - {min_tec}, 0)), 0) AS tecnologia_scaled, -- <-- Nuevo escalado
            -- CAMPOS ESCALADOS PARA PENALIZACIONES --
            COALESCE(SAFE_DIVIDE(COALESCE(acceso_low_cost, {min_acc_lc}) - {min_acc_lc}, NULLIF({max_acc_lc} - {min_acc_lc}, 0)), 0) AS acceso_low_cost_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(deportividad, {min_depor}) - {min_depor}, NULLIF({max_depor} - {min_depor}, 0)), 0) AS deportividad_scaled,
            -- Mapeos existentes --
            CASE WHEN traccion = 'ALL' THEN 1.0 WHEN traccion = 'RWD' THEN 0.5 ELSE 0.0 END AS traccion_scaled,
            (CASE WHEN COALESCE(reductoras, FALSE) THEN 1.0 ELSE 0.0 END) AS reductoras_scaled,
            (CASE WHEN @penalizar_puertas = TRUE AND puertas <= 3 THEN {PENALTY_PUERTAS_BAJAS} ELSE 0.0 END) AS puertas_penalty
        FROM
            `thecarmentor-mvp2.web_cars.match_coches_pruebas`
    )
    SELECT
      -- Añade las nuevas columnas BQ si quieres ver sus valores originales fiabilidad, durabilidad, seguridad, comodidad, acceso_low_cost, deportividad, tecnologia (para después)
      nombre, ID, marca, modelo, cambio_automatico, tipo_mecanica, tipo_carroceria, 
      indice_altura_interior, batalla, estetica, premium, singular, altura_libre_suelo, 
      ancho, traccion, reductoras, puertas, plazas, precio_compra_contado,
      
      ( 
        estetica_scaled * @peso_estetica 
        + premium_scaled * @peso_premium
        + singular_scaled * @peso_singular
        + altura_scaled * @peso_altura
        + batalla_scaled * @peso_batalla 
        + indice_altura_scaled * @peso_indice_altura
        + ancho_scaled * @peso_ancho 
        + traccion_scaled * @peso_traccion
        + reductoras_scaled * @peso_reductoras
        + puertas_penalty
        -- NUEVOS TÉRMINOS DE SCORE PARA RATINGS --
        + fiabilidad_scaled * @peso_rating_fiabilidad_durabilidad  
        + durabilidad_scaled * @peso_rating_fiabilidad_durabilidad -- Usando el mismo peso para ambas
        + seguridad_scaled * @peso_rating_seguridad               
        + comodidad_scaled * @peso_rating_comodidad
        + fiabilidad_scaled * @peso_rating_impacto_ambiental  -- P4 (Impacto Ambiental) usa fiabilidad_scaled
        + durabilidad_scaled * @peso_rating_impacto_ambiental -- P4 (Impacto Ambiental) usa durabilidad_scaled (si así lo defines)
        + tecnologia_scaled * @peso_rating_tecnologia_conectividad -- P6
        -- PENALIZACIONES POR COMODIDAD --
        + (CASE WHEN @flag_penalizar_low_cost_comodidad = TRUE AND acceso_low_cost_scaled >= {UMBRAL_LOW_COST_PENALIZABLE} THEN {PENALTY_LOW_COST_POR_COMODIDAD} ELSE 0.0 END)
        + (CASE WHEN @flag_penalizar_deportividad_comodidad = TRUE AND deportividad_scaled >= {UMBRAL_DEPORTIVIDAD_PENALIZABLE} THEN {PENALTY_DEPORTIVIDAD_POR_COMODIDAD} ELSE 0.0 END)
        -- FIN NUEVOS TÉRMINOS Y PENALIZACIONES --
      ) AS score_total
    FROM ScaledData
    WHERE 1=1 
    """
    
    
    # --- Parámetros Iniciales (solo pesos para el score y flags) ---
    params = [
        bigquery.ScalarQueryParameter("peso_estetica",   "FLOAT64", pesos_completos["estetica"]),
        bigquery.ScalarQueryParameter("peso_premium", "FLOAT64", pesos_completos["premium"]),
        bigquery.ScalarQueryParameter("peso_singular", "FLOAT64", pesos_completos["singular"]),
        bigquery.ScalarQueryParameter("peso_altura", "FLOAT64", pesos_completos["altura_libre_suelo"]),
        bigquery.ScalarQueryParameter("peso_batalla", "FLOAT64", pesos_completos["batalla"]),
        bigquery.ScalarQueryParameter("peso_indice_altura", "FLOAT64", pesos_completos["indice_altura_interior"]),
        bigquery.ScalarQueryParameter("peso_ancho", "FLOAT64", pesos_completos["ancho"]),
        bigquery.ScalarQueryParameter("peso_traccion", "FLOAT64", pesos_completos["traccion"]),
        bigquery.ScalarQueryParameter("peso_reductoras", "FLOAT64", pesos_completos["reductoras"]),
        bigquery.ScalarQueryParameter("penalizar_puertas", "BOOL", penalizar_puertas_val),
        # --- NUEVOS PARÁMETROS DE PESO Y FLAGS ---
        bigquery.ScalarQueryParameter("peso_rating_fiabilidad_durabilidad", "FLOAT64", pesos_completos["rating_fiabilidad_durabilidad"]),
        bigquery.ScalarQueryParameter("peso_rating_seguridad", "FLOAT64", pesos_completos["rating_seguridad"]),
        bigquery.ScalarQueryParameter("peso_rating_comodidad", "FLOAT64", pesos_completos["rating_comodidad"]),
        bigquery.ScalarQueryParameter("peso_rating_impacto_ambiental", "FLOAT64", pesos_completos["rating_impacto_ambiental"]), # <-- Nuevo
        bigquery.ScalarQueryParameter("peso_rating_tecnologia_conectividad", "FLOAT64", pesos_completos["rating_tecnologia_conectividad"]), # <-- Nuevo
        bigquery.ScalarQueryParameter("flag_penalizar_low_cost_comodidad", "BOOL", flag_penalizar_low_cost_comod),
        bigquery.ScalarQueryParameter("flag_penalizar_deportividad_comodidad", "BOOL", flag_penalizar_deportividad_comod),
        # --- FIN NUEVOS PARÁMETROS ---
        bigquery.ScalarQueryParameter("k", "INT64", k)
    ]
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
        # Dejamos solo los que SÍ deben ser filtros duros si existen, 
        # o mantenemos el mapa vacío si no hay otros filtros numéricos duros.
        # Si tuvieras otros como "potencia_min_cv", irían aquí.
        # Por ahora, este mapa podría quedar vacío o no existir si no hay otros filtros numéricos.
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
    
    log_params_for_logging = [] 
    if params: # Asegurarse de que params no sea None o vacío
        for p in params:
            param_name = p.name
            param_value = getattr(p, 'value', getattr(p, 'values', None)) # Para Scalar y Array params
            
            param_type_str = "UNKNOWN" # Default
            if isinstance(p, bigquery.ScalarQueryParameter):
                param_type_str = p.type_ # Atributo correcto para el tipo escalar
            elif isinstance(p, bigquery.ArrayQueryParameter):
                param_type_str = f"ARRAY<{p.array_type}>" # Atributo correcto para el tipo de array

            log_params_for_logging.append({
                "name": param_name, 
                "value": param_value, 
                "type": param_type_str # Usar el tipo corregido
            })
    print("--- 🧠 SQL Query (Paso a Paso) ---\n", sql) 
    print("\n--- 📦 Parameters (Paso a Paso) ---\n", [(p.name, getattr(p, 'value', getattr(p, 'values', None))) for p in params]) 

    try:
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        query_job = client.query(sql, job_config=job_config)
        df = query_job.result().to_dataframe() 
        logging.info(f"✅ (Paso a Paso) BigQuery query ejecutada, {len(df)} resultados obtenidos.")
        #return df.to_dict(orient="records")
        return df.to_dict(orient="records"), sql, log_params_for_logging
    except Exception as e:
        logging.error(f"❌ (Paso a Paso) Error al ejecutar la query en BigQuery: {e}")
        traceback.print_exc()
        return [], sql, log_params_for_logging # Devolver SQL y params incluso si falla
    
#RESUMEN   
# MIN_MAX_RANGES: Debes añadir los rangos para fiabilidad, durabilidad, seguridad, comodidad, tecnologia y, crucialmente, para acceso_low_cost y deportividad (o como se llamen tus columnas BQ que representan esos conceptos).
# Nuevas Constantes: Definí PENALTY_LOW_COST_POR_COMODIDAD, PENALTY_DEPORTIVIDAD_POR_COMODIDAD, UMBRAL_LOW_COST_PENALIZABLE, UMBRAL_DEPORTIVIDAD_PENALIZABLE. Ajusta estos valores según necesites.
# pesos_completos: Ahora extrae los pesos para los nuevos ratings (ej: pesos.get("rating_fiabilidad_durabilidad", 0.0)).
# Nuevos Flags: Obtiene flag_penalizar_low_cost_comodidad y flag_penalizar_deportividad_comodidad del diccionario filtros.
# Desempaquetar Min/Max: Se desempaquetan los Min/Max para las nuevas columnas BQ.
# CTE ScaledData:
# Se añaden las líneas para calcular fiabilidad_scaled, durabilidad_scaled, seguridad_scaled, comodidad_scaled.
# Se añaden las líneas para calcular acceso_low_cost_scaled y deportividad_scaled.
# La penalización por puertas se mantiene.
# SELECT Final: Se añaden las columnas originales (fiabilidad, durabilidad, etc., y acceso_low_cost, deportividad) para que puedas ver sus valores.
# Cálculo score_total:
# Se añaden los términos para fiabilidad/durabilidad, seguridad y comodidad, multiplicados por sus respectivos @peso_rating_....
# Se añaden los dos nuevos CASE WHEN para las penalizaciones, usando los @flag_..., los umbrales y los valores de penalización.
# params: Se añaden los nuevos ScalarQueryParameter para los @peso_rating_... y los @flag_....
# Filtros WHERE: La lógica de filtros WHERE (transmisión, estetica_min, etc.) se mantiene como estaba.
# Recordatorios Antes de Probar:

# Actualiza MIN_MAX_RANGES con los rangos correctos para TODAS las columnas numéricas que escalas.
# Asegúrate de que tu tabla BQ tenga columnas llamadas fiabilidad, durabilidad, seguridad, comodidad, acceso_low_cost, deportividad (o los nombres que uses, y ajústalos en el SQL).
# Verifica que finalizar_y_presentar_node esté pasando los nuevos pesos (ej: rating_fiabilidad_durabilidad) en el diccionario pesos y los nuevos flags (ej: flag_penalizar_low_cost_comodidad) en el diccionario filtros a esta función buscar_coches_bq.
# Este es un cambio sustancial en el score. ¡Pruébalo con cuidado y observa cómo cambian los rankings!

