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

# Definir aquí los rangos mínimos y máximos para cada característica/Valores de bd
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
    "devaluacion": (0.0, 10.0), # Asumiendo una escala de 0-10 para depreciación en BQ
    "maletero_minimo": (11.0, 15000.0), # Ejemplo en litros, ¡USA TUS VALORES!
    "maletero_maximo": (11.0, 15000.0), # Ejemplo en litros, ¡USA TUS VALORES!
    "largo": (2450.0, 6400.0) ,       # Ejemplo en mm, ¡USA TUS VALORES!
    "autonomia_uso_maxima": (30.8, 1582.4), # --- NUEVO RANGO PARA AUTONOMÍA ---
    "peso": (470.0, 3500.0), 
    "indice_consumo_energia": (7.4, 133.0),
    "costes_de_uso": (3.0, 31.0), 
    "costes_mantenimiento": (1.0, 10.0) ,
    "par": (41.0, 967.0), 
    "capacidad_remolque_con_freno": (100.0, 3600.0), 
    "capacidad_remolque_sin_freno": (35.0, 1250.0),   
}
PENALTY_PUERTAS_BAJAS = -0.10
# --- NUEVAS PENALIZACIONES (AJUSTA ESTOS VALORES) ---
PENALTY_LOW_COST_POR_COMODIDAD = -0.15 # Cuánto restar si es muy low-cost y se quiere confort
PENALTY_DEPORTIVIDAD_POR_COMODIDAD = -0.15 # Cuánto restar si es muy deportivo y se quiere confort
# --- UMBRALES PARA PENALIZACIÓN (AJUSTA ESTOS VALORES, 0-1 después de escalar) ---
UMBRAL_LOW_COST_PENALIZABLE = 0.7 # Penalizar si acceso_low_cost_scaled >= 0.7
UMBRAL_DEPORTIVIDAD_PENALIZABLE = 0.7 # Penalizar si deportividad_scaled >= 0.7
# --- NUEVAS CONSTANTES PARA PENALIZACIÓN GRADUAL POR ANTIGÜEDAD ---
PENALTY_ANTIGUEDAD_MAS_10_ANOS = -0.30
PENALTY_ANTIGUEDAD_7_A_10_ANOS = -0.20
PENALTY_ANTIGUEDAD_5_A_7_ANOS  = -0.10

# --- NUEVAS CONSTANTES PARA BONIFICACIÓN/PENALIZACIÓN DISTINTIVO AMBIENTAL ---
BONUS_DISTINTIVO_ECO_CERO_C = 0.20  # Cuánto sumar si es C, ECO o CERO
PENALTY_DISTINTIVO_NA_B = -0.50   # Cuánto restar si es NA o B
BONUS_OCASION_POR_IMPACTO_AMBIENTAL = 0.20 #
# --------------------------------------------------------------------------

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

    # Pesos completos (incluyendo los nuevos ratings - DEBEN COINCIDIR CON RAW-WEIGHTS)
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
        "rating_impacto_ambiental": pesos.get("rating_impacto_ambiental", 0.0), 
        "rating_costes_uso": pesos.get("rating_costes_uso", 0.0), # Peso general para el concepto
        "fav_bajo_coste_uso_directo": pesos.get("fav_bajo_coste_uso_directo", 0.0),
        "fav_bajo_coste_mantenimiento_directo": pesos.get("fav_bajo_coste_mantenimiento_directo", 0.0),             
        "rating_tecnologia_conectividad": pesos.get("rating_tecnologia_conectividad", 0.0), 
        "devaluacion": pesos.get("devaluacion", 0.0), 
        # Las claves deben coincidir con las generadas en compute_raw_weights
        "maletero_minimo_score": pesos.get("maletero_minimo_score", 0.0),
        "maletero_maximo_score": pesos.get("maletero_maximo_score", 0.0),
        "largo_vehiculo_score": pesos.get("largo_vehiculo_score", 0.0),
        "autonomia_vehiculo": pesos.get("autonomia_vehiculo", 0.0),
        "fav_bajo_peso": pesos.get("fav_bajo_peso", 0.0),
        "fav_bajo_consumo": pesos.get("fav_bajo_consumo", 0.0),
        "par_motor_remolque_score": pesos.get("par_motor_remolque_score", 0.0),
        "cap_remolque_cf_score": pesos.get("cap_remolque_cf_score", 0.0),
        "cap_remolque_sf_score": pesos.get("cap_remolque_sf_score", 0.0),
        
    }

    # Flags de penalización (vienen en el dict 'filtros') --- FLAGS (DEBEN VENIR EN EL DICT 'filtros') ---
    penalizar_puertas_val = bool(filtros.get("penalizar_puertas_bajas", False))
    flag_penalizar_low_cost_comod = bool(filtros.get("flag_penalizar_low_cost_comodidad", False))
    flag_penalizar_deportividad_comod = bool(filtros.get("flag_penalizar_deportividad_comodidad", False))
    flag_penalizar_antiguo_tec_val = bool(filtros.get("flag_penalizar_antiguo_por_tecnologia", False))
    flag_aplicar_logica_distintivo_val = bool(filtros.get("aplicar_logica_distintivo_ambiental", False))

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
    min_coste_uso, max_coste_uso = MIN_MAX_RANGES["costes_de_uso"]
    min_coste_mante, max_coste_mante = MIN_MAX_RANGES["costes_mantenimiento"]
    min_tec, max_tec = MIN_MAX_RANGES["tecnologia"] 
    min_acc_lc, max_acc_lc = MIN_MAX_RANGES["acceso_low_cost"] # Necesario para penalización
    min_depor, max_depor = MIN_MAX_RANGES["deportividad"]    # Necesario para penalización
    min_depr, max_depr = MIN_MAX_RANGES["devaluacion"]
    min_mal_min, max_mal_min = MIN_MAX_RANGES["maletero_minimo"]
    min_mal_max, max_mal_max = MIN_MAX_RANGES["maletero_maximo"]
    min_largo, max_largo = MIN_MAX_RANGES["largo"]
    min_auton, max_auton = MIN_MAX_RANGES["autonomia_uso_maxima"]
    min_peso_kg, max_peso_kg = MIN_MAX_RANGES["peso"]
    min_consumo, max_consumo = MIN_MAX_RANGES["indice_consumo_energia"]
    min_par, max_par = MIN_MAX_RANGES["par"]
    min_cap_cf, max_cap_cf = MIN_MAX_RANGES["capacidad_remolque_con_freno"]
    min_cap_sf, max_cap_sf = MIN_MAX_RANGES["capacidad_remolque_sin_freno"]

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
              -- --- NUEVOS CAMPOS ESCALADOS (INVERTIDOS PORQUE MENOR ES MEJOR) ---
            COALESCE(SAFE_DIVIDE({max_coste_uso} - COALESCE(costes_de_uso, {max_coste_uso}), NULLIF({max_coste_uso} - {min_coste_uso}, 0)), 0) AS costes_de_uso_scaled,
            COALESCE(SAFE_DIVIDE({max_coste_mante} - COALESCE(costes_mantenimiento, {max_coste_mante}), NULLIF({max_coste_mante} - {min_coste_mante}, 0)), 0) AS costes_mantenimiento_scaled,
            -- --- FIN NUEVOS CAMPOS ESCALADOS ---
            COALESCE(SAFE_DIVIDE(COALESCE(tecnologia, {min_tec}) - {min_tec}, NULLIF({max_tec} - {min_tec}, 0)), 0) AS tecnologia_scaled, -- <-- Nuevo escalado
            -- CAMPOS ESCALADOS PARA PENALIZACIONES --
            COALESCE(SAFE_DIVIDE(COALESCE(acceso_low_cost, {min_acc_lc}) - {min_acc_lc}, NULLIF({max_acc_lc} - {min_acc_lc}, 0)), 0) AS acceso_low_cost_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(deportividad, {min_depor}) - {min_depor}, NULLIF({max_depor} - {min_depor}, 0)), 0) AS deportividad_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(devaluacion, {min_depr}) - {min_depr}, NULLIF({max_depr} - {min_depr}, 0)), 0) AS devaluacion_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(maletero_minimo, {min_mal_min}) - {min_mal_min}, NULLIF({max_mal_min} - {min_mal_min}, 0)), 0) AS maletero_minimo_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(maletero_maximo, {min_mal_max}) - {min_mal_max}, NULLIF({max_mal_max} - {min_mal_max}, 0)), 0) AS maletero_maximo_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(largo, {min_largo}) - {min_largo}, NULLIF({max_largo} - {min_largo}, 0)), 0) AS largo_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(autonomia_uso_maxima, {min_auton}) - {min_auton}, NULLIF({max_auton} - {min_auton}, 0)), 0) AS autonomia_uso_maxima_scaled,
            -- Mapeos existentes --
            CASE WHEN traccion = 'ALL' THEN 1.0 WHEN traccion = 'RWD' THEN 0.5 ELSE 0.0 END AS traccion_scaled,
            -- --- NUEVOS CAMPOS ESCALADOS (INVERTIDOS) ---
            COALESCE(SAFE_DIVIDE({max_peso_kg} - COALESCE(peso, {max_peso_kg}), NULLIF({max_peso_kg} - {min_peso_kg}, 0)), 0) AS bajo_peso_scaled, -- Invertido
            COALESCE(SAFE_DIVIDE({max_consumo} - COALESCE(indice_consumo_energia, {max_consumo}), NULLIF({max_consumo} - {min_consumo}, 0)), 0) AS bajo_consumo_scaled, -- Invertido
            COALESCE(SAFE_DIVIDE(COALESCE(par, {min_par}) - {min_par}, NULLIF({max_par} - {min_par}, 0)), 0) AS par_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(capacidad_remolque_con_freno, {min_cap_cf}) - {min_cap_cf}, NULLIF({max_cap_cf} - {min_cap_cf}, 0)), 0) AS cap_remolque_cf_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(capacidad_remolque_sin_freno, {min_cap_sf}) - {min_cap_sf}, NULLIF({max_cap_sf} - {min_cap_sf}, 0)), 0) AS cap_remolque_sf_scaled, 
            (CASE WHEN COALESCE(reductoras, FALSE) THEN 1.0 ELSE 0.0 END) AS reductoras_scaled,
            (CASE WHEN @penalizar_puertas = TRUE AND puertas <= 3 THEN {PENALTY_PUERTAS_BAJAS} ELSE 0.0 END) AS puertas_penalty
        FROM
            `thecarmentor-mvp2.web_cars.match_coches_pruebas`
    )
    SELECT
      -- Añade las nuevas columnas BQ si quieres ver sus valores originales:
      nombre, ID , modelo, cambio_automatico, tipo_mecanica, tipo_carroceria, 
      indice_altura_interior, estetica, premium, singular,  seguridad, comodidad, acceso_low_cost, deportividad, tecnologia, devaluacion, altura_libre_suelo, maletero_minimo, maletero_maximo,
      traccion, reductoras, plazas, precio_compra_contado, largo, autonomia_uso_maxima, distintivo_ambiental, anos_vehiculo, ocasion,
      peso AS peso_original_kg, indice_consumo_energia AS consumo_original, costes_de_uso, costes_mantenimiento,par, capacidad_remolque_con_freno,capacidad_remolque_sin_freno,
      
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
        + maletero_minimo_scaled * @peso_maletero_minimo_score
        + maletero_maximo_scaled * @peso_maletero_maximo_score
        + largo_scaled * @peso_largo_vehiculo_score
        + devaluacion_scaled * @peso_devaluacion
        + autonomia_uso_maxima_scaled * @peso_autonomia_vehiculo
        -- Estos se activan si el peso correspondiente es > 0 (calculado en compute_raw_weights)
        + bajo_peso_scaled * @peso_fav_bajo_peso
        + bajo_consumo_scaled * @peso_fav_bajo_consumo
        -- --- NUEVOS TÉRMINOS DE SCORE PARA COSTES DE USO Y MANTENIMIENTO ---
        + costes_de_uso_scaled * @peso_fav_bajo_coste_uso_directo
        + costes_mantenimiento_scaled * @peso_fav_bajo_coste_mantenimiento_directo
        + par_scaled * @peso_par_motor_remolque_score
        + cap_remolque_cf_scaled * @peso_cap_remolque_cf_score
        + cap_remolque_sf_scaled * @peso_cap_remolque_sf_score
        -- PENALIZACIONES POR COMODIDAD y  ANTIGÜEDAD--
        + (CASE WHEN @flag_penalizar_low_cost_comodidad = TRUE AND acceso_low_cost_scaled >= {UMBRAL_LOW_COST_PENALIZABLE} THEN {PENALTY_LOW_COST_POR_COMODIDAD} ELSE 0.0 END)
        + (CASE WHEN @flag_penalizar_deportividad_comodidad = TRUE AND deportividad_scaled >= {UMBRAL_DEPORTIVIDAD_PENALIZABLE} THEN {PENALTY_DEPORTIVIDAD_POR_COMODIDAD} ELSE 0.0 END)
        + (CASE WHEN @flag_penalizar_antiguo_tec = TRUE THEN
                 CASE
                     WHEN anos_vehiculo > 10 THEN {PENALTY_ANTIGUEDAD_MAS_10_ANOS}
                     WHEN anos_vehiculo > 7  THEN {PENALTY_ANTIGUEDAD_7_A_10_ANOS}
                     WHEN anos_vehiculo > 5  THEN {PENALTY_ANTIGUEDAD_5_A_7_ANOS}
                     ELSE 0.0 
                 END
             ELSE 0.0 
           END)
        -- --- NUEVA LÓGICA PARA DISTINTIVO AMBIENTAL ---
        + (CASE
             WHEN @flag_aplicar_logica_distintivo = TRUE THEN
                 CASE
                     WHEN distintivo_ambiental IN ('0', 'ECO', 'C') THEN {BONUS_DISTINTIVO_ECO_CERO_C}
                     WHEN distintivo_ambiental IN ('B', 'NA') THEN {PENALTY_DISTINTIVO_NA_B}
                     ELSE 0.0 -- Para otros distintivos o si es NULL
                 END
             ELSE 0.0 -- Si el flag no está activo
           END)
        -- --- NUEVA LÓGICA PARA FAVORECER 'ocasion' ---
        + (CASE
             WHEN @flag_aplicar_logica_distintivo = TRUE AND COALESCE(ocasion, FALSE) = TRUE THEN {BONUS_OCASION_POR_IMPACTO_AMBIENTAL}
             ELSE 0.0
           END)
        -- --- FIN NUEVA LÓGICA 'ocasion' ---
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
         # --- NUEVOS PARÁMETROS DE PESO_COSTES DE USO ---
        bigquery.ScalarQueryParameter("peso_rating_costes_uso", "FLOAT64", pesos_completos["rating_costes_uso"]), # Para el peso general del concepto
        bigquery.ScalarQueryParameter("peso_fav_bajo_coste_uso_directo", "FLOAT64", pesos_completos["fav_bajo_coste_uso_directo"]),
        bigquery.ScalarQueryParameter("peso_fav_bajo_coste_mantenimiento_directo", "FLOAT64", pesos_completos["fav_bajo_coste_mantenimiento_directo"]),
        bigquery.ScalarQueryParameter("peso_devaluacion", "FLOAT64", pesos_completos["devaluacion"]),
        bigquery.ScalarQueryParameter("peso_maletero_minimo_score", "FLOAT64", pesos_completos["maletero_minimo_score"]),
        bigquery.ScalarQueryParameter("peso_maletero_maximo_score", "FLOAT64", pesos_completos["maletero_maximo_score"]),
        bigquery.ScalarQueryParameter("peso_largo_vehiculo_score", "FLOAT64", pesos_completos["largo_vehiculo_score"]),
        bigquery.ScalarQueryParameter("peso_autonomia_vehiculo", "FLOAT64", pesos_completos["autonomia_vehiculo"]),
        bigquery.ScalarQueryParameter("peso_fav_bajo_peso", "FLOAT64", pesos_completos["fav_bajo_peso"]),
        bigquery.ScalarQueryParameter("peso_fav_bajo_consumo", "FLOAT64", pesos_completos["fav_bajo_consumo"]),
        bigquery.ScalarQueryParameter("peso_par_motor_remolque_score", "FLOAT64", pesos_completos["par_motor_remolque_score"]),
        bigquery.ScalarQueryParameter("peso_cap_remolque_cf_score", "FLOAT64", pesos_completos["cap_remolque_cf_score"]),
        bigquery.ScalarQueryParameter("peso_cap_remolque_sf_score", "FLOAT64", pesos_completos["cap_remolque_sf_score"]),
        bigquery.ScalarQueryParameter("flag_penalizar_low_cost_comodidad", "BOOL", flag_penalizar_low_cost_comod),
        bigquery.ScalarQueryParameter("flag_penalizar_deportividad_comodidad", "BOOL", flag_penalizar_deportividad_comod),
        bigquery.ScalarQueryParameter("flag_penalizar_antiguo_tec", "BOOL", flag_penalizar_antiguo_tec_val),
        bigquery.ScalarQueryParameter("flag_aplicar_logica_distintivo", "BOOL", flag_aplicar_logica_distintivo_val),
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
        for p_idx, p in enumerate(params): # Usar enumerate si necesitas un índice para depurar
            param_name = "unknown_param_name"
            param_value = None
            param_type_str = "UNKNOWN_TYPE"
            
            try:
                param_name = p.name
                param_value = getattr(p, 'value', getattr(p, 'values', "N/A")) # Para Scalar y Array params
                
                if isinstance(p, bigquery.ScalarQueryParameter):
                    param_type_str = p.type_ # Atributo correcto para el tipo escalar
                elif isinstance(p, bigquery.ArrayQueryParameter):
                    param_type_str = f"ARRAY<{p.array_type}>" # Atributo correcto para el tipo de array
                else:
                    param_type_str = f"UNEXPECTED_PARAM_TYPE ({type(p)})"

                log_params_for_logging.append({
                    "name": param_name, 
                    "value": param_value, 
                    "type": param_type_str 
                })
            except AttributeError as e_attr:
                # Esto puede pasar si un objeto en 'params' no es lo que esperamos
                logging.error(f"Error al procesar parámetro para logging en índice {p_idx}: {e_attr}. Objeto: {p}")
                log_params_for_logging.append({
                    "name": f"error_param_{p_idx}", 
                    "value": "Error al procesar", 
                    "type": "ERROR"
                })
            except Exception as e_gen:
                logging.error(f"Error general al procesar parámetro para logging en índice {p_idx}: {e_gen}. Objeto: {p}")
                log_params_for_logging.append({
                    "name": f"error_param_{p_idx}", 
                    "value": "Error general al procesar", 
                    "type": "ERROR"
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

