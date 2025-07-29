# En utils/bigquery_search.py
import logging
import traceback
from typing import Optional, List, Dict, Any , Tuple
from google.cloud import bigquery
from config.settings import ( 
    MIN_MAX_RANGES,PENALTY_PUERTAS_BAJAS,PENALTY_LOW_COST_POR_COMODIDAD, PENALTY_DEPORTIVIDAD_POR_COMODIDAD, PENALTY_ANTIGUEDAD_7_A_10_ANOS, PENALTY_ANTIGUEDAD_10_A_15_ANOS, PENALTY_ANTIGUEDAD_MAS_15_ANOS, PENALTY_ANTIGUEDAD_5_A_7_ANOS, BONUS_DISTINTIVO_ECO_CERO_C, PENALTY_DISTINTIVO_NA_B, BONUS_OCASION_POR_IMPACTO_AMBIENTAL,  PENALTY_BEV_REEV_AVENTURA_OCASIONAL,PENALTY_PHEV_AVENTURA_OCASIONAL, PENALTY_ELECTRIFICADOS_AVENTURA_EXTREMA,BONUS_CARROCERIA_MONTANA, BONUS_CARROCERIA_COMERCIAL,BONUS_CARROCERIA_PASAJEROS_PRO, PENALTY_CARROCERIA_NO_AVENTURA , BONUS_SUV_AVENTURA_OCASIONAL, BONUS_TODOTERRENO_AVENTURA_EXTREMA, BONUS_PICKUP_AVENTURA_EXTREMA, BONUS_CARROCERIA_OBJETOS_ESPECIALES, PENALTY_CARROCERIA_OBJETOS_ESPECIALES,  BONUS_CARROCERIA_CONFORT, FACTOR_CONVERSION_PRECIO_CUOTA,
    BONUS_OCASION_POR_USO_OCASIONAL, PENALTY_ELECTRIFICADOS_POR_USO_OCASIONAL, BONUS_BEV_REEV_USO_DEFINIDO,PENALTY_PHEV_USO_INTENSIVO_LARGO, BONUS_MOTOR_POCO_KM, PENALTY_OCASION_POCO_KM, PENALTY_OCASION_MEDIO_KM, BONUS_MOTOR_MUCHO_KM, PENALTY_OCASION_MUCHO_KM, PENALTY_OCASION_MUY_ALTO_KM_V2 ,BONUS_BEV_MUY_ALTO_KM , BONUS_REEV_MUY_ALTO_KM , BONUS_DIESEL_HEVD_MUY_ALTO_KM, BONUS_PHEVD_GLP_GNV_MUY_ALTO_KM, BONUS_PUNTO_CARGA_PROPIO, PENALTY_AWD_NINGUNA_AVENTURA,  BONUS_AWD_AVENTURA_OCASIONAL, BONUS_AWD_AVENTURA_EXTREMA, BONUS_AWD_ZONA_NIEVE, BONUS_AWD_ZONA_MONTA, BONUS_REDUCTORAS_AVENTURA_EXTREMA , PENALTY_ZBE_DISTINTIVO_DESFAVORABLE_NA, PENALTY_ZBE_DISTINTIVO_DESFAVORABLE_B , BONUS_ZBE_DISTINTIVO_FAVORABLE_C , BONUS_ZBE_DISTINTIVO_FAVORABLE_ECO_CERO, 
    BONUS_AWD_NINGUNA_AVENTURA_CLIMA_ADVERSO, PENALTY_DIESEL_CIUDAD , BONUS_DIESEL_CIUDAD_OCASIONAL, FACTOR_ESCALA_BASE, PENALTY_OCASION_KILOMETRAJE_EXTREMO, FACTOR_BONUS_RATING_CRITICO,FACTOR_BONUS_RATING_FUERTE, FACTOR_BONUS_FIABILIDAD_POR_IMPACTO, FACTOR_BONUS_DURABILIDAD_POR_IMPACTO, BONUS_REDUCTORAS_AVENTURA_OCASIONAL, FACTOR_BONUS_FIAB_DUR_CRITICO , FACTOR_BONUS_FIAB_DUR_FUERTE,FACTOR_BONUS_COSTES_CRITICO, PENALTY_ANO_PRE_1990 ,PENALTY_ANO_1991_1995, PENALTY_ANO_1996_2000 ,PENALTY_DIESEL_2001_2006, PENALTY_TAMANO_CARRETERA, PENALTY_TAMANO_CIUDAD, BONUS_CARROCERIA_COUPE_SINGULAR, BONUS_CARROCERIA_DESCAPOTABLE_SINGULAR, BONUS_CARROCERIA_COUPE_DEPORTIVO, BONUS_CARROCERIA_DESCAPOTABLE_DEPORTIVO, PENALTY_CARROCERIA_COMERCIAL_DEPORTIVO, PENALTY_CARROCERIA_FURGONETA_DEPORTIVO, 
    PENALTY_MALETERO_INSUFICIENTE , PENALTY_COMERCIAL_USO_PERSONAL, BONUS_COCHE_MUY_CORTO_CIUDAD, BONUS_COCHE_LIGERO_CIUDAD , BONUS_COCHE_CORTO_CIUDAD_2 , BONUS_COCHE_LIGERO_CIUDAD_2,  UMBRAL_LARGO_CIUDAD_MM , UMBRAL_LARGO_CARRETERA_MM, PENALTY_CARROCERIA_SUV_DEPORTIVO, PENALTY_BEV_NO_DEPORTIVO_LIFESTYLE, FACTOR_PRECIO_MINIMO
    )
# --- Configuración de Logging ---
logger = logging.getLogger(__name__) 

FiltrosDict = Dict[str, Any] 
PesosDict = Dict[str, float]

# Agrupación de coches "iguales" (PARTITION BY):
# El sistema considera que dos coches son "el mismo" si coinciden exactamente en estas cuatro características:

# nombre (la marca, ej: "Seat") para pruebas este no va por ahora
# modelo (el modelo, ej: "León")
# tipo_mecanica (el motor, ej: "GLP")
# cambio_automatico (si es automático o manual)

# La mejor forma de implementar esta regla ("máximo 2 coches por marca") es directamente en la consulta de BigQuery, después de haber calculado todas las puntuaciones y de haber eliminado los duplicados.

# Usaremos una función de ventana ROW_NUMBER() adicional, muy parecida a la que ya usas para deduplicar, pero esta vez la usaremos para "numerar" los coches dentro de cada marca.

# Solución: Modificar la Consulta SQL
# Vamos a reestructurar el final de tu consulta en buscar_coches_bq para añadir esta nueva capa de filtrado.

# Lógica Actual (Simplificada)
# Tu consulta actual termina con una estructura parecida a esta:

# DeduplicatedData: Elimina duplicados de modelo/tipo_mecanica.
# SELECT Final: Ordena todo por score_total y coge los k mejores.
# Nueva Lógica Integrada y Corregida
# Vamos a insertar un paso intermedio. Reemplaza el final de tu consulta (desde la CTE DeduplicatedData en adelante) por esta nueva estructura:

# SQL

# -- ... (Tus CTEs ScaledData y RankedData se mantienen igual que antes) ...

# ), -- Cierra la CTE RankedData

# -- PASO 2 (MODIFICADO): Calculamos el score_total y eliminamos duplicados de modelo/versión
# DeduplicatedData AS (
#     SELECT
#         *,
#         -- Calculamos el score_total aquí para poder usarlo en los siguientes pasos
#         (puntuacion_base + ajustes_experto) AS score_total,
#         ROW_NUMBER() OVER(
#             PARTITION BY modelo, tipo_mecanica
#             ORDER BY (puntuacion_base + ajustes_experto) DESC, precio_compra_contado ASC
#         ) as rn
#     FROM 
#         RankedData
# ),

# -- ✅ PASO 3 (NUEVO): Ranking por marca para diversificar
# BrandRankedData AS (
#     SELECT
#         *,
#         -- Numeramos los coches DENTRO de cada marca, del mejor al peor score
#         ROW_NUMBER() OVER(
#             PARTITION BY marca
#             ORDER BY score_total DESC
#         ) as brand_rank
#     FROM 
#         DeduplicatedData
#     WHERE 
#         rn = 1 -- Nos aseguramos de trabajar solo con los coches ya deduplicados
# )

# -- ✅ PASO 4 (FINAL): Aplicamos el filtro de diversificación
# SELECT
#     * EXCEPT(rn, brand_rank) -- No necesitamos mostrar las columnas de ranking
# FROM 
#     BrandRankedData
# WHERE 
#     brand_rank <= 2 -- La nueva regla: solo nos quedamos con el 1º y 2º de cada marca
# ORDER BY 
#     score_total DESC -- Ordenamos la lista final por la puntuación general
# LIMIT @k -- Aplicamos el límite final de resultados a mostrar
# Explicación del Nuevo Flujo
# DeduplicatedData (Paso 2): Primero, calculamos el score_total y eliminamos las versiones duplicadas de un mismo modelo (como hacías antes). El resultado es una lista limpia donde cada coche aparece solo una vez, con su puntuación final.
# BrandRankedData (Paso 3 - El Nuevo Truco):
# Tomamos esa lista limpia.
# PARTITION BY marca: Agrupamos virtualmente todos los coches por su marca (todos los Kia juntos, todos los Subaru juntos, etc.).
# ROW_NUMBER() OVER(...): Dentro de cada grupo de marca, los numeramos del 1 en adelante, ordenándolos por su score_total de mayor a menor. Al mejor Kia se le asigna brand_rank = 1, al segundo mejor Kia brand_rank = 2, y así sucesivamente.
# SELECT Final (Paso 4):
# WHERE brand_rank <= 2: Esta es tu nueva regla en acción. Filtramos la lista para quedarnos únicamente con aquellos coches cuyo ranking dentro de su marca sea 1 o 2.
# ORDER BY score_total DESC LIMIT @k: Finalmente, de la lista ya diversificada, tomamos los @k coches con la puntuación más alta en general para presentárselos al usuario.

#------------------------------------------------------------------------------------------------

def buscar_coches_bq(
    filtros: Optional[FiltrosDict],
    pesos: Optional[PesosDict], 
    k: int
) -> Tuple[List[Dict[str, Any]], str, List[Dict[str, Any]]]:
    
    if not filtros: filtros = {}
    if not pesos: pesos = {}

    try:
        client = bigquery.Client()
    except Exception as e_auth:
        logging.error(f"Error al inicializar cliente BigQuery: {e_auth}")
        return [], f"Error BQ Auth: {e_auth}", []

    # PASO 1: PREPARACIÓN DE DATOS (Pesos, Flags, Min/Max)
    # (Esta parte se mantiene igual)
    pesos_completos = {
        "estetica": pesos.get("estetica", 0.0), 
        "premium": pesos.get("premium", 0.0),
        "singular": pesos.get("singular", 0.0), 
        "altura_libre_suelo": pesos.get("altura_libre_suelo", 0.0),
        "batalla": pesos.get("batalla", 0.0), 
        "indice_altura_interior": pesos.get("indice_altura_interior", 0.0), 
        "ancho_general_score": pesos.get("ancho", 0.0),
        "rating_durabilidad": pesos.get("rating_durabilidad", 0.0),
        "rating_fiabilidad": pesos.get("rating_fiabilidad", 0.0),
        "rating_seguridad": pesos.get("rating_seguridad", 0.0),
        "rating_comodidad": pesos.get("rating_comodidad", 0.0),
        "rating_impacto_ambiental": pesos.get("rating_impacto_ambiental", 0.0), 
        "rating_costes_uso": pesos.get("rating_costes_uso", 0.0),
        "rating_tecnologia_conectividad": pesos.get("rating_tecnologia_conectividad", 0.0),
        "devaluacion": pesos.get("devaluacion", 0.0), 
        "maletero_minimo_score": pesos.get("maletero_minimo_score", 0.0),
        "maletero_maximo_score": pesos.get("maletero_maximo_score", 0.0),
        "largo_vehiculo_score": pesos.get("largo_vehiculo_score", 0.0),
        "autonomia_uso_maxima": pesos.get("autonomia_uso_maxima", 0.0),
        "fav_bajo_peso": pesos.get("fav_bajo_peso", 0.0),
        "fav_bajo_consumo": pesos.get("fav_bajo_consumo", 0.0),
        "fav_bajo_coste_uso_directo": pesos.get("fav_bajo_coste_uso_directo", 0.0),
        "fav_bajo_coste_mantenimiento_directo": pesos.get("fav_bajo_coste_mantenimiento_directo", 0.0),             
        "par_motor_remolque_score": pesos.get("par_motor_remolque_score", 0.0),
        "cap_remolque_cf_score": pesos.get("cap_remolque_cf_score", 0.0),
        "cap_remolque_sf_score": pesos.get("cap_remolque_sf_score", 0.0),
        "fav_menor_superficie_planta": pesos.get("fav_menor_superficie_planta", 0.0),
        "fav_menor_diametro_giro": pesos.get("fav_menor_diametro_giro", 0.0),
        "fav_menor_largo_garage": pesos.get("fav_menor_largo_garage", 0.0),
        "fav_menor_ancho_garage": pesos.get("fav_menor_ancho_garage", 0.0),
        "fav_menor_alto_garage": pesos.get("fav_menor_alto_garage", 0.0),
        "deportividad_style_score": pesos.get("deportividad_style_score", 0.0),
        "fav_menor_rel_peso_potencia_score": pesos.get("fav_menor_rel_peso_potencia_score", 0.0),
        "potencia_maxima_style_score": pesos.get("potencia_maxima_style_score", 0.0),
        "par_motor_style_score": pesos.get("par_motor_style_score", 0.0),
        "fav_menor_aceleracion_score": pesos.get("fav_menor_aceleracion_score", 0.0),
        "peso_autonomia_uso_principal": pesos.get("autonomia_uso_principal", 0.0),
        "peso_autonomia_uso_2nd_drive":  pesos.get("autonomia_uso_2nd_drive", 0.0),
        "peso_menor_tiempo_carga_min": pesos.get("menor_tiempo_carga_min", 0.0),
        "peso_potencia_maxima_carga_AC":  pesos.get("potencia_maxima_carga_AC", 0.0),
        "peso_potencia_maxima_carga_DC":  pesos.get("potencia_maxima_carga_DC", 0.0),     
    }

    # ... el resto de la preparación de flags y min/max se mantiene igual ...
    penalizar_puertas_val = bool(filtros.get("penalizar_puertas_bajas", False))
    flag_penalizar_low_cost_comod = bool(filtros.get("flag_penalizar_low_cost_comodidad", False))
    flag_penalizar_deportividad_comod = bool(filtros.get("flag_penalizar_deportividad_comodidad", False))
    flag_penalizar_antiguo_tec_val = bool(filtros.get("flag_penalizar_antiguo_por_tecnologia", False))
    flag_aplicar_logica_distintivo_val = bool(filtros.get("aplicar_logica_distintivo_ambiental", False))
    flag_es_municipio_zbe_val = bool(filtros.get("es_municipio_zbe", False))
    flag_pen_bev_reev_ocas_val = bool(filtros.get("penalizar_bev_reev_aventura_ocasional", False))
    flag_pen_phev_ocas_val = bool(filtros.get("penalizar_phev_aventura_ocasional", False))
    flag_pen_electrif_extr_val = bool(filtros.get("penalizar_electrificados_aventura_extrema", False))
    flag_fav_car_montana_val = bool(filtros.get("favorecer_carroceria_montana", False))
    flag_fav_car_comercial_val = bool(filtros.get("favorecer_carroceria_comercial", False))
    flag_fav_car_pasajeros_pro_val = bool(filtros.get("favorecer_carroceria_pasajeros_pro", False))
    flag_desfav_car_no_aventura_val = bool(filtros.get("desfavorecer_carroceria_no_aventura", False))
    flag_fav_suv_aventura_ocasional = bool(filtros.get("favorecer_suv_aventura_ocasional", False))
    flag_fav_pickup_todoterreno_aventura_extrema = bool(filtros.get("favorecer_pickup_todoterreno_aventura_extrema", False))
    flag_aplicar_logica_objetos_especiales = bool(filtros.get("aplicar_logica_objetos_especiales", False))
    flag_fav_carroceria_confort = bool(filtros.get("favorecer_carroceria_confort", False))
    flag_logica_uso_ocasional_val = bool(filtros.get("flag_logica_uso_ocasional", False))
    flag_favorecer_bev_val = bool(filtros.get("flag_favorecer_bev_uso_definido", False))
    flag_penalizar_phev_val = bool(filtros.get("flag_penalizar_phev_uso_intensivo", False))
    flag_favorecer_electrificados_val = bool(filtros.get("flag_favorecer_electrificados_por_punto_carga", False))
    km_anuales_estimados_val = filtros.get("km_anuales_estimados") or 0
    penalizar_awd_ninguna_val = bool(filtros.get("penalizar_awd_ninguna_aventura", False))
    favorecer_awd_ocasional_val = bool(filtros.get("favorecer_awd_aventura_ocasional", False))
    favorecer_awd_extrema_val = bool(filtros.get("favorecer_awd_aventura_extrema", False))
    flag_bonus_nieve_val = bool(filtros.get("flag_bonus_awd_nieve", False))
    flag_bonus_montana_val = bool(filtros.get("flag_bonus_awd_montana", False))
    flag_reductoras_aventura_val = filtros.get("flag_logica_reductoras_aventura")
    flag_bonus_clima_val = bool(filtros.get("flag_bonus_awd_clima_adverso", False))
    flag_diesel_ciudad_val = filtros.get("flag_logica_diesel_ciudad")
    flag_bonus_seguridad_critico_val = bool(filtros.get("flag_bonus_seguridad_critico", False))
    flag_bonus_seguridad_fuerte_val =  bool(filtros.get("flag_bonus_seguridad_fuerte", False))
    flag_bonus_fiab_dur_critico_val = bool(filtros.get("flag_bonus_fiab_dur_critico", False))
    flag_bonus_fiab_dur_fuerte_val =  bool(filtros.get("flag_bonus_fiab_dur_fuerte", False))
    flag_bonus_costes_critico = bool(filtros.get("flag_bonus_costes_critico", False))
    flag_penalizar_tamano_val = bool(filtros.get("flag_penalizar_tamano_no_compacto", False))
    flag_bonus_singularidad_lifestyle = bool(filtros.get("flag_penalizar_tamano_no_compacto", False))
    flag_deportividad_lifestyle = bool(filtros.get("flag_deportividad_lifestyle", False))
    flag_ajuste_maletero_personal = bool(filtros.get("flag_ajuste_maletero_personal", False))
    flag_coche_ciudad_perfil = bool(filtros.get("flag_coche_ciudad_perfil", False))
    flag_coche_ciudad_2_perfil = bool(filtros.get("flag_coche_ciudad_2_perfil", False))
    flag_es_conductor_urbano =  bool(filtros.get("flag_es_conductor_urbano", False))
    
    
    m = MIN_MAX_RANGES
    min_est, max_est = m["estetica"]; min_prem, max_prem = m["premium"]; min_sing, max_sing = m["singular"]
    min_alt_ls, max_alt_ls = m["altura_libre_suelo"]; min_bat, max_bat = m["batalla"]; min_ind_alt, max_ind_alt = m["indice_altura_interior"]
    min_anc, max_anc = m["ancho"]; min_fiab, max_fiab = m["fiabilidad"]; 
    min_durab, max_durab = m["durabilidad"]; 
    min_seg, max_seg = m["seguridad"]; min_comod, max_comod = m["comodidad"]; min_tec, max_tec = m["tecnologia"]
    min_deval, max_deval = m["devaluacion"]; min_mal_min, max_mal_min = m["maletero_minimo"]; min_mal_max, max_mal_max = m["maletero_maximo"]
    min_largo, max_largo = m["largo"]; min_acc_lc, max_acc_lc = m["acceso_low_cost"]; min_depor_bq, max_depor_bq = m["deportividad"]
    min_auton, max_auton = m["autonomia_uso_maxima"]; min_peso_kg, max_peso_kg = m["peso"]; min_consumo, max_consumo = m["indice_consumo_energia"]
    min_coste_uso, max_coste_uso = m["costes_de_uso"]; min_coste_mante, max_coste_mante = m["costes_mantenimiento"]
    min_par, max_par = m["par"]; min_cap_cf, max_cap_cf = m["capacidad_remolque_con_freno"]; min_cap_sf, max_cap_sf = m["capacidad_remolque_sin_freno"]
    min_sup_planta, max_sup_planta = m["superficie_planta"]; min_diam_giro, max_diam_giro = m["diametro_giro"]
    min_alto_veh, max_alto_veh = m["alto_vehiculo"]; min_rel_pp, max_rel_pp = m["relacion_peso_potencia"]; min_pot_max, max_pot_max = m["potencia_maxima"]; min_acel, max_acel = m["aceleracion_0_100"] 
    min_auto_p, max_auto_p = m["autonomia_uso_principal"]; min_auto_2, max_auto_2 = m["autonomia_uso_2nd_drive"]
    min_t_carga, max_t_carga = m["tiempo_carga_min"]; min_pot_ac, max_pot_ac = m["potencia_maxima_carga_AC"]
    min_pot_dc, max_pot_dc = m["potencia_maxima_carga_DC"]

    # PASO 2: CONSTRUCCIÓN DE PARÁMETROS Y FILTROS
    # (Esta parte se mantiene igual)
    params = [
        bigquery.ScalarQueryParameter("peso_estetica", "FLOAT64", pesos_completos["estetica"]),
        bigquery.ScalarQueryParameter("peso_premium", "FLOAT64", pesos_completos["premium"]),
        bigquery.ScalarQueryParameter("peso_singular", "FLOAT64", pesos_completos["singular"]),
        bigquery.ScalarQueryParameter("peso_altura", "FLOAT64", pesos_completos["altura_libre_suelo"]),
        bigquery.ScalarQueryParameter("peso_batalla", "FLOAT64", pesos_completos["batalla"]),
        bigquery.ScalarQueryParameter("peso_indice_altura", "FLOAT64", pesos_completos["indice_altura_interior"]),
        bigquery.ScalarQueryParameter("peso_ancho_general_score", "FLOAT64", pesos_completos["ancho_general_score"]),
        bigquery.ScalarQueryParameter("penalizar_puertas", "BOOL", penalizar_puertas_val),
        bigquery.ScalarQueryParameter("peso_rating_durabilidad", "FLOAT64", pesos_completos["rating_durabilidad"]),
        bigquery.ScalarQueryParameter("peso_rating_fiabilidad", "FLOAT64", pesos_completos["rating_fiabilidad"]),
        bigquery.ScalarQueryParameter("peso_rating_seguridad", "FLOAT64", pesos_completos["rating_seguridad"]),
        bigquery.ScalarQueryParameter("peso_rating_impacto_ambiental", "FLOAT64", pesos_completos["rating_impacto_ambiental"]),
        bigquery.ScalarQueryParameter("peso_fav_bajo_coste_uso_directo", "FLOAT64", pesos_completos["fav_bajo_coste_uso_directo"]),
        bigquery.ScalarQueryParameter("peso_fav_bajo_coste_mantenimiento_directo", "FLOAT64", pesos_completos["fav_bajo_coste_mantenimiento_directo"]),
        bigquery.ScalarQueryParameter("peso_rating_tecnologia_conectividad", "FLOAT64", pesos_completos["rating_tecnologia_conectividad"]),
        bigquery.ScalarQueryParameter("peso_devaluacion", "FLOAT64", pesos_completos["devaluacion"]),
        bigquery.ScalarQueryParameter("peso_maletero_minimo_score", "FLOAT64", pesos_completos["maletero_minimo_score"]),
        bigquery.ScalarQueryParameter("peso_maletero_maximo_score", "FLOAT64", pesos_completos["maletero_maximo_score"]),
        bigquery.ScalarQueryParameter("peso_largo_vehiculo_score", "FLOAT64", pesos_completos["largo_vehiculo_score"]),
        bigquery.ScalarQueryParameter("peso_autonomia_vehiculo", "FLOAT64", pesos_completos["autonomia_uso_maxima"]),
        bigquery.ScalarQueryParameter("peso_fav_bajo_peso", "FLOAT64", pesos_completos["fav_bajo_peso"]),
        bigquery.ScalarQueryParameter("peso_fav_bajo_consumo", "FLOAT64", pesos_completos["fav_bajo_consumo"]),
        bigquery.ScalarQueryParameter("peso_par_motor_remolque_score", "FLOAT64", pesos_completos["par_motor_remolque_score"]),
        bigquery.ScalarQueryParameter("peso_cap_remolque_cf_score", "FLOAT64", pesos_completos["cap_remolque_cf_score"]),
        bigquery.ScalarQueryParameter("peso_cap_remolque_sf_score", "FLOAT64", pesos_completos["cap_remolque_sf_score"]),
        bigquery.ScalarQueryParameter("peso_fav_menor_superficie_planta", "FLOAT64", pesos_completos["fav_menor_superficie_planta"]),
        bigquery.ScalarQueryParameter("peso_fav_menor_diametro_giro", "FLOAT64", pesos_completos["fav_menor_diametro_giro"]),
        bigquery.ScalarQueryParameter("peso_fav_menor_largo_garage", "FLOAT64", pesos_completos["fav_menor_largo_garage"]),
        bigquery.ScalarQueryParameter("peso_fav_menor_ancho_garage", "FLOAT64", pesos_completos["fav_menor_ancho_garage"]),
        bigquery.ScalarQueryParameter("peso_fav_menor_alto_garage", "FLOAT64", pesos_completos["fav_menor_alto_garage"]),
        bigquery.ScalarQueryParameter("peso_deportividad_style_score", "FLOAT64", pesos_completos["deportividad_style_score"]),
        bigquery.ScalarQueryParameter("peso_fav_menor_rel_peso_potencia_score", "FLOAT64", pesos_completos["fav_menor_rel_peso_potencia_score"]),
        bigquery.ScalarQueryParameter("peso_potencia_maxima_style_score", "FLOAT64", pesos_completos["potencia_maxima_style_score"]),
        bigquery.ScalarQueryParameter("peso_par_motor_style_score", "FLOAT64", pesos_completos["par_motor_style_score"]),
        bigquery.ScalarQueryParameter("peso_autonomia_uso_principal", "FLOAT64", pesos_completos["peso_autonomia_uso_principal"]),
        bigquery.ScalarQueryParameter("peso_autonomia_uso_2nd_drive", "FLOAT64", pesos_completos["peso_autonomia_uso_2nd_drive"]),
        bigquery.ScalarQueryParameter("peso_menor_tiempo_carga_min", "FLOAT64", pesos_completos["peso_menor_tiempo_carga_min"]),
        bigquery.ScalarQueryParameter("peso_potencia_maxima_carga_AC", "FLOAT64", pesos_completos["peso_potencia_maxima_carga_AC"]),
        bigquery.ScalarQueryParameter("peso_potencia_maxima_carga_DC", "FLOAT64", pesos_completos["peso_potencia_maxima_carga_DC"]),
        bigquery.ScalarQueryParameter("peso_fav_menor_aceleracion_score", "FLOAT64", pesos_completos["fav_menor_aceleracion_score"]),
        bigquery.ScalarQueryParameter("flag_penalizar_low_cost_comodidad", "BOOL", flag_penalizar_low_cost_comod),
        bigquery.ScalarQueryParameter("flag_penalizar_deportividad_comodidad", "BOOL", flag_penalizar_deportividad_comod),
        bigquery.ScalarQueryParameter("flag_penalizar_antiguo_tec", "BOOL", flag_penalizar_antiguo_tec_val),
        bigquery.ScalarQueryParameter("flag_aplicar_logica_distintivo", "BOOL", flag_aplicar_logica_distintivo_val),
        bigquery.ScalarQueryParameter("flag_es_municipio_zbe", "BOOL", flag_es_municipio_zbe_val),
        bigquery.ScalarQueryParameter("flag_pen_bev_reev_avent_ocas", "BOOL", flag_pen_bev_reev_ocas_val),
        bigquery.ScalarQueryParameter("flag_pen_phev_avent_ocas", "BOOL", flag_pen_phev_ocas_val),
        bigquery.ScalarQueryParameter("flag_pen_electrif_avent_extr", "BOOL", flag_pen_electrif_extr_val),
        bigquery.ScalarQueryParameter("flag_fav_car_montana", "BOOL", flag_fav_car_montana_val),
        bigquery.ScalarQueryParameter("flag_fav_car_comercial", "BOOL", flag_fav_car_comercial_val),
        bigquery.ScalarQueryParameter("flag_fav_car_pasajeros_pro", "BOOL", flag_fav_car_pasajeros_pro_val),
        bigquery.ScalarQueryParameter("flag_desfav_car_no_aventura", "BOOL", flag_desfav_car_no_aventura_val), 
        bigquery.ScalarQueryParameter("flag_fav_suv_aventura_ocasional", "BOOL", flag_fav_suv_aventura_ocasional),
        bigquery.ScalarQueryParameter("flag_fav_pickup_todoterreno_aventura_extrema", "BOOL", flag_fav_pickup_todoterreno_aventura_extrema),
        bigquery.ScalarQueryParameter("flag_aplicar_logica_objetos_especiales", "BOOL", flag_aplicar_logica_objetos_especiales),
        bigquery.ScalarQueryParameter("flag_fav_carroceria_confort", "BOOL", flag_fav_carroceria_confort),
        bigquery.ScalarQueryParameter("flag_logica_uso_ocasional", "BOOL", flag_logica_uso_ocasional_val),
        bigquery.ScalarQueryParameter("flag_favorecer_bev_uso_definido", "BOOL", flag_favorecer_bev_val),
        bigquery.ScalarQueryParameter("flag_penalizar_phev_uso_intensivo", "BOOL", flag_penalizar_phev_val),
        bigquery.ScalarQueryParameter("flag_favorecer_electrificados_por_punto_carga", "BOOL", flag_favorecer_electrificados_val),
        bigquery.ScalarQueryParameter("penalizar_awd_ninguna_aventura", "BOOL", penalizar_awd_ninguna_val),
        bigquery.ScalarQueryParameter("favorecer_awd_aventura_ocasional", "BOOL", favorecer_awd_ocasional_val),
        bigquery.ScalarQueryParameter("favorecer_awd_aventura_extrema", "BOOL", favorecer_awd_extrema_val),
        bigquery.ScalarQueryParameter("flag_bonus_awd_nieve", "BOOL", flag_bonus_nieve_val),
        bigquery.ScalarQueryParameter("flag_bonus_awd_montana", "BOOL", flag_bonus_montana_val),
        bigquery.ScalarQueryParameter("flag_logica_reductoras_aventura", "STRING", flag_reductoras_aventura_val),
        bigquery.ScalarQueryParameter("flag_bonus_awd_clima_adverso", "BOOL", flag_bonus_clima_val),
        bigquery.ScalarQueryParameter("flag_logica_diesel_ciudad", "STRING", flag_diesel_ciudad_val),
        bigquery.ScalarQueryParameter("flag_bonus_seguridad_critico", "BOOL", flag_bonus_seguridad_critico_val),
        bigquery.ScalarQueryParameter("flag_bonus_seguridad_fuerte", "BOOL", flag_bonus_seguridad_fuerte_val),
        bigquery.ScalarQueryParameter("flag_bonus_fiab_dur_critico", "BOOL", flag_bonus_fiab_dur_critico_val),
        bigquery.ScalarQueryParameter("flag_bonus_fiab_dur_fuerte", "BOOL", flag_bonus_fiab_dur_fuerte_val),
        bigquery.ScalarQueryParameter("flag_bonus_costes_critico", "BOOL", flag_bonus_costes_critico),
        bigquery.ScalarQueryParameter("km_anuales_estimados", "INT64", km_anuales_estimados_val),
        bigquery.ScalarQueryParameter("flag_penalizar_tamano_no_compacto", "BOOL", flag_penalizar_tamano_val),
        bigquery.ScalarQueryParameter("flag_bonus_singularidad_lifestyle", "BOOL", flag_bonus_singularidad_lifestyle),
        bigquery.ScalarQueryParameter("flag_deportividad_lifestyle", "BOOL", flag_deportividad_lifestyle),
        bigquery.ScalarQueryParameter("flag_ajuste_maletero_personal", "BOOL", flag_ajuste_maletero_personal),
        bigquery.ScalarQueryParameter("flag_coche_ciudad_perfil", "BOOL", flag_coche_ciudad_perfil),
        bigquery.ScalarQueryParameter("flag_coche_ciudad_2_perfil", "BOOL", flag_coche_ciudad_2_perfil),
        bigquery.ScalarQueryParameter("flag_es_conductor_urbano", "BOOL", flag_es_conductor_urbano),
        bigquery.ScalarQueryParameter("k", "INT64", k)
    ]
    
    sql_where_clauses = []
    transmision_val = filtros.get("transmision_preferida")
    if isinstance(transmision_val, str) and transmision_val != "ambos":
        param_name_trans = "param_transmision_auto"
        if transmision_val.lower() == 'automático': 
            sql_where_clauses.append(f"sd.cambio_automatico = @{param_name_trans}")
            params.append(bigquery.ScalarQueryParameter(param_name_trans, "BOOL", True))
        elif transmision_val.lower() == 'manual': 
            sql_where_clauses.append(f"sd.cambio_automatico = @{param_name_trans}")
            params.append(bigquery.ScalarQueryParameter(param_name_trans, "BOOL", False))
    
    plazas_min_val = filtros.get("plazas_min")
    if plazas_min_val is not None and isinstance(plazas_min_val, int) and plazas_min_val > 0:
        sql_where_clauses.append(f"sd.plazas >= @plazas_min") 
        params.append(bigquery.ScalarQueryParameter("plazas_min", "INT64", plazas_min_val))

    tipos_mecanica_list = filtros.get("tipo_mecanica")
    if isinstance(tipos_mecanica_list, list) and tipos_mecanica_list:
        tipos_mecanica_str_list = [m.value if hasattr(m, 'value') else str(m) for m in tipos_mecanica_list]
        sql_where_clauses.append(f"sd.tipo_mecanica IN UNNEST(@tipos_mecanica)")
        params.append(bigquery.ArrayQueryParameter("tipos_mecanica", "STRING", tipos_mecanica_str_list))

    # --- LÓGICA DE FILTRADO ECONÓMICO (CORREGIDA Y REFACTORIZADA) ---

# --- LÓGICA DE FILTRADO ECONÓMICO (CORREGIDA Y REFACTORIZADA) ---

    modo_adq_rec = filtros.get("modo_adquisicion_recomendado")
    precio_maximo = None
    cuota_maxima = None

    # 1. Determinamos el presupuesto MÁXIMO a usar con una lógica explícita
    if modo_adq_rec == "Contado":
        precio_maximo = filtros.get("precio_max_contado_recomendado")
    elif modo_adq_rec == "Financiado":
        cuota_maxima = filtros.get("cuota_max_calculada")
    else:
        # MODO 2 (DIRECTO) - El usuario proporciona su propio presupuesto
        precio_maximo = filtros.get("pago_contado")
        if precio_maximo is None:
            cuota_maxima = filtros.get("cuota_max")

    # 2. Construimos las cláusulas SQL basándonos en el presupuesto que se haya determinado
    if precio_maximo is not None:
        precio_minimo = precio_maximo * FACTOR_PRECIO_MINIMO
        logging.info(f"Filtro Económico: Rango de precio Contado -> {precio_minimo:,.0f}€ a {precio_maximo:,.0f}€")
        
        # Filtro de Límite Superior
        sql_where_clauses.append(f"COALESCE(sd.precio_compra_contado, 999999999) <= @precio_maximo")
        params.append(bigquery.ScalarQueryParameter("precio_maximo", "FLOAT64", float(precio_maximo)))
        
        # ✅ NUEVO FILTRO DE LÍMITE INFERIOR
        sql_where_clauses.append(f"sd.precio_compra_contado >= @precio_minimo")
        params.append(bigquery.ScalarQueryParameter("precio_minimo", "FLOAT64", float(precio_minimo)))
    
    elif cuota_maxima is not None:
        cuota_minima = cuota_maxima * FACTOR_PRECIO_MINIMO
        logging.info(f"Filtro Económico: Rango de Cuota -> {cuota_minima:,.0f}€/mes a {cuota_maxima:,.0f}€/mes")

        # Filtro de Límite Superior
        sql_where_clauses.append(f"(COALESCE(sd.precio_compra_contado, 0) * {FACTOR_CONVERSION_PRECIO_CUOTA}) <= @cuota_maxima")
        params.append(bigquery.ScalarQueryParameter("cuota_maxima", "FLOAT64", float(cuota_maxima)))
        
        # ✅ NUEVO FILTRO DE LÍMITE INFERIOR
        sql_where_clauses.append(f"(COALESCE(sd.precio_compra_contado, 0) * {FACTOR_CONVERSION_PRECIO_CUOTA}) >= @cuota_minima")
        params.append(bigquery.ScalarQueryParameter("cuota_minima", "FLOAT64", float(cuota_minima)))
        
    # PASO 3: CONVERTIR CLÁUSULAS A STRING
    sql_where_clauses_str = ""
    if sql_where_clauses:
        sql_where_clauses_str = " AND " + " AND ".join(sql_where_clauses)

    # PASO 4: DEFINIR LA PLANTILLA SQL
    sql = f"""
    WITH ScaledData AS (
        SELECT
            *,
            COALESCE(SAFE_DIVIDE(COALESCE(estetica, {min_est}) - {min_est}, NULLIF({max_est} - {min_est}, 0)), 0) AS estetica_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(premium, {min_prem}) - {min_prem}, NULLIF({max_prem} - {min_prem}, 0)), 0) AS premium_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(singular, {min_sing}) - {min_sing}, NULLIF({max_sing} - {min_sing}, 0)), 0) AS singular_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(altura_libre_suelo, {min_alt_ls}) - {min_alt_ls}, NULLIF({max_alt_ls} - {min_alt_ls}, 0)), 0) AS altura_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(batalla, {min_bat}) - {min_bat}, NULLIF({max_bat} - {min_bat}, 0)), 0) AS batalla_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(indice_altura_interior, {min_ind_alt}) - {min_ind_alt}, NULLIF({max_ind_alt} - {min_ind_alt}, 0)), 0) AS indice_altura_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(ancho, {min_anc}) - {min_anc}, NULLIF({max_anc} - {min_anc}, 0)), 0) AS ancho_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(fiabilidad, {min_fiab}) - {min_fiab}, NULLIF({max_fiab} - {min_fiab}, 0)), 0) AS fiabilidad_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(durabilidad, {min_durab}) - {min_durab}, NULLIF({max_durab} - {min_durab}, 0)), 0) AS durabilidad_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(seguridad, {min_seg}) - {min_seg}, NULLIF({max_seg} - {min_seg}, 0)), 0) AS seguridad_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(comodidad, {min_comod}) - {min_comod}, NULLIF({max_comod} - {min_comod}, 0)), 0) AS comodidad_scaled,
            COALESCE(SAFE_DIVIDE({max_coste_uso} - COALESCE(costes_de_uso, {max_coste_uso}), NULLIF({max_coste_uso} - {min_coste_uso}, 0)), 0) AS costes_de_uso_bajo_scaled,
            COALESCE(SAFE_DIVIDE({max_coste_mante} - COALESCE(costes_mantenimiento, {max_coste_mante}), NULLIF({max_coste_mante} - {min_coste_mante}, 0)), 0) AS costes_mantenimiento_bajo_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(tecnologia, {min_tec}) - {min_tec}, NULLIF({max_tec} - {min_tec}, 0)), 0) AS tecnologia_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(acceso_low_cost, {min_acc_lc}) - {min_acc_lc}, NULLIF({max_acc_lc} - {min_acc_lc}, 0)), 0) AS acceso_low_cost_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(deportividad, {min_depor_bq}) - {min_depor_bq}, NULLIF({max_depor_bq} - {min_depor_bq}, 0)), 0) AS deportividad_bq_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(devaluacion, {min_deval}) - {min_deval}, NULLIF({max_deval} - {min_deval}, 0)), 0) AS devaluacion_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(maletero_minimo, {min_mal_min}) - {min_mal_min}, NULLIF({max_mal_min} - {min_mal_min}, 0)), 0) AS maletero_minimo_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(maletero_maximo, {min_mal_max}) - {min_mal_max}, NULLIF({max_mal_max} - {min_mal_max}, 0)), 0) AS maletero_maximo_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(largo, {min_largo}) - {min_largo}, NULLIF({max_largo} - {min_largo}, 0)), 0) AS largo_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(autonomia_uso_maxima, {min_auton}) - {min_auton}, NULLIF({max_auton} - {min_auton}, 0)), 0) AS autonomia_uso_maxima_scaled,
            COALESCE(SAFE_DIVIDE({max_peso_kg} - COALESCE(peso, {max_peso_kg}), NULLIF({max_peso_kg} - {min_peso_kg}, 0)), 0) AS bajo_peso_scaled,
            COALESCE(SAFE_DIVIDE({max_consumo} - COALESCE(indice_consumo_energia, {max_consumo}), NULLIF({max_consumo} - {min_consumo}, 0)), 0) AS bajo_consumo_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(par, {min_par}) - {min_par}, NULLIF({max_par} - {min_par}, 0)), 0) AS par_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(capacidad_remolque_con_freno, {min_cap_cf}) - {min_cap_cf}, NULLIF({max_cap_cf} - {min_cap_cf}, 0)), 0) AS cap_remolque_cf_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(capacidad_remolque_sin_freno, {min_cap_sf}) - {min_cap_sf}, NULLIF({max_cap_sf} - {min_cap_sf}, 0)), 0) AS cap_remolque_sf_scaled,
            COALESCE(SAFE_DIVIDE({max_sup_planta} - COALESCE(superficie_planta, {max_sup_planta}), NULLIF({max_sup_planta} - {min_sup_planta}, 0)), 0) AS menor_superficie_planta_scaled,
            COALESCE(SAFE_DIVIDE({max_diam_giro} - COALESCE(diametro_giro, {max_diam_giro}), NULLIF({max_diam_giro} - {min_diam_giro}, 0)), 0) AS menor_diametro_giro_scaled,
            COALESCE(SAFE_DIVIDE({max_largo} - COALESCE(largo, {max_largo}), NULLIF({max_largo} - {min_largo}, 0)), 0) AS menor_largo_garage_scaled,
            COALESCE(SAFE_DIVIDE({max_anc} - COALESCE(ancho, {max_anc}), NULLIF({max_anc} - {min_anc}, 0)), 0) AS menor_ancho_garage_scaled,
            COALESCE(SAFE_DIVIDE({max_alto_veh} - COALESCE(alto, {max_alto_veh}), NULLIF({max_alto_veh} - {min_alto_veh}, 0)), 0) AS menor_alto_garage_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(deportividad, {min_depor_bq}) - {min_depor_bq}, NULLIF({max_depor_bq} - {min_depor_bq}, 0)), 0) AS deportividad_style_scaled,
            COALESCE(SAFE_DIVIDE({max_rel_pp} - COALESCE(relacion_peso_potencia, {max_rel_pp}), NULLIF({max_rel_pp} - {min_rel_pp}, 0)), 0) AS menor_rel_peso_potencia_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(potencia_maxima, {min_pot_max}) - {min_pot_max}, NULLIF({max_pot_max} - {min_pot_max}, 0)), 0) AS potencia_maxima_style_scaled,
            COALESCE(SAFE_DIVIDE({max_acel} - COALESCE(aceleracion_0_100, {max_acel}), NULLIF({max_acel} - {min_acel}, 0)), 0) AS menor_aceleracion_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(autonomia_uso_principal, {min_auto_p}) - {min_auto_p}, NULLIF({max_auto_p} - {min_auto_p}, 0)), 0) AS autonomia_uso_principal_scaled,
            COALESCE(SAFE_DIVIDE(COALESCE(autonomia_uso_2nd_drive, {min_auto_2}) - {min_auto_2}, NULLIF({max_auto_2} - {min_auto_2}, 0)), 0) AS autonomia_uso_2nd_drive_scaled, 
            (CASE WHEN COALESCE(tiempo_carga_min, 0) = 0 THEN 0.0 ELSE COALESCE(SAFE_DIVIDE({max_t_carga} - tiempo_carga_min, NULLIF({max_t_carga} - {min_t_carga}, 0)), 0) END) AS menor_tiempo_carga_min_scaled,
            (CASE WHEN COALESCE(potencia_maxima_carga_AC, 0) = 0 THEN 0.0 ELSE COALESCE(SAFE_DIVIDE(potencia_maxima_carga_AC - {min_pot_ac}, NULLIF({max_pot_ac} - {min_pot_ac}, 0)), 0) END) AS potencia_maxima_carga_AC_scaled,
            (CASE WHEN COALESCE(potencia_maxima_carga_DC, 0) = 0 THEN 0.0 ELSE COALESCE(SAFE_DIVIDE(potencia_maxima_carga_DC - {min_pot_dc}, NULLIF({max_pot_dc} - {min_pot_dc}, 0)), 0) END) AS potencia_maxima_carga_DC_scaled,
            
        FROM
            `thecarmentor-mvp2.web_cars.coches_prueba_2`
            --`thecarmentor-mvp2.web_cars.match_coches_pruebas`
    ),      
    -- ESTE ES EL CTE CLAVE CON TODOS LOS DESGLOSES
    DebugScores AS (
        SELECT
            sd.*,
            
            -- Desglose de puntuacion_base
            (sd.estetica_scaled * @peso_estetica * {FACTOR_ESCALA_BASE}) AS dbg_score_estetica,
            (sd.premium_scaled * @peso_premium * {FACTOR_ESCALA_BASE}) AS dbg_score_premium,
            (sd.singular_scaled * @peso_singular * {FACTOR_ESCALA_BASE}) AS dbg_score_singular,
            (sd.altura_scaled * @peso_altura * {FACTOR_ESCALA_BASE}) AS dbg_score_altura_libre,
            (sd.batalla_scaled * @peso_batalla * {FACTOR_ESCALA_BASE}) AS dbg_score_batalla,
            (sd.indice_altura_scaled * @peso_indice_altura * {FACTOR_ESCALA_BASE}) AS dbg_score_altura_interior,
            (sd.ancho_scaled * @peso_ancho_general_score * {FACTOR_ESCALA_BASE}) AS dbg_score_ancho,
            (sd.devaluacion_scaled * @peso_devaluacion * {FACTOR_ESCALA_BASE}) AS dbg_score_devaluacion,
            (sd.maletero_minimo_scaled * @peso_maletero_minimo_score * {FACTOR_ESCALA_BASE}) AS dbg_score_maletero_min,
            (sd.maletero_maximo_scaled * @peso_maletero_maximo_score * {FACTOR_ESCALA_BASE}) AS dbg_score_maletero_max,
            (sd.largo_scaled * @peso_largo_vehiculo_score * {FACTOR_ESCALA_BASE}) AS dbg_score_largo,
            (sd.autonomia_uso_maxima_scaled * @peso_autonomia_vehiculo * {FACTOR_ESCALA_BASE}) AS dbg_score_autonomia_max,
            (sd.bajo_peso_scaled * @peso_fav_bajo_peso * {FACTOR_ESCALA_BASE}) AS dbg_score_bajo_peso,
            (sd.par_scaled * @peso_par_motor_remolque_score * {FACTOR_ESCALA_BASE}) AS dbg_score_par_remolque,
            (sd.cap_remolque_cf_scaled * @peso_cap_remolque_cf_score * {FACTOR_ESCALA_BASE}) AS dbg_score_remolque_cf,
            (sd.cap_remolque_sf_scaled * @peso_cap_remolque_sf_score * {FACTOR_ESCALA_BASE}) AS dbg_score_remolque_sf,
            (sd.menor_superficie_planta_scaled * @peso_fav_menor_superficie_planta * {FACTOR_ESCALA_BASE}) AS dbg_score_menor_superficie,
            (sd.menor_diametro_giro_scaled * @peso_fav_menor_diametro_giro * {FACTOR_ESCALA_BASE}) AS dbg_score_menor_giro,
            (sd.menor_largo_garage_scaled * @peso_fav_menor_largo_garage * {FACTOR_ESCALA_BASE}) AS dbg_score_menor_largo,
            (sd.menor_ancho_garage_scaled * @peso_fav_menor_ancho_garage * {FACTOR_ESCALA_BASE}) AS dbg_score_menor_ancho,
            (sd.menor_alto_garage_scaled * @peso_fav_menor_alto_garage * {FACTOR_ESCALA_BASE}) AS dbg_score_menor_alto,
            (sd.deportividad_style_scaled * @peso_deportividad_style_score * {FACTOR_ESCALA_BASE}) AS dbg_score_deportividad,
            (sd.menor_rel_peso_potencia_scaled * @peso_fav_menor_rel_peso_potencia_score * {FACTOR_ESCALA_BASE}) AS dbg_score_menor_rel_peso_pot,
            (sd.potencia_maxima_style_scaled * @peso_potencia_maxima_style_score * {FACTOR_ESCALA_BASE}) AS dbg_score_potencia,
            (sd.par_scaled * @peso_par_motor_style_score * {FACTOR_ESCALA_BASE}) AS dbg_score_par_deportivo,
            --(sd.autonomia_uso_principal_scaled * @peso_autonomia_uso_principal * {FACTOR_ESCALA_BASE}) AS dbg_score_autonomia_principal,
            (sd.autonomia_uso_2nd_drive_scaled * @peso_autonomia_uso_2nd_drive * {FACTOR_ESCALA_BASE}) AS dbg_score_autonomia_2nd,
            (sd.menor_tiempo_carga_min_scaled * @peso_menor_tiempo_carga_min * {FACTOR_ESCALA_BASE}) AS dbg_score_menor_t_carga,
            (sd.potencia_maxima_carga_AC_scaled * @peso_potencia_maxima_carga_AC * {FACTOR_ESCALA_BASE}) AS dbg_score_pot_carga_ac,
            (sd.potencia_maxima_carga_DC_scaled * @peso_potencia_maxima_carga_DC * {FACTOR_ESCALA_BASE}) AS dbg_score_pot_carga_dc,
            (sd.menor_aceleracion_scaled * @peso_fav_menor_aceleracion_score * {FACTOR_ESCALA_BASE}) AS dbg_score_menor_aceleracion, 
            -- Desglose de ajustes_experto --
            ( (sd.seguridad_scaled * @peso_rating_seguridad) * (CASE WHEN @flag_bonus_seguridad_critico = TRUE THEN {FACTOR_BONUS_RATING_CRITICO} WHEN @flag_bonus_seguridad_fuerte = TRUE THEN {FACTOR_BONUS_RATING_FUERTE} ELSE 1.0 END) * {FACTOR_ESCALA_BASE} ) as dbg_bonus_seguridad,
                -- Bonus Acumulativo para Fiabilidad
            ( (sd.fiabilidad_scaled * @peso_rating_fiabilidad) * ((CASE WHEN @flag_aplicar_logica_distintivo = TRUE THEN {FACTOR_BONUS_FIABILIDAD_POR_IMPACTO} ELSE 1.0 END) * (CASE WHEN @flag_bonus_fiab_dur_critico = TRUE THEN {FACTOR_BONUS_FIAB_DUR_CRITICO} WHEN @flag_bonus_fiab_dur_fuerte = TRUE THEN {FACTOR_BONUS_FIAB_DUR_FUERTE} ELSE 1.0 END)) * {FACTOR_ESCALA_BASE} ) as dbg_bonus_fiabilidad,  
                -- Bonus Acumulativo para Durabilidad
            ( (sd.durabilidad_scaled * @peso_rating_durabilidad) * ((CASE WHEN @flag_aplicar_logica_distintivo = TRUE THEN {FACTOR_BONUS_DURABILIDAD_POR_IMPACTO} ELSE 1.0 END) * (CASE WHEN @flag_bonus_fiab_dur_critico = TRUE THEN {FACTOR_BONUS_FIAB_DUR_CRITICO} WHEN @flag_bonus_fiab_dur_fuerte = TRUE THEN {FACTOR_BONUS_FIAB_DUR_FUERTE} ELSE 1.0 END)) * {FACTOR_ESCALA_BASE}) as dbg_bonus_durabilidad,
            -- ✅ NUEVA LÓGICA: Bonus proporcional para características de COSTE
            ( (sd.bajo_consumo_scaled * @peso_fav_bajo_consumo) * (CASE WHEN @flag_bonus_costes_critico = TRUE THEN {FACTOR_BONUS_COSTES_CRITICO} ELSE 1.0 END) * {FACTOR_ESCALA_BASE} )  as dbg_bonus_bajo_consumo,
            ( (sd.costes_de_uso_bajo_scaled * @peso_fav_bajo_coste_uso_directo) * (CASE WHEN @flag_bonus_costes_critico = TRUE THEN {FACTOR_BONUS_COSTES_CRITICO} ELSE 1.0 END) * {FACTOR_ESCALA_BASE} )  as dbg_bonus_coste_uso,
            ( (sd.costes_mantenimiento_bajo_scaled * @peso_fav_bajo_coste_mantenimiento_directo) * (CASE WHEN @flag_bonus_costes_critico = TRUE THEN {FACTOR_BONUS_COSTES_CRITICO} ELSE 1.0 END) * {FACTOR_ESCALA_BASE} )  as dbg_bonus_coste_mantenimiento,
            (CASE WHEN COALESCE(sd.km_ocasion, 0) >= 250000 THEN {PENALTY_OCASION_KILOMETRAJE_EXTREMO} ELSE 0.0 END) as dbg_pen_km_extremo,
            (CASE WHEN @penalizar_puertas = TRUE AND puertas <= 3 THEN {PENALTY_PUERTAS_BAJAS} ELSE 0.0 END) as dbg_pen_puertas,
            (CASE WHEN @flag_penalizar_low_cost_comodidad = TRUE THEN (sd.acceso_low_cost_scaled * {PENALTY_LOW_COST_POR_COMODIDAD}) ELSE 0.0 END) as dbg_pen_low_cost_comodidad,
            (CASE WHEN @flag_penalizar_deportividad_comodidad = TRUE THEN (sd.deportividad_bq_scaled * {PENALTY_DEPORTIVIDAD_POR_COMODIDAD}) ELSE 0.0 END) as dbg_pen_deportividad_comodidad,
            (CASE WHEN @flag_penalizar_antiguo_tec = TRUE THEN CASE
                WHEN sd.anos_vehiculo > 15 THEN {PENALTY_ANTIGUEDAD_MAS_15_ANOS}
                WHEN sd.anos_vehiculo > 10 THEN {PENALTY_ANTIGUEDAD_10_A_15_ANOS} 
                WHEN sd.anos_vehiculo > 7  THEN {PENALTY_ANTIGUEDAD_7_A_10_ANOS} 
                WHEN sd.anos_vehiculo > 5  THEN {PENALTY_ANTIGUEDAD_5_A_7_ANOS} 
            ELSE 0.0 END ELSE 0.0 END) as dbg_pen_antiguedad,
            -- ✅ NUEVA LÓGICA: Penalización general por antigüedad
            (CASE
                WHEN sd.ano_unidad < 1990 THEN {PENALTY_ANO_PRE_1990}
                WHEN sd.ano_unidad BETWEEN 1991 AND 1995 THEN {PENALTY_ANO_1991_1995}
                WHEN sd.ano_unidad BETWEEN 1996 AND 2000 THEN {PENALTY_ANO_1996_2000}
                WHEN sd.ano_unidad BETWEEN 2001 AND 2006 AND sd.tipo_mecanica = 'DIESEL' THEN {PENALTY_DIESEL_2001_2006}
                ELSE 0.0
            END) as dbg_pen_antiguedad_general,
            (CASE WHEN @flag_aplicar_logica_distintivo = TRUE THEN CASE WHEN UPPER(sd.distintivo_ambiental) IN ('CERO', '0', 'ECO', 'C') THEN {BONUS_DISTINTIVO_ECO_CERO_C} WHEN UPPER(sd.distintivo_ambiental) IN ('B', 'NA') THEN {PENALTY_DISTINTIVO_NA_B} ELSE 0.0 END ELSE 0.0 END) as dbg_ajuste_distintivo,
            (CASE WHEN @flag_aplicar_logica_distintivo = TRUE AND COALESCE(sd.ocasion, FALSE) = TRUE THEN {BONUS_OCASION_POR_IMPACTO_AMBIENTAL} ELSE 0.0 END) as dbg_bonus_ocasion_ambiental,
            (CASE WHEN @flag_es_municipio_zbe = TRUE AND UPPER(sd.distintivo_ambiental) IN ('CERO', '0', 'ECO') THEN {BONUS_ZBE_DISTINTIVO_FAVORABLE_ECO_CERO} WHEN @flag_es_municipio_zbe = TRUE AND UPPER(sd.distintivo_ambiental) IN ('C') THEN {BONUS_ZBE_DISTINTIVO_FAVORABLE_C} WHEN @flag_es_municipio_zbe = TRUE AND UPPER(sd.distintivo_ambiental) IN ('NA') THEN {PENALTY_ZBE_DISTINTIVO_DESFAVORABLE_NA} WHEN @flag_es_municipio_zbe = TRUE AND UPPER(sd.distintivo_ambiental) IN ('B') THEN {PENALTY_ZBE_DISTINTIVO_DESFAVORABLE_B} ELSE 0.0 END) as dbg_ajuste_zbe,
            (CASE WHEN @flag_pen_bev_reev_avent_ocas = TRUE AND sd.tipo_mecanica IN ('BEV', 'REEV') THEN {PENALTY_BEV_REEV_AVENTURA_OCASIONAL} ELSE 0.0 END) as dbg_pen_bev_reev_avent_ocas,
            (CASE WHEN @flag_pen_phev_avent_ocas = TRUE AND sd.tipo_mecanica IN ('PHEVD', 'PHEVG') THEN {PENALTY_PHEV_AVENTURA_OCASIONAL} ELSE 0.0 END) as dbg_pen_phev_avent_ocas,
            (CASE WHEN @flag_pen_electrif_avent_extr = TRUE AND sd.tipo_mecanica IN ('BEV', 'REEV', 'PHEVD', 'PHEVG') THEN {PENALTY_ELECTRIFICADOS_AVENTURA_EXTREMA} ELSE 0.0 END) as dbg_pen_electrif_avent_extr,
            (CASE WHEN @flag_fav_car_montana = TRUE AND sd.tipo_carroceria IN ('SUV', 'TODOTERRENO') THEN {BONUS_CARROCERIA_MONTANA} ELSE 0.0 END) as dbg_bonus_car_montana,
            (CASE WHEN @flag_fav_car_comercial = TRUE AND sd.tipo_carroceria IN ('COMERCIAL') THEN {BONUS_CARROCERIA_COMERCIAL} ELSE 0.0 END) as dbg_bonus_car_comercial,
            (CASE WHEN @flag_fav_car_pasajeros_pro = TRUE AND sd.tipo_carroceria IN ('3VOL', 'MONOVOLUMEN') THEN {BONUS_CARROCERIA_PASAJEROS_PRO} ELSE 0.0 END) as dbg_bonus_car_pasajeros,
            (CASE WHEN @flag_desfav_car_no_aventura = TRUE AND sd.tipo_carroceria IN ('PICKUP', 'TODOTERRENO') THEN {PENALTY_CARROCERIA_NO_AVENTURA} ELSE 0.0 END) as dbg_pen_car_no_aventura,
            (CASE WHEN @flag_fav_suv_aventura_ocasional = TRUE AND sd.tipo_carroceria IN ('SUV') THEN {BONUS_SUV_AVENTURA_OCASIONAL} ELSE 0.0 END) as dbg_bonus_suv_avent_ocas,
            (CASE WHEN @flag_fav_pickup_todoterreno_aventura_extrema = TRUE AND sd.tipo_carroceria IN ('TODOTERRENO') THEN {BONUS_TODOTERRENO_AVENTURA_EXTREMA} ELSE 0.0 END) as dbg_bonus_tt_avent_extr,
            (CASE WHEN @flag_fav_pickup_todoterreno_aventura_extrema = TRUE AND sd.tipo_carroceria IN ('PICKUP') THEN {BONUS_PICKUP_AVENTURA_EXTREMA} ELSE 0.0 END) as dbg_bonus_pickup_avent_extr,
            (CASE WHEN @flag_aplicar_logica_objetos_especiales = TRUE THEN CASE WHEN sd.tipo_carroceria IN ('MONOVOLUMEN', 'FURGONETA', 'FAMILIAR', 'SUV') THEN {BONUS_CARROCERIA_OBJETOS_ESPECIALES} WHEN sd.tipo_carroceria IN ('3VOL', 'COUPE', 'DESCAPOTABLE') THEN {PENALTY_CARROCERIA_OBJETOS_ESPECIALES} ELSE 0.0 END ELSE 0.0 END) as dbg_ajuste_objetos_especiales,
            (CASE WHEN @flag_fav_carroceria_confort = TRUE AND sd.tipo_carroceria IN ('3VOL', '2VOL', 'SUV', 'FAMILIAR', 'MONOVOLUMEN') THEN {BONUS_CARROCERIA_CONFORT} ELSE 0.0 END) as dbg_bonus_car_confort,
            (CASE WHEN @flag_logica_uso_ocasional = TRUE AND COALESCE(sd.ocasion, FALSE) = TRUE THEN {BONUS_OCASION_POR_USO_OCASIONAL} ELSE 0.0 END) as dbg_bonus_ocasion_uso_ocas,
            (CASE WHEN @flag_logica_uso_ocasional = TRUE AND sd.tipo_mecanica IN ('PHEVD', 'PHEVG', 'BEV', 'REEV') THEN {PENALTY_ELECTRIFICADOS_POR_USO_OCASIONAL} ELSE 0.0 END) as dbg_pen_electrif_uso_ocas,
            (CASE WHEN @flag_favorecer_bev_uso_definido = TRUE AND sd.tipo_mecanica IN ('BEV', 'REEV') THEN {BONUS_BEV_REEV_USO_DEFINIDO} ELSE 0.0 END) as dbg_bonus_bev_uso_definido,
            (CASE WHEN @flag_penalizar_phev_uso_intensivo = TRUE AND sd.tipo_mecanica IN ('PHEVD', 'PHEVG') THEN {PENALTY_PHEV_USO_INTENSIVO_LARGO} ELSE 0.0 END) as dbg_pen_phev_uso_intensivo,
            (CASE WHEN @flag_favorecer_electrificados_por_punto_carga = TRUE AND sd.tipo_mecanica IN ('BEV', 'PHEVD', 'PHEVG', 'REEV') THEN {BONUS_PUNTO_CARGA_PROPIO} ELSE 0.0 END) as dbg_bonus_punto_carga,
            (CASE WHEN @flag_bonus_awd_clima_adverso = TRUE AND sd.traccion = 'ALL' THEN {BONUS_AWD_NINGUNA_AVENTURA_CLIMA_ADVERSO} WHEN @penalizar_awd_ninguna_aventura = TRUE AND sd.traccion = 'ALL' THEN {PENALTY_AWD_NINGUNA_AVENTURA} WHEN @favorecer_awd_aventura_ocasional = TRUE AND sd.traccion = 'ALL' THEN {BONUS_AWD_AVENTURA_OCASIONAL} WHEN @favorecer_awd_aventura_extrema = TRUE AND sd.traccion = 'ALL' THEN {BONUS_AWD_AVENTURA_EXTREMA} ELSE 0.0 END) as dbg_ajuste_awd_aventura,
            (CASE WHEN @flag_bonus_awd_nieve = TRUE AND sd.traccion = 'ALL' THEN {BONUS_AWD_ZONA_NIEVE} ELSE 0.0 END) as dbg_bonus_awd_nieve,
            (CASE WHEN @flag_bonus_awd_montana = TRUE AND sd.traccion = 'ALL' THEN {BONUS_AWD_ZONA_MONTA} ELSE 0.0 END) as dbg_bonus_awd_montana,
            (CASE WHEN @flag_logica_reductoras_aventura = 'FAVORECER_OCASIONAL' AND COALESCE(sd.reductoras, FALSE) = TRUE THEN {BONUS_REDUCTORAS_AVENTURA_OCASIONAL} WHEN @flag_logica_reductoras_aventura = 'FAVORECER_EXTREMA' AND COALESCE(sd.reductoras, FALSE) = TRUE THEN {BONUS_REDUCTORAS_AVENTURA_EXTREMA} ELSE 0.0 END) as dbg_bonus_reductoras,
            (CASE WHEN @flag_logica_diesel_ciudad = 'PENALIZAR' AND sd.tipo_mecanica IN ('DIESEL', 'HEVD', 'MHEVD') THEN {PENALTY_DIESEL_CIUDAD} WHEN @flag_logica_diesel_ciudad = 'BONIFICAR' AND sd.tipo_mecanica IN ('DIESEL', 'HEVD', 'MHEVD') THEN {BONUS_DIESEL_CIUDAD_OCASIONAL} ELSE 0.0 END) as dbg_ajuste_diesel_ciudad,
            -- ✅ LÓGICA MEJORADA: Penalización por tamaño no compacto, AHORA CONTEXTUAL
            (CASE 
                -- La regla solo se activa si el flag principal está activo
                WHEN @flag_penalizar_tamano_no_compacto = TRUE THEN
                    -- Ahora, aplicamos la penalización correcta según el contexto
                    (CASE
                        -- Si es conductor urbano, usa el umbral y la penalización de ciudad
                        WHEN @flag_es_conductor_urbano = TRUE AND sd.largo >= {UMBRAL_LARGO_CIUDAD_MM}
                        THEN {PENALTY_TAMANO_CIUDAD}
                        
                        -- Si NO es conductor urbano, usa el umbral y la penalización de carretera
                        WHEN @flag_es_conductor_urbano = FALSE AND sd.largo >= {UMBRAL_LARGO_CARRETERA_MM}
                        THEN {PENALTY_TAMANO_CARRETERA}
                        
                        ELSE 0.0
                    END)
                ELSE 0.0 
            END) as dbg_pen_tamano_contextual,
             (CASE 
                WHEN @flag_bonus_singularidad_lifestyle = TRUE AND sd.tipo_carroceria = 'COUPE' THEN {BONUS_CARROCERIA_COUPE_SINGULAR}
                WHEN @flag_bonus_singularidad_lifestyle = TRUE AND sd.tipo_carroceria = 'DESCAPOTABLE' THEN {BONUS_CARROCERIA_DESCAPOTABLE_SINGULAR}
                ELSE 0.0 
            END) as dbg_bonus_lifestyle,
            (CASE
                WHEN @flag_deportividad_lifestyle = TRUE AND sd.tipo_carroceria = 'COUPE' THEN {BONUS_CARROCERIA_COUPE_DEPORTIVO}
                WHEN @flag_deportividad_lifestyle = TRUE AND sd.tipo_carroceria = 'DESCAPOTABLE' THEN {BONUS_CARROCERIA_DESCAPOTABLE_DEPORTIVO}
                WHEN @flag_deportividad_lifestyle = TRUE AND sd.tipo_carroceria = 'COMERCIAL' THEN {PENALTY_CARROCERIA_COMERCIAL_DEPORTIVO}
                WHEN @flag_deportividad_lifestyle = TRUE AND sd.tipo_carroceria = 'FURGONETA' THEN {PENALTY_CARROCERIA_FURGONETA_DEPORTIVO}
                WHEN @flag_deportividad_lifestyle = TRUE AND sd.tipo_carroceria = 'SUV' THEN {PENALTY_CARROCERIA_SUV_DEPORTIVO}
                ELSE 0.0
            END) as dbg_ajuste_deportividad_lifestyle,
            (CASE 
                WHEN @flag_deportividad_lifestyle = TRUE 
                     AND sd.tipo_mecanica = 'BEV' 
                     AND sd.tipo_carroceria NOT IN ('COUPE', 'DESCAPOTABLE')
                THEN {PENALTY_BEV_NO_DEPORTIVO_LIFESTYLE}
                ELSE 0.0 
            END) as dbg_pen_bev_lifestyle,
            (CASE
                WHEN @flag_ajuste_maletero_personal = TRUE THEN
                    -- Sumamos las tres penalizaciones posibles
                    (CASE 
                        WHEN sd.plazas <= 3 AND sd.maletero_minimo < 450 THEN {PENALTY_MALETERO_INSUFICIENTE}
                        WHEN sd.plazas > 3 AND sd.maletero_minimo < 550 THEN {PENALTY_MALETERO_INSUFICIENTE}
                        ELSE 0.0
                    END)
                    +
                    (CASE
                        WHEN sd.tipo_carroceria = 'COMERCIAL' THEN {PENALTY_COMERCIAL_USO_PERSONAL}
                        ELSE 0.0
                    END)
                ELSE 0.0 
            END) as dbg_ajuste_maletero_personal,
            -- ✅ NUEVA LÓGICA: Bonus para el perfil "Coche de Ciudad"
            (
                (CASE 
                    WHEN @flag_coche_ciudad_perfil = TRUE AND sd.largo < 3300 -- 330 cm = 3300 mm
                    THEN {BONUS_COCHE_MUY_CORTO_CIUDAD} 
                    ELSE 0.0 
                END)
                +
                (CASE 
                    WHEN @flag_coche_ciudad_perfil = TRUE AND sd.peso < 950 
                    THEN {BONUS_COCHE_LIGERO_CIUDAD} 
                    ELSE 0.0 
                END)
            ) as dbg_bonus_coche_ciudad,
            -- ✅ NUEVA LÓGICA: Bonus para el perfil "Coche de Ciudad 2"
            (
                (CASE 
                    WHEN @flag_coche_ciudad_2_perfil = TRUE AND sd.largo < 3900 -- 390 cm = 3900 mm
                    THEN {BONUS_COCHE_CORTO_CIUDAD_2} 
                    ELSE 0.0 
                END)
                +
                (CASE 
                    WHEN @flag_coche_ciudad_2_perfil = TRUE AND sd.peso < 1000 
                    THEN {BONUS_COCHE_LIGERO_CIUDAD_2} 
                    ELSE 0.0 
                END)
            ) as dbg_bonus_coche_ciudad_2,
            (CASE WHEN @km_anuales_estimados > 0 AND @km_anuales_estimados < 10000 THEN (CASE WHEN sd.tipo_mecanica IN ('GASOLINA', 'MHEVG', 'HEVG') THEN {BONUS_MOTOR_POCO_KM} ELSE 0 END) + (CASE WHEN COALESCE(sd.km_ocasion, 0) > 250000 THEN {PENALTY_OCASION_POCO_KM} ELSE 0 END) WHEN @km_anuales_estimados >= 10000 AND @km_anuales_estimados < 30000 THEN (CASE WHEN COALESCE(sd.km_ocasion, 0) > 120000 THEN {PENALTY_OCASION_MEDIO_KM} ELSE 0 END) WHEN @km_anuales_estimados >= 30000 AND @km_anuales_estimados < 60000 THEN (CASE WHEN sd.tipo_mecanica IN ('DIESEL', 'MHEVD', 'HEVD', 'GLP', 'GNV') THEN {BONUS_MOTOR_MUCHO_KM} ELSE 0 END) + (CASE WHEN COALESCE(sd.km_ocasion, 0) > 80000 THEN {PENALTY_OCASION_MUCHO_KM} ELSE 0 END) WHEN @km_anuales_estimados >= 60000 THEN (CASE sd.tipo_mecanica WHEN 'BEV' THEN {BONUS_BEV_MUY_ALTO_KM} WHEN 'REEV' THEN {BONUS_REEV_MUY_ALTO_KM} WHEN 'HEVD' THEN {BONUS_DIESEL_HEVD_MUY_ALTO_KM} WHEN 'DIESEL' THEN {BONUS_DIESEL_HEVD_MUY_ALTO_KM} WHEN 'MHEVD' THEN {BONUS_DIESEL_HEVD_MUY_ALTO_KM} WHEN 'PHEVD' THEN {BONUS_PHEVD_GLP_GNV_MUY_ALTO_KM} WHEN 'GLP' THEN {BONUS_PHEVD_GLP_GNV_MUY_ALTO_KM} WHEN 'GNV' THEN {BONUS_PHEVD_GLP_GNV_MUY_ALTO_KM} ELSE 0.0 END) + (CASE WHEN COALESCE(sd.km_ocasion, 0) > 20000 THEN {PENALTY_OCASION_MUY_ALTO_KM_V2} ELSE 0 END) ELSE 0.0 END) as dbg_ajuste_km_anuales
        FROM ScaledData sd
        WHERE 1=1 {sql_where_clauses_str}
    ),
    -- Este CTE suma los componentes para obtener los scores finales
    IntermediateScores AS (
        SELECT 
            *,
            (
                dbg_score_estetica + dbg_score_premium + dbg_score_singular + dbg_score_altura_libre +
                dbg_score_batalla + dbg_score_altura_interior + dbg_score_ancho +
                dbg_score_devaluacion + dbg_score_maletero_min + dbg_score_maletero_max + dbg_score_largo  +
                dbg_score_bajo_peso  + dbg_score_par_remolque + dbg_score_remolque_cf + dbg_score_remolque_sf + dbg_score_menor_superficie +
                dbg_score_menor_giro + dbg_score_menor_largo + dbg_score_menor_ancho + dbg_score_menor_alto +
                dbg_score_deportividad + dbg_score_menor_rel_peso_pot + dbg_score_potencia + dbg_score_par_deportivo +
                dbg_score_autonomia_max + dbg_score_autonomia_2nd + dbg_score_menor_t_carga +
                dbg_score_pot_carga_ac + dbg_score_pot_carga_dc + dbg_score_menor_aceleracion + dbg_pen_bev_lifestyle
            ) AS puntuacion_base,
            (
                dbg_pen_km_extremo + dbg_pen_puertas + dbg_pen_low_cost_comodidad + dbg_pen_deportividad_comodidad +
                dbg_pen_antiguedad + dbg_ajuste_distintivo + dbg_bonus_ocasion_ambiental + dbg_ajuste_zbe +
                dbg_pen_bev_reev_avent_ocas + dbg_pen_phev_avent_ocas + dbg_pen_electrif_avent_extr +
                dbg_bonus_car_montana + dbg_bonus_car_comercial + dbg_bonus_car_pasajeros + dbg_pen_car_no_aventura +
                dbg_bonus_suv_avent_ocas + dbg_bonus_tt_avent_extr + dbg_bonus_pickup_avent_extr + 
                dbg_ajuste_objetos_especiales + dbg_bonus_car_confort + dbg_bonus_ocasion_uso_ocas +
                dbg_pen_electrif_uso_ocas + dbg_bonus_bev_uso_definido + dbg_pen_phev_uso_intensivo +
                dbg_bonus_punto_carga + dbg_ajuste_awd_aventura + dbg_bonus_awd_nieve + dbg_bonus_awd_montana +
                dbg_bonus_reductoras + dbg_ajuste_diesel_ciudad + dbg_ajuste_km_anuales + dbg_bonus_seguridad  +
                dbg_bonus_fiabilidad + dbg_bonus_durabilidad + dbg_bonus_bajo_consumo + dbg_bonus_coste_uso +
                dbg_bonus_coste_mantenimiento + dbg_pen_antiguedad_general + dbg_pen_tamano_contextual + dbg_bonus_lifestyle + 
                dbg_ajuste_deportividad_lifestyle + dbg_ajuste_maletero_personal + dbg_bonus_coche_ciudad + dbg_bonus_coche_ciudad_2
            ) AS ajustes_experto
        FROM DebugScores
    ),
    DeduplicatedData AS (
        SELECT
            *,
            (puntuacion_base + ajustes_experto) AS score_total,
            ROW_NUMBER() OVER(
                PARTITION BY modelo, tipo_mecanica
                ORDER BY (puntuacion_base + ajustes_experto) DESC, precio_compra_contado ASC
            ) as rn
        FROM 
            IntermediateScores
    ),
    BrandRankedData AS (
        SELECT
            *,
            ROW_NUMBER() OVER(
                PARTITION BY marca
                ORDER BY score_total DESC
            ) as brand_rank
        FROM 
            DeduplicatedData
        WHERE 
            rn = 1
    )
    SELECT
        -- Columnas principales
        nombre, ID, marca, modelo, score_total, puntuacion_base, ajustes_experto, foto,
        
        -- Desglose completo para depuración
        * EXCEPT (nombre, ID, marca, modelo, score_total, puntuacion_base, ajustes_experto, rn, brand_rank)

    FROM 
        BrandRankedData
    WHERE 
        brand_rank <= 2
    ORDER BY 
        score_total DESC
    LIMIT @k 
    """
    # PASO 5: LOGGING Y EJECUCIÓN
    # (Esta parte se mantiene igual)
    log_params_for_logging = [] 
    if params:
        for p in params:
            try:
                param_name = p.name
                param_value = getattr(p, 'value', getattr(p, 'values', "N/A"))
                param_type_str = f"ARRAY<{p.array_type}>" if isinstance(p, bigquery.ArrayQueryParameter) else p.type_
                log_params_for_logging.append({"name": param_name, "value": param_value, "type": param_type_str})
            except Exception as e_log_param:
                logging.error(f"Error procesando param para log: {p}, error: {e_log_param}")
    
  # --- ESTOS SON LOS PRINTS CLAVE PARA EL DEBUG ---
    print("--- 🧠 SQL Query Template Enviada a BigQuery ---")
    print(sql) # Este print ya contiene el valor de FACTOR_ESCALA_BASE
    print("-------------------------------------------------")
    print(f"\n--- 📦 Parameters Enviados a BigQuery ---\n{log_params_for_logging}")
    print("-------------------------------------------------")


    try:
        # No necesitas el bloque de .format() aquí
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        query_job = client.query(sql, job_config=job_config)
        df = query_job.result().to_dataframe() 
        logging.info(f"✅ BigQuery query ejecutada, {len(df)} resultados obtenidos.")
        return df.to_dict(orient="records"), sql, log_params_for_logging
    except Exception as e:
        logging.error(f"❌ Error al ejecutar la query en BigQuery: {e}")
        traceback.print_exc()
        return [], sql, log_params_for_logging
    
    
    
    #===============================================
    
    # RankedDataWithDebug AS (
    #     SELECT
    #         sd.*,
            
    #         -- PUNTUACIÓN BASE (0-100 puntos)
    #         (
    #             (
    #                 sd.estetica_scaled * @peso_estetica 
    #                 + sd.premium_scaled * @peso_premium
    #                 + sd.singular_scaled * @peso_singular
    #                 + sd.altura_scaled * @peso_altura
    #                 + sd.batalla_scaled * @peso_batalla 
    #                 + sd.indice_altura_scaled * @peso_indice_altura
    #                 + sd.ancho_scaled * @peso_ancho_general_score
    #                 + (sd.fiabilidad_scaled * @peso_rating_fiabilidad) -- Corregido para usar pesos separados
    #                 + (sd.durabilidad_scaled * @peso_rating_durabilidad)
    #                 + (sd.seguridad_scaled * @peso_rating_seguridad)
    #                 + (sd.comodidad_scaled * @peso_rating_comodidad)
    #                 + sd.tecnologia_scaled * @peso_rating_tecnologia_conectividad 
    #                 + sd.devaluacion_scaled * @peso_devaluacion
    #                 + sd.maletero_minimo_scaled * @peso_maletero_minimo_score
    #                 + sd.maletero_maximo_scaled * @peso_maletero_maximo_score
    #                 + sd.largo_scaled * @peso_largo_vehiculo_score
    #                 + sd.autonomia_uso_maxima_scaled * @peso_autonomia_vehiculo
    #                 + sd.bajo_peso_scaled * @peso_fav_bajo_peso
    #                 + sd.bajo_consumo_scaled * @peso_fav_bajo_consumo
    #                 + sd.costes_de_uso_bajo_scaled * @peso_fav_bajo_coste_uso_directo
    #                 + sd.costes_mantenimiento_bajo_scaled * @peso_fav_bajo_coste_mantenimiento_directo
    #                 + sd.par_scaled * @peso_par_motor_remolque_score
    #                 + sd.cap_remolque_cf_scaled * @peso_cap_remolque_cf_score
    #                 + sd.cap_remolque_sf_scaled * @peso_cap_remolque_sf_score
    #                 + sd.menor_superficie_planta_scaled * @peso_fav_menor_superficie_planta
    #                 + sd.menor_diametro_giro_scaled * @peso_fav_menor_diametro_giro
    #                 + sd.menor_largo_garage_scaled * @peso_fav_menor_largo_garage
    #                 + sd.menor_ancho_garage_scaled * @peso_fav_menor_ancho_garage
    #                 + sd.menor_alto_garage_scaled * @peso_fav_menor_alto_garage
    #                 + sd.deportividad_style_scaled * @peso_deportividad_style_score
    #                 + sd.menor_rel_peso_potencia_scaled * @peso_fav_menor_rel_peso_potencia_score
    #                 + sd.potencia_maxima_style_scaled * @peso_potencia_maxima_style_score
    #                 + sd.par_scaled * @peso_par_motor_style_score 
    #                 + sd.autonomia_uso_principal_scaled * @peso_autonomia_uso_principal
    #                 + sd.autonomia_uso_2nd_drive_scaled * @peso_autonomia_uso_2nd_drive
    #                 + sd.menor_tiempo_carga_min_scaled * @peso_menor_tiempo_carga_min
    #                 + sd.potencia_maxima_carga_AC_scaled * @peso_potencia_maxima_carga_AC
    #                 + sd.potencia_maxima_carga_DC_scaled * @peso_potencia_maxima_carga_DC
    #                 + sd.menor_aceleracion_scaled * @peso_fav_menor_aceleracion_score
    #             ) * {FACTOR_ESCALA_BASE}
    #         ) AS puntuacion_base,

    #         -- ✅ CORREGIDO: Se han añadido los '+' que faltaban y se han quitado los alias 'AS' de aquí.
    #         -- AJUSTES DE EXPERTO (Puntos +/-)
    #         ( (sd.seguridad_scaled * @peso_rating_seguridad) * (CASE WHEN @flag_bonus_seguridad_critico = TRUE THEN {FACTOR_BONUS_RATING_CRITICO} WHEN @flag_bonus_seguridad_fuerte = TRUE THEN {FACTOR_BONUS_RATING_FUERTE} ELSE 1.0 END) * {FACTOR_ESCALA_BASE} ) - ( (sd.seguridad_scaled * @peso_rating_seguridad) * {FACTOR_ESCALA_BASE} ) as dbg_bonus_seguridad,
    #         (CASE WHEN COALESCE(sd.km_ocasion, 0) >= 300000 THEN {PENALTY_OCASION_KILOMETRAJE_EXTREMO} ELSE 0.0 END) as dbg_pen_km_extremo,
    #         (CASE WHEN @penalizar_puertas = TRUE AND puertas <= 3 THEN {PENALTY_PUERTAS_BAJAS} ELSE 0.0 END) as dbg_pen_puertas,
    #         (CASE WHEN @flag_penalizar_low_cost_comodidad = TRUE THEN (sd.acceso_low_cost_scaled * {PENALTY_LOW_COST_POR_COMODIDAD}) ELSE 0.0 END) as dbg_pen_low_cost_comodidad,
    #         (CASE WHEN @flag_penalizar_deportividad_comodidad = TRUE THEN (sd.deportividad_bq_scaled * {PENALTY_DEPORTIVIDAD_POR_COMODIDAD}) ELSE 0.0 END) as dbg_pen_deportividad_comodidad,
    #         (CASE WHEN @flag_penalizar_antiguo_tec = TRUE THEN CASE WHEN sd.anos_vehiculo > 15 THEN {PENALTY_ANTIGUEDAD_MAS_15_ANOS} WHEN sd.anos_vehiculo > 10 THEN {PENALTY_ANTIGUEDAD_10_A_15_ANOS} WHEN sd.anos_vehiculo > 7 THEN {PENALTY_ANTIGUEDAD_7_A_10_ANOS} WHEN sd.anos_vehiculo > 5 THEN {PENALTY_ANTIGUEDAD_5_A_7_ANOS} ELSE 0.0 END ELSE 0.0 END) as dbg_pen_antiguedad,
    #         (CASE WHEN @flag_aplicar_logica_distintivo = TRUE THEN CASE WHEN UPPER(sd.distintivo_ambiental) IN ('CERO', '0', 'ECO', 'C') THEN {BONUS_DISTINTIVO_ECO_CERO_C} WHEN UPPER(sd.distintivo_ambiental) IN ('B', 'NA') THEN {PENALTY_DISTINTIVO_NA_B} ELSE 0.0 END ELSE 0.0 END) as dbg_ajuste_distintivo,
    #         (CASE WHEN @flag_aplicar_logica_distintivo = TRUE AND COALESCE(sd.ocasion, FALSE) = TRUE THEN {BONUS_OCASION_POR_IMPACTO_AMBIENTAL} ELSE 0.0 END) as dbg_bonus_ocasion_ambiental,
    #         (CASE WHEN @flag_es_municipio_zbe = TRUE AND UPPER(sd.distintivo_ambiental) IN ('CERO', '0', 'ECO') THEN {BONUS_ZBE_DISTINTIVO_FAVORABLE_ECO_CERO} WHEN @flag_es_municipio_zbe = TRUE AND UPPER(sd.distintivo_ambiental) IN ('C') THEN {BONUS_ZBE_DISTINTIVO_FAVORABLE_C} WHEN @flag_es_municipio_zbe = TRUE AND UPPER(sd.distintivo_ambiental) IN ('NA') THEN {PENALTY_ZBE_DISTINTIVO_DESFAVORABLE_NA} WHEN @flag_es_municipio_zbe = TRUE AND UPPER(sd.distintivo_ambiental) IN ('B') THEN {PENALTY_ZBE_DISTINTIVO_DESFAVORABLE_B} ELSE 0.0 END) as dbg_ajuste_zbe,
    #         (CASE WHEN @flag_pen_bev_reev_avent_ocas = TRUE AND sd.tipo_mecanica IN ('BEV', 'REEV') THEN {PENALTY_BEV_REEV_AVENTURA_OCASIONAL} ELSE 0.0 END) as dbg_pen_bev_reev_avent_ocas,
    #         (CASE WHEN @flag_pen_phev_avent_ocas = TRUE AND sd.tipo_mecanica IN ('PHEVD', 'PHEVG') THEN {PENALTY_PHEV_AVENTURA_OCASIONAL} ELSE 0.0 END) as dbg_pen_phev_avent_ocas,
    #         (CASE WHEN @flag_pen_electrif_avent_extr = TRUE AND sd.tipo_mecanica IN ('BEV', 'REEV', 'PHEVD', 'PHEVG') THEN {PENALTY_ELECTRIFICADOS_AVENTURA_EXTREMA} ELSE 0.0 END) as dbg_pen_electrif_avent_extr,
    #         (CASE WHEN @flag_fav_car_montana = TRUE AND sd.tipo_carroceria IN ('SUV', 'TODOTERRENO') THEN {BONUS_CARROCERIA_MONTANA} ELSE 0.0 END) as dbg_bonus_car_montana,
    #         (CASE WHEN @flag_fav_car_comercial = TRUE AND sd.tipo_carroceria IN ('COMERCIAL') THEN {BONUS_CARROCERIA_COMERCIAL} ELSE 0.0 END) as dbg_bonus_car_comercial,
    #         (CASE WHEN @flag_fav_car_pasajeros_pro = TRUE AND sd.tipo_carroceria IN ('3VOL', 'MONOVOLUMEN') THEN {BONUS_CARROCERIA_PASAJEROS_PRO} ELSE 0.0 END) as dbg_bonus_car_pasajeros,
    #         (CASE WHEN @flag_desfav_car_no_aventura = TRUE AND sd.tipo_carroceria IN ('PICKUP', 'TODOTERRENO') THEN {PENALTY_CARROCERIA_NO_AVENTURA} ELSE 0.0 END) as dbg_pen_car_no_aventura,
    #         (CASE WHEN @flag_fav_suv_aventura_ocasional = TRUE AND sd.tipo_carroceria IN ('SUV') THEN {BONUS_SUV_AVENTURA_OCASIONAL} ELSE 0.0 END) as dbg_bonus_suv_avent_ocas,
    #         (CASE WHEN @flag_fav_pickup_todoterreno_aventura_extrema = TRUE AND sd.tipo_carroceria IN ('TODOTERRENO') THEN {BONUS_TODOTERRENO_AVENTURA_EXTREMA} ELSE 0.0 END) as dbg_bonus_tt_avent_extr,
    #         (CASE WHEN @flag_fav_pickup_todoterreno_aventura_extrema = TRUE AND sd.tipo_carroceria IN ('PICKUP') THEN {BONUS_PICKUP_AVENTURA_EXTREMA} ELSE 0.0 END) as dbg_bonus_pickup_avent_extr,
    #         (CASE WHEN @flag_aplicar_logica_objetos_especiales = TRUE THEN CASE WHEN sd.tipo_carroceria IN ('MONOVOLUMEN', 'FURGONETA', 'FAMILIAR', 'SUV') THEN {BONUS_CARROCERIA_OBJETOS_ESPECIALES} WHEN sd.tipo_carroceria IN ('3VOL', 'COUPE', 'DESCAPOTABLE') THEN {PENALTY_CARROCERIA_OBJETOS_ESPECIALES} ELSE 0.0 END ELSE 0.0 END) as dbg_ajuste_objetos_especiales,
    #         (CASE WHEN @flag_fav_carroceria_confort = TRUE AND sd.tipo_carroceria IN ('3VOL', '2VOL', 'SUV', 'FAMILIAR', 'MONOVOLUMEN') THEN {BONUS_CARROCERIA_CONFORT} ELSE 0.0 END) as dbg_bonus_car_confort,
    #         (CASE WHEN @flag_logica_uso_ocasional = TRUE AND COALESCE(sd.ocasion, FALSE) = TRUE THEN {BONUS_OCASION_POR_USO_OCASIONAL} ELSE 0.0 END) as dbg_bonus_ocasion_uso_ocas,
    #         (CASE WHEN @flag_logica_uso_ocasional = TRUE AND sd.tipo_mecanica IN ('PHEVD', 'PHEVG', 'BEV', 'REEV') THEN {PENALTY_ELECTRIFICADOS_POR_USO_OCASIONAL} ELSE 0.0 END) as dbg_pen_electrif_uso_ocas,
    #         (CASE WHEN @flag_favorecer_bev_uso_definido = TRUE AND sd.tipo_mecanica IN ('BEV', 'REEV') THEN {BONUS_BEV_REEV_USO_DEFINIDO} ELSE 0.0 END) as dbg_bonus_bev_uso_definido,
    #         (CASE WHEN @flag_penalizar_phev_uso_intensivo = TRUE AND sd.tipo_mecanica IN ('PHEVD', 'PHEVG') THEN {PENALTY_PHEV_USO_INTENSIVO_LARGO} ELSE 0.0 END) as dbg_pen_phev_uso_intensivo,
    #         (CASE WHEN @flag_favorecer_electrificados_por_punto_carga = TRUE AND sd.tipo_mecanica IN ('BEV', 'PHEVD', 'PHEVG', 'REEV') THEN {BONUS_PUNTO_CARGA_PROPIO} ELSE 0.0 END) as dbg_bonus_punto_carga,
    #         (CASE WHEN @flag_bonus_awd_clima_adverso = TRUE AND sd.traccion = 'ALL' THEN {BONUS_AWD_NINGUNA_AVENTURA_CLIMA_ADVERSO} WHEN @penalizar_awd_ninguna_aventura = TRUE AND sd.traccion = 'ALL' THEN {PENALTY_AWD_NINGUNA_AVENTURA} WHEN @favorecer_awd_aventura_ocasional = TRUE AND sd.traccion = 'ALL' THEN {BONUS_AWD_AVENTURA_OCASIONAL} WHEN @favorecer_awd_aventura_extrema = TRUE AND sd.traccion = 'ALL' THEN {BONUS_AWD_AVENTURA_EXTREMA} ELSE 0.0 END) as dbg_ajuste_awd_aventura,
    #         (CASE WHEN @flag_bonus_awd_nieve = TRUE AND sd.traccion = 'ALL' THEN {BONUS_AWD_ZONA_NIEVE} ELSE 0.0 END) as dbg_bonus_awd_nieve,
    #         (CASE WHEN @flag_bonus_awd_montana = TRUE AND sd.traccion = 'ALL' THEN {BONUS_AWD_ZONA_MONTA} ELSE 0.0 END) as dbg_bonus_awd_montana,
    #         (CASE WHEN @flag_logica_reductoras_aventura = 'FAVORECER_OCASIONAL' AND COALESCE(sd.reductoras, FALSE) = TRUE THEN {BONUS_REDUCTORAS_AVENTURA_OCASIONAL} WHEN @flag_logica_reductoras_aventura = 'FAVORECER_EXTREMA' AND COALESCE(sd.reductoras, FALSE) = TRUE THEN {BONUS_REDUCTORAS_AVENTURA_EXTREMA} ELSE 0.0 END) as dbg_bonus_reductoras,
    #         (CASE WHEN @flag_logica_diesel_ciudad = 'PENALIZAR' AND sd.tipo_mecanica IN ('DIESEL', 'HEVD', 'MHEVD') THEN {PENALTY_DIESEL_CIUDAD} WHEN @flag_logica_diesel_ciudad = 'BONIFICAR' AND sd.tipo_mecanica IN ('DIESEL', 'HEVD', 'MHEVD') THEN {BONUS_DIESEL_CIUDAD_OCASIONAL} ELSE 0.0 END) as dbg_ajuste_diesel_ciudad,
    #         (CASE WHEN @km_anuales_estimados > 0 AND @km_anuales_estimados < 10000 THEN (CASE WHEN sd.tipo_mecanica IN ('GASOLINA', 'MHEVG', 'HEVG') THEN {BONUS_MOTOR_POCO_KM} ELSE 0 END) + (CASE WHEN COALESCE(sd.km_ocasion, 0) > 250000 THEN {PENALTY_OCASION_POCO_KM} ELSE 0 END) WHEN @km_anuales_estimados >= 10000 AND @km_anuales_estimados < 30000 THEN (CASE WHEN COALESCE(sd.km_ocasion, 0) > 120000 THEN {PENALTY_OCASION_MEDIO_KM} ELSE 0 END) WHEN @km_anuales_estimados >= 30000 AND @km_anuales_estimados < 60000 THEN (CASE WHEN sd.tipo_mecanica IN ('DIESEL', 'MHEVD', 'HEVD', 'GLP', 'GNV') THEN {BONUS_MOTOR_MUCHO_KM} ELSE 0 END) + (CASE WHEN COALESCE(sd.km_ocasion, 0) > 80000 THEN {PENALTY_OCASION_MUCHO_KM} ELSE 0 END) WHEN @km_anuales_estimados >= 60000 THEN (CASE sd.tipo_mecanica WHEN 'BEV' THEN {BONUS_BEV_MUY_ALTO_KM} WHEN 'REEV' THEN {BONUS_REEV_MUY_ALTO_KM} WHEN 'HEVD' THEN {BONUS_DIESEL_HEVD_MUY_ALTO_KM} WHEN 'DIESEL' THEN {BONUS_DIESEL_HEVD_MUY_ALTO_KM} WHEN 'MHEVD' THEN {BONUS_DIESEL_HEVD_MUY_ALTO_KM} WHEN 'PHEVD' THEN {BONUS_PHEVD_GLP_GNV_MUY_ALTO_KM} WHEN 'GLP' THEN {BONUS_PHEVD_GLP_GNV_MUY_ALTO_KM} WHEN 'GNV' THEN {BONUS_PHEVD_GLP_GNV_MUY_ALTO_KM} ELSE 0.0 END) + (CASE WHEN COALESCE(sd.km_ocasion, 0) > 20000 THEN {PENALTY_OCASION_MUY_ALTO_KM_V2} ELSE 0.0 END) ELSE 0.0 END) as dbg_ajuste_km_anuales

    #         ) AS ajustes_experto,
            
    #     FROM ScaledData sd
    #     WHERE 1=1 {sql_where_clauses_str}
    # ),
    
    # -- Este CTE calcula el score total y realiza la deduplicación de modelos
    # DeduplicatedData AS (
    #     SELECT
    #         *,
    #         (puntuacion_base + ajustes_experto) AS score_total,
    #         ROW_NUMBER() OVER(
    #             PARTITION BY modelo, tipo_mecanica
    #             ORDER BY (puntuacion_base + ajustes_experto) DESC, precio_compra_contado ASC
    #         ) as rn
    #     FROM 
    #         RankedDataWithDebug
    # ),
    # -- Este CTE calcula el score total y realiza la deduplicación de modelos
    # DeduplicatedData AS (
    #     SELECT
    #         *,
    #         (puntuacion_base + ajustes_experto) AS score_total,
    #         ROW_NUMBER() OVER(
    #             PARTITION BY modelo, tipo_mecanica
    #             ORDER BY (puntuacion_base + ajustes_experto) DESC, precio_compra_contado ASC
    #         ) as rn
    #     FROM 
    #         IntermediateScores
    # ),

    # -- Este CTE aplica el filtro de diversificación por marca
    # BrandRankedData AS (
    #     SELECT
    #         *,
    #         ROW_NUMBER() OVER(
    #             PARTITION BY marca
    #             ORDER BY score_total DESC
    #         ) as brand_rank
    #     FROM 
    #         DeduplicatedData
    #     WHERE 
    #         rn = 1
    # )

    # -- Selección Final
    # SELECT
    #     -- Columnas principales para mostrar
    #     nombre, ID, marca, modelo, score_total, puntuacion_base, ajustes_experto, foto,
        
    #     -- El resto de columnas para un análisis completo, incluyendo todas las de debug
    #     * EXCEPT (nombre, ID, marca, modelo, score_total, puntuacion_base, ajustes_experto, rn, brand_rank)

    # FROM 
    #     BrandRankedData
    # WHERE 
    #     brand_rank <= 2
    # ORDER BY 
    #     score_total DESC
    # LIMIT @k


# Paso a Paso: De la Preferencia al Bonus Final
# Paso 1: La "Nota" Objetiva del Coche (El Escalado)
# Primero, el sistema no puede trabajar con el 9.1 directamente. Lo convierte a nuestra escala universal de 0 a 1.

# Fórmula: (Valor del Coche - Mínimo) / (Rango Total)

# Asumiendo que la escala de seguridad en tu base de datos va de 1 a 10:

# Cálculo: (9.1 - 1) / (10 - 1) = 8.1 / 9 = 0.9

# Resultado: La "nota" objetiva de este coche en seguridad (sd.seguridad_scaled) es 0.9. Es un coche sobresaliente en este aspecto.

# Paso 2: La Contribución Base a la Puntuación (La Ponderación)
# Ahora, calculamos cuántos puntos habría aportado la seguridad a la "Puntuación Base" de 0-100, antes de aplicar ningún bonus.

# Fórmula: (Nota del Coche * Peso Normalizado del Usuario) * FACTOR_ESCALA_BASE

# Valores:

# sd.seguridad_scaled: 0.9

# @peso_rating_seguridad: 0.018569 (el valor de tu log)

# FACTOR_ESCALA_BASE: 100.0

# Cálculo: (0.9 * 0.018569) * 100.0 = 0.0167121 * 100.0 = 1.67121 puntos

# Resultado: Si el usuario no hubiera marcado la seguridad como "crítica", este coche habría recibido 1.67 puntos por su seguridad en la Puntuación Base.

# Paso 3: El Amplificador del Experto (El CASE en la SQL)
# Aquí es donde entra en juego la lógica que querías depurar.

# La Lógica: Como el usuario dio un 10/10 en seguridad, tu nodo calcular_flags_dinamicos_node activó el flag flag_bonus_seguridad_critico = TRUE.

# El CASE evalúa: WHEN @flag_bonus_seguridad_critico = TRUE... -> Esto es verdadero.

# Resultado: La sentencia CASE devuelve el valor de tu constante {FACTOR_BONUS_RATING_CRITICO}, que habíamos definido como 2.0.

# Paso 4: El Cálculo del Bonus (La Fórmula de Depuración)
# Tu columna dbg_bonus_seguridad está diseñada para aislar el efecto del bonus. La fórmula que creamos fue:

# Bonus = (Puntuación_Base_Seguridad * Factor_Bonus) - Puntuación_Base_Seguridad

# Esta fórmula calcula la "Puntuación Total de Seguridad" y le resta la "Puntuación Base de Seguridad" para mostrarte únicamente los puntos extra que se han añadido.

# Cálculo:

# Puntuación Total de Seguridad: 1.67121 * 2.0 = 3.34242

# Puntuación Base de Seguridad: 1.67121

# Bonus: 3.34242 - 1.67121 = 1.67121

# Conclusión Final
# El resultado de tu log (dbg_bonus_seguridad: 1.67125) y nuestro cálculo manual (1.67121) son prácticamente idénticos (la pequeña diferencia se debe a los decimales que no vemos en los logs).

# Esto confirma que el sistema está funcionando a la perfección:

# Calculó que la contribución base de la seguridad para ese coche era de 1.67 puntos.

# Como activaste el bonus "crítico", el sistema duplicó esa contribución.

# La columna de depuración dbg_bonus_seguridad te muestra correctamente los 1.67 puntos adicionales que se han sumado al score final gracias a esta regla.

# ¡Tu lógica de scoring está funcionando exactamente como la diseñamos!