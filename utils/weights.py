# utils/weights.py
from typing import Optional, Dict, Any # Añadir tipos
from .conversion import is_yes
import yaml
import logging
from .enums import NivelAventura , FrecuenciaUso, DistanciaTrayecto,EstiloConduccion
from graph.perfil.state import PerfilUsuario # Importar para type hint
# from config.settings import (altura_map, MIN_SINGLE_RAW_WEIGHT, MAX_SINGLE_RAW_WEIGHT, AJUSTE_CRUDO_SEGURIDAD_POR_NIEBLA , PESO_CRUDO_FAV_MENOR_SUPERFICIE, PESO_CRUDO_FAV_MENOR_DIAMETRO_GIRO, PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE, UMBRAL_RATING_IMPACTO_PARA_FAV_PESO_CONSUMO, UMBRAL_RATING_COSTES_USO_PARA_FAV_CONSUMO_COSTES, UMBRAL_RATING_COMODIDAD_PARA_FAVORECER, RAW_WEIGHT_BONUS_FIABILIDAD_POR_IMPACTO,
#                             RAW_WEIGHT_ADICIONAL_FAV_BAJO_PESO_POR_IMPACTO, RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_IMPACTO, RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_COSTES, RAW_WEIGHT_FAV_BAJO_COSTE_USO_DIRECTO, RAW_WEIGHT_FAV_BAJO_COSTE_MANTENIMIENTO_DIRECTO,
#                             RAW_PESO_DEPORTIVIDAD_ALTO, RAW_PESO_MENOR_REL_PESO_POTENCIA_ALTO, RAW_PESO_POTENCIA_MAXIMA_ALTO, RAW_PESO_PAR_MOTOR_DEPORTIVO_ALTO, RAW_PESO_MENOR_ACELERACION_ALTO,
#                             RAW_PESO_DEPORTIVIDAD_MEDIO, RAW_PESO_MENOR_REL_PESO_POTENCIA_MEDIO, RAW_PESO_POTENCIA_MAXIMA_MEDIO, RAW_PESO_PAR_MOTOR_DEPORTIVO_MEDIO, RAW_PESO_MENOR_ACELERACION_MEDIO,
#                             RAW_PESO_DEPORTIVIDAD_BAJO, RAW_PESO_MENOR_REL_PESO_POTENCIA_BAJO, RAW_PESO_POTENCIA_MAXIMA_BAJO, RAW_PESO_PAR_MOTOR_DEPORTIVO_BAJO, RAW_PESO_MENOR_ACELERACION_BAJO,
#                             RAW_PESO_PAR_MOTOR_REMOLQUE, RAW_PESO_CAP_REMOLQUE_CF, RAW_PESO_CAP_REMOLQUE_SF, RAW_WEIGHT_ADICIONAL_FAV_IND_ALTURA_INT_POR_COMODIDAD, RAW_WEIGHT_ADICIONAL_FAV_AUTONOMIA_VEHI_POR_COMODIDAD,
#                             PESO_CRUDO_FAV_MALETERO_MAX, PESO_CRUDO_FAV_MALETERO_MIN, PESO_CRUDO_FAV_BATALLA_ALTURA_MAYOR_190, PESO_CRUDO_FAV_IND_ALTURA_INT_ALTURA_MAYOR_190,PESO_CRUDO_FAV_ANCHO_PASAJEROS_OCASIONAL, PESO_CRUDO_FAV_ANCHO_PASAJEROS_FRECUENTE , PESO_CRUDO_FAV_DEVALUACION,
#                             RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_USO_INTENSIVO, WEIGHT_AUTONOMIA_PRINCIPAL_MUY_ALTO_KM,WEIGHT_AUTONOMIA_2ND_DRIVE_MUY_ALTO_KM, WEIGHT_TIEMPO_CARGA_MIN_MUY_ALTO_KM, PESO_CRUDO_FAV_SINGULAR_PREF_DISENO_EXCLUSIVO,
#                             WEIGHT_POTENCIA_DC_MUY_ALTO_KM,PESO_CRUDO_FAV_ESTETICA , PESO_CRUDO_FAV_PREMIUM_APASIONADO_MOTOR, PESO_CRUDO_FAV_SINGULAR_APASIONADO_MOTOR,PESO_CRUDO_FAV_DIAMETRO_GIRO_CONDUC_CIUDAD, PESO_CRUDO_BASE, 
#                             PESO_CRUDO_FAV_MALETERO_ESP_OBJ_ESPECIALES_ANCHO ,PESO_CRUDO_FAV_MALETERO_ESP_OBJ_ESPECIALES_LARGO, RAW_WEIGHT_BONUS_DURABILIDAD_POR_IMPACTO
#                             )
# --- Configuración de Logging ---
logger = logging.getLogger(__name__) 

def compute_raw_weights(
    preferencias: Optional[Dict[str, Any]],
    info_pasajeros_dict: Optional[Dict[str, Any]],
    es_zona_nieblas: bool = False,
    km_anuales_estimados: Optional[int] = None,
) -> Dict[str, float]:
    """
    Calcula los pesos crudos usando el método "Boost y Re-Normalización".
    El estilo de conducción ajusta la importancia de las dimensiones principales
    antes de aplicar los multiplicadores de preferencias específicas.
    """
    # --- PASO 1: Carga del "Genoma" de Pesos Base ---
    try:
        with open('master_weights.yaml', 'r', encoding='utf-8') as f:
            master_weights = yaml.safe_load(f)
    except FileNotFoundError:
        logging.error("ERROR CRÍTICO: No se encontró 'master_weights.yaml'. El cálculo de pesos no puede continuar.")
        return {}

    preferencias = preferencias or {}
    pasajeros_info = info_pasajeros_dict or {}

    # --- PASO 2: Ajuste Dinámico de Pesos Base (Boost y Re-Normalización) ---
    dynamic_master_weights = master_weights.copy()
    
    # Manejo robusto del estilo de conducción, aceptando string o Enum
    estilo_input = preferencias.get("estilo_conduccion", EstiloConduccion.TRANQUILO)
    try:
        estilo = EstiloConduccion(estilo_input)
    except ValueError:
        estilo = EstiloConduccion.TRANQUILO

    if estilo in [EstiloConduccion.DEPORTIVO, EstiloConduccion.MIXTO]:
        performance_keys = [
            'deportividad_style_score', 'fav_menor_rel_peso_potencia_score',
            'potencia_maxima_style_score', 'par_motor_style_score',
            'fav_menor_aceleracion_score'
        ]
        
        boost_factor = 5.0 if estilo == EstiloConduccion.DEPORTIVO else 2.5

        for key in performance_keys:
            if key in dynamic_master_weights:
                dynamic_master_weights[key] *= boost_factor
        
        total_boosted_weight = sum(dynamic_master_weights.values())
        if total_boosted_weight > 0:
            dynamic_master_weights = {k: v / total_boosted_weight for k, v in dynamic_master_weights.items()}

     # --- PASO 3: Inicialización de Multiplicadores ---
    multiplicadores = {key: 1.0 for key in dynamic_master_weights.keys()}

    # --- PASO 4: Aplicación de Reglas de Negocio como Multiplicadores ---

    # --- 4.1: Lógica de Preferencias Directas (Booleanas) ---
    if is_yes(preferencias.get("valora_estetica")): multiplicadores['estetica'] *= 6.0
    if is_yes(preferencias.get("apasionado_motor")):
        multiplicadores['premium'] *= 6.0
        multiplicadores['singular'] *= 5.0
    if is_yes(preferencias.get("prefiere_diseno_exclusivo")): multiplicadores['singular'] *= 6.0
    if is_yes(preferencias.get("prioriza_baja_depreciacion")): multiplicadores['devaluacion'] *= 10.0
    if is_yes(preferencias.get("arrastra_remolque")):
        multiplicadores['par_motor_remolque_score'] *= 6.0
        multiplicadores['cap_remolque_cf_score'] *= 7.0
        multiplicadores['cap_remolque_sf_score'] *= 3.0

    # --- 4.2: Lógica de Escenarios de Uso y Contexto ---
    if km_anuales_estimados is not None and km_anuales_estimados > 60000:
        multiplicadores['autonomia_uso_maxima'] *= 9.0
        multiplicadores['autonomia_uso_2nd_drive'] *= 3.0
        multiplicadores['menor_tiempo_carga_min'] *= 9.0
        multiplicadores['potencia_maxima_carga_DC'] *= 9.0

# Lógica de Aventura (usando Enum para mayor robustez)
    aventura_input = preferencias.get("aventura", NivelAventura.ninguna)
    try:
        aventura_val = NivelAventura(aventura_input)
    except ValueError:
        aventura_val = NivelAventura.ninguna
        
    aventura_map = {NivelAventura.ocasional: 4.0, NivelAventura.extrema: 10.0}
    multiplicadores['altura_libre_suelo'] *= aventura_map.get(aventura_val, 1.0)

    if is_yes(preferencias.get("altura_mayor_190")):
        multiplicadores['batalla'] *= 5.0
        multiplicadores['indice_altura_interior'] *= 8.0
   
    # --- 4.3: Lógica Condicional Compleja (Pasajeros, Carga, Garaje) ---
    frecuencia_pasajeros = pasajeros_info.get("frecuencia")
    num_ninos_silla = pasajeros_info.get("num_ninos_silla", 0)
    num_otros_pasajeros = pasajeros_info.get("num_otros_pasajeros", 0)
    if frecuencia_pasajeros == "frecuente" and num_otros_pasajeros >= 2:
        multiplicadores['ancho'] *= 8.0
    elif frecuencia_pasajeros == "ocasional" and (num_ninos_silla + num_otros_pasajeros) >= 2:
        multiplicadores['ancho'] *= 4.0

    if is_yes(preferencias.get("transporta_carga_voluminosa")):
        multiplicadores['maletero_minimo_score'] *= 8.0
        multiplicadores['maletero_maximo_score'] *= 6.0
        if is_yes(preferencias.get("necesita_espacio_objetos_especiales")):
            multiplicadores['largo_vehiculo_score'] *= 7.0
            multiplicadores['ancho'] *= 5.0 # Efecto aditivo ahora es multiplicativo

    if is_yes(preferencias.get("circula_principalmente_ciudad")):
        multiplicadores['fav_menor_diametro_giro'] *= 7.0
    
    if preferencias.get("tiene_garage") is not None:
        if not is_yes(preferencias.get("tiene_garage")):
            if is_yes(preferencias.get("problemas_aparcar_calle")):
                multiplicadores['fav_menor_superficie_planta'] *= 3.0
        else: # Sí tiene garaje
            if not is_yes(preferencias.get("espacio_sobra_garage")):
                multiplicadores['fav_menor_diametro_giro'] *= 5.0
                problema_dim = preferencias.get("problema_dimension_garage") or []
                if "largo" in problema_dim: multiplicadores['fav_menor_largo_garage'] *= 8.0
                if "ancho" in problema_dim: multiplicadores['fav_menor_ancho_garage'] *= 8.0
                if "alto" in problema_dim:  multiplicadores['fav_menor_alto_garage'] *= 8.0

    
    # --- 4.5: Lógica de Ratings por Umbrales (Versión Final) ---
    def get_rating_multiplier(rating_val: Optional[float]) -> float:
        """Helper para convertir un rating de 1-10 en un multiplicador."""
        rating_val = rating_val or 0
        if rating_val >= 9: return 1.10  # Prioridad Crítica
        if rating_val >= 7: return 1.05  # Interés Fuerte
        if rating_val >= 5: return 1.02  # Interés Moderado
        return 1.0                     # Sin interés / Por defecto

    # Ratings que afectan a una sola característica
    multiplicadores['rating_seguridad'] *= get_rating_multiplier(preferencias.get("rating_seguridad"))
    multiplicadores['rating_tecnologia_conectividad'] *= get_rating_multiplier(preferencias.get("rating_tecnologia_conectividad"))

    # Ratings que afectan a múltiples características
    mult_fiab_dur = get_rating_multiplier(preferencias.get("rating_fiabilidad_durabilidad"))
    multiplicadores['rating_fiabilidad'] *= mult_fiab_dur
    multiplicadores['rating_durabilidad'] *= mult_fiab_dur

    mult_comodidad = get_rating_multiplier(preferencias.get("rating_comodidad"))
    multiplicadores['rating_comodidad'] *= mult_comodidad
    if mult_comodidad > 1.0:
        multiplicadores['indice_altura_interior'] *= (mult_comodidad / 2) # Influencia secundaria
        multiplicadores['autonomia_uso_maxima'] *= (mult_comodidad / 2)

    mult_costes_uso = get_rating_multiplier(preferencias.get("rating_costes_uso"))
    if mult_costes_uso > 1.0:
        multiplicadores['fav_bajo_consumo'] *= mult_costes_uso
        multiplicadores['fav_bajo_coste_uso_directo'] *= mult_costes_uso
        multiplicadores['fav_bajo_coste_mantenimiento_directo'] *= mult_costes_uso
        
    # Impacto Ambiental (regla aditiva convertida a multiplicativa)
    if (preferencias.get("rating_impacto_ambiental") or 0) >= 8:
        multiplicadores['fav_bajo_peso'] *= 10.0
        multiplicadores['fav_bajo_consumo'] *= 7.0
        multiplicadores['rating_fiabilidad'] *= 2.0 # Bonus
        multiplicadores['rating_durabilidad'] *= 3.0 # Bonus

    # --- 4.6: Lógica de Factores Externos ---
    if es_zona_nieblas:
        multiplicadores['rating_seguridad'] *= 1.5 # Amplificador de seguridad por clima

# --- PASO 5: Cálculo de Pesos Crudos Finales y Clamping ---
    raw_weights = {
        key: dynamic_master_weights.get(key, 0.0) * multiplicadores.get(key, 1.0)
        for key in dynamic_master_weights
    }
    
    logging.debug(f"Pesos Crudos (Antes de Clamping): {raw_weights}")
    print(f"DEBUG (Weights) ► Pesos Crudos (Antes de Clamping): {raw_weights}")

    # --- PASO 7: Clamping Final ---
    MAX_SINGLE_RAW_WEIGHT = 10.0
    for key, value in raw_weights.items():
        min_weight = dynamic_master_weights.get(key, 0.0)
        raw_weights[key] = max(min_weight, min(MAX_SINGLE_RAW_WEIGHT, value))

    final_weights = {k: float(v or 0.0) for k, v in raw_weights.items()}
    
    logging.debug(f"Pesos Crudos Finales (Después de Clamping): {final_weights}")
    print(f"DEBUG (Weights) ► Pesos Crudos Finales (Después de Clamping): {final_weights}")
    
    return final_weights

# Cuando el usuario dice que su estilo es "deportivo", la función hace lo siguiente:

# Paso 1: El "Boost" (La Multiplicación que tú viste)
# El sistema primero multiplica el tamaño de esa porción por 5.
# 6.49% * 5 = 32.45%.
# Hace lo mismo con las otras 4 características de rendimiento. Ahora, si sumamos todas las porciones, el pastel ya no es del 100%, ¡sino mucho más grande (ej. 157%)!

# Paso 2: La "Re-Normalización" (El Paso Clave)
# El sistema no puede trabajar con un pastel del 157%. Su regla de oro es que el total siempre debe ser 100%. Para lograrlo, reduce el tamaño de TODAS las porciones proporcionalmente hasta que la suma vuelva a ser 100%.
# La porción de fav_menor_rel_peso_potencia_score se reduce desde ese 32.45% temporal, pero como partía de un valor tan grande, su porción final en el nuevo pastel del 100% es del 20.60%.
# En esencia, para que la porción de "Rendimiento" crezca tanto, ha tenido que "robar" un trocito de todas las demás porciones (Economía, Seguridad, Practicidad, etc.).

# Demostración Matemática
# Vamos a demostrarlo con los números exactos:
# Suma de los pesos de rendimiento originales:
# deportividad (0.0043) + rel_peso_pot (0.0649) + potencia_max (0.024) + par_motor (0.0144) + aceleracion (0.036) = 0.1436
# Boost: Multiplicamos este grupo por 5. El resto de los pesos (que suman 1.0 - 0.1436 = 0.8564) se quedan igual.
# Nuevo valor del grupo de rendimiento: 0.1436 * 5 = 0.718
# Nueva suma total del pastel: 0.718 (rendimiento) + 0.8564 (el resto) = 1.5744
# Peso de rel_peso_pot antes de re-normalizar: 0.0649 * 5 = 0.3245
# Re-Normalización: Dividimos el peso "boosteado" por la nueva suma total.
# 0.3245 / 1.5744 = **0.20609...**

# ¡El resultado coincide exactamente con lo que observaste!
# Conclusión
# El sistema está funcionando a la perfección. No está simplemente multiplicando un peso, sino que está redistribuyendo la importancia total para que las características de rendimiento ocupen una porción mucho mayor del "presupuesto de importancia" total.
# Esto es mucho más robusto porque los pesos que envías a BigQuery siguen siendo proporcionales y su suma es 1.0, evitando el problema de la "doble amplificación" que tenías antes.


# normalize_weights se mantiene igual (quizás con el DEBUG print que añadí antes)
def normalize_weights(raw_weights: dict) -> dict:
    """Normaliza los pesos crudos para que sumen 1.0."""
    valid_values = [v for v in raw_weights.values() if isinstance(v, (int, float))]
    total = sum(valid_values) or 1.0 
    logging.info(f"DEBUG (Weights) ► ► Suma Pesos Crudos: {total}")
    normalized = {k: (v / total) if isinstance(v, (int, float)) else 0.0 for k, v in raw_weights.items()}
    print(f"DEBUG (Normalize Weights) ► Pesos Normalizados: {normalized}")
    return normalized


