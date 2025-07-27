# utils/weights.py
from typing import Optional, Dict, Any # Añadir tipos
from .conversion import is_yes
import yaml
import math
import logging
from .enums import NivelAventura , FrecuenciaUso, DistanciaTrayecto,EstiloConduccion, DimensionProblematica
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

# Flujo General de la Lógica
# La función sigue un flujo de datos muy claro y lógico:

# Pesos Base (YAML) → Ajuste por Arquetipo → Pesos Dinámicos → Aplicación de Multiplicadores (Preferencias) → Pesos Crudos → Mecanismo de Seguridad (Clamping) → Pesos Finales


logger = logging.getLogger(__name__) 
# def compute_raw_weights(
#     preferencias: Optional[Dict[str, Any]],
#     info_pasajeros_dict: Optional[Dict[str, Any]],
#     es_zona_nieblas: bool = False,
#     km_anuales_estimados: Optional[int] = None,
# ) -> Dict[str, float]:
#     """
#     Calcula los pesos crudos para el perfil de un usuario.
#     1. Suaviza los pesos base para reducir la disparidad inicial.
#     2. Ajusta los pesos según el arquetipo de conducción.
#     3. Aplica multiplicadores basados en preferencias explícitas (booleanas/contextuales).
#     """
#     # --- PASO 1: Carga del "Genoma" de Pesos Base ---
#     try:
#         with open('master_weights.yaml', 'r', encoding='utf-8') as f:
#             master_weights = yaml.safe_load(f)
#     except FileNotFoundError:
#         logging.error("ERROR CRÍTICO: No se encontró 'master_weights.yaml'. El cálculo de pesos no puede continuar.")
#         return {}
#     except Exception as e:
#         logging.error(f"Error al cargar o procesar 'master_weights.yaml': {e}")
#         return {}

#     # --- PASO 1.5: SUAVIZADO DE PESOS BASE CON RAÍZ CUADRADA (NUEVO) ---
#     # Este paso reduce la diferencia entre los pesos muy altos (ej. fiabilidad) y los muy bajos (ej. estética),
#     # creando una base más equilibrada antes de aplicar la lógica de personalización.
#     master_weights_sqrt = {k: math.sqrt(v) for k, v in master_weights.items()}
    
#     # Después de la transformación, se re-normalizan para que la suma total vuelva a ser 1.0
#     total_sqrt_weight = sum(master_weights_sqrt.values())
#     if total_sqrt_weight > 0:
#         master_weights = {k: v / total_sqrt_weight for k, v in master_weights_sqrt.items()}
    
#     # A partir de aquí, la función trabaja con los pesos ya "suavizados" y normalizados.

#     preferencias = preferencias or {}
#     pasajeros_info = info_pasajeros_dict or {}

#     # --- PASO 2: Ajuste Dinámico de Pesos Base (Boost y Re-Normalización) ---
#     dynamic_master_weights = master_weights.copy()
    
#     estilo_input = preferencias.get("estilo_conduccion", "TRANQUILO")
#     try:
#         estilo = EstiloConduccion(estilo_input)
#     except (ValueError, NameError):
#         estilo = "TRANQUILO"

#     # Diccionario que define los multiplicadores para cada característica por estilo
#     # NOTA: Puedes ajustar estos valores como consideres oportuno
#     style_multipliers = {
#         "DEPORTIVO": {
#             'deportividad_style_score': 40.0, # sacar despues a bq
#             'fav_menor_rel_peso_potencia_score': 14.0, # Prioridad máxima
#             'potencia_maxima_style_score': 30.0,
#             'par_motor_style_score': 14.0,
#             'fav_menor_aceleracion_score': 12.0       # Casi tan importante como la relación peso/potencia
#         },
#         "MIXTO": {
#             'deportividad_style_score': 20.0,
#             'fav_menor_rel_peso_potencia_score': 8.5,
#             'potencia_maxima_style_score': 10.0,
#             'par_motor_style_score': 8.5,
#             'fav_menor_aceleracion_score': 6.0
#         }
#     }

#     # Determinamos el estilo de forma robusta
#     current_style_name = estilo.name if hasattr(estilo, 'name') else estilo

#     # Aplicamos los multiplicadores si el estilo es DEPORTIVO o MIXTO
#     if current_style_name in style_multipliers:
#         # Obtenemos el diccionario de multiplicadores para el estilo actual
#         multipliers_to_apply = style_multipliers[current_style_name]

#         # Iteramos sobre el diccionario y aplicamos cada multiplicador individual
#         for key, boost_value in multipliers_to_apply.items():
#             if key in dynamic_master_weights:
#                 dynamic_master_weights[key] *= boost_value
        
#         # El proceso de re-normalización se mantiene igual
#         total_boosted_weight = sum(dynamic_master_weights.values())
#         if total_boosted_weight > 0:
#             dynamic_master_weights = {k: v / total_boosted_weight for k, v in dynamic_master_weights.items()}

#     # --- PASO 3: Inicialización de Multiplicadores ---
#     multiplicadores = {key: 1.0 for key in dynamic_master_weights.keys()}

#     # --- PASO 4: Aplicación de Reglas de Negocio (Multiplicadores Booleanos/Contextuales) ---
#     # (Usando los valores de multiplicadores comprimidos que definimos)

#     # --- 4.1: Lógica de Preferencias Directas (Booleanas) ---
#     if is_yes(preferencias.get("valora_estetica")): multiplicadores['estetica'] *= 20.0
#     if is_yes(preferencias.get("apasionado_motor")):
#         multiplicadores['premium'] *= 25.0
#         multiplicadores['singular'] *= 4.0
#     if is_yes(preferencias.get("prefiere_diseno_exclusivo")): multiplicadores['singular'] *= 20.0
#     if is_yes(preferencias.get("prioriza_baja_depreciacion")): multiplicadores['devaluacion'] *= 30.0
#     if is_yes(preferencias.get("arrastra_remolque")):
#         multiplicadores['par_motor_remolque_score'] *= 10.0
#         multiplicadores['cap_remolque_cf_score'] *= 10.0
#         multiplicadores['cap_remolque_sf_score'] *= 10.0

#     # --- 4.2: Lógica de Escenarios de Uso y Contexto ---
#     if km_anuales_estimados is not None and km_anuales_estimados > 60000:
#         multiplicadores['autonomia_uso_maxima'] *= 5.0
#         multiplicadores['autonomia_uso_2nd_drive'] *= 5.0
#         multiplicadores['menor_tiempo_carga_min'] *= 5.0
#         multiplicadores['potencia_maxima_carga_DC'] *= 5.0

# # Lógica de Aventura (usando Enum para mayor robustez)
#     aventura_input = preferencias.get("aventura", NivelAventura.ninguna)
#     try:
#         aventura_val = NivelAventura(aventura_input)
#     except ValueError:
#         aventura_val = NivelAventura.ninguna
        
#     aventura_map = {NivelAventura.ocasional: 8.0, NivelAventura.extrema:12.0}
#     multiplicadores['altura_libre_suelo'] *= aventura_map.get(aventura_val, 1.0)

#     if is_yes(preferencias.get("altura_mayor_190")):
#         multiplicadores['batalla'] *= 25.0
#         multiplicadores['indice_altura_interior'] *= 25.0
   
#     # --- 4.3: Lógica Condicional Compleja (Pasajeros, Carga, Garaje) ---
#     frecuencia_pasajeros = pasajeros_info.get("frecuencia_viaje_con_acompanantes")
#     num_ninos_silla = pasajeros_info.get("num_ninos_silla", 0)
#     num_otros_pasajeros = pasajeros_info.get("num_otros_pasajeros", 0)
#     if frecuencia_pasajeros == "frecuente" and num_otros_pasajeros >= 2:
#         logging.debug("Multiplicador de ancho aumentado a 3.0 por frecuencia frecuente y >=2 pasajeros")
#         multiplicadores['ancho'] *= 3.0
#     elif frecuencia_pasajeros == "ocasional" and (num_ninos_silla + num_otros_pasajeros) >= 2:
#         logging.debug("Multiplicador de ancho aumentado a 1.5 por frecuencia ocasional y >=2 pasajeros")
#         multiplicadores['ancho'] *= 1.5
        

#     if is_yes(preferencias.get("transporta_carga_voluminosa")):
#         multiplicadores['maletero_minimo_score'] *= 35.0
#         multiplicadores['maletero_maximo_score'] *= 30.0
#         if is_yes(preferencias.get("necesita_espacio_objetos_especiales")):
#             multiplicadores['largo_vehiculo_score'] *= 30.0
#             multiplicadores['ancho'] *= 3.0 # Efecto aditivo ahora es multiplicativo

#     if is_yes(preferencias.get("circula_principalmente_ciudad")):
#         multiplicadores['fav_menor_diametro_giro'] *= 6.0
    
#     if preferencias.get("tiene_garage") is not None:
#         if not is_yes(preferencias.get("tiene_garage")):
#             if is_yes(preferencias.get("problemas_aparcar_calle")):
#                 multiplicadores['fav_menor_superficie_planta'] *= 3.0
#         else: # Sí tiene garaje
#             if not is_yes(preferencias.get("espacio_sobra_garage")):
#                 multiplicadores['fav_menor_diametro_giro'] *= 2.5
#                 problema_dim = preferencias.get("problema_dimension_garage") or []
#                 if "largo" in problema_dim: multiplicadores['fav_menor_largo_garage'] *= 3.5
#                 if "ancho" in problema_dim: multiplicadores['fav_menor_ancho_garage'] *= 3.5
#                 if "alto" in problema_dim:  multiplicadores['fav_menor_alto_garage'] *= 3.5

   
#     # --- 4.6: Lógica de Factores Externos ---
#     if es_zona_nieblas:
#         multiplicadores['rating_seguridad'] *= 2.5 # Amplificador de seguridad por clima

# # --- PASO 5: Cálculo de Pesos Crudos Finales y Clamping ---
#     raw_weights = {
#         key: dynamic_master_weights.get(key, 0.0) * multiplicadores.get(key, 1.0)
#         for key in dynamic_master_weights
#     }
    
#     logging.debug(f"Pesos Crudos (Antes de Clamping): {raw_weights}")
#     #print(f"DEBUG (Weights) ► Pesos Crudos (Antes de Clamping): {raw_weights}")

#     # --- PASO 7: Clamping Final ---
#     MAX_SINGLE_RAW_WEIGHT =10.0
#     for key, value in raw_weights.items():
#         min_weight = dynamic_master_weights.get(key, 0.0)
#         raw_weights[key] = max(min_weight, min(MAX_SINGLE_RAW_WEIGHT, value))

#     final_weights = {k: float(v or 0.0) for k, v in raw_weights.items()}
    
#     logging.debug(f"Pesos Crudos Finales (Después de Clamping): {final_weights}")
#     #print(f"DEBUG (Weights) ► Pesos Crudos Finales (Después de Clamping): {final_weights}")
    
#     return final_weights

def compute_raw_weights(
    preferencias: Optional[Dict[str, Any]],
    info_pasajeros_dict: Optional[Dict[str, Any]],
    es_zona_nieblas: bool = False,
    km_anuales_estimados: Optional[int] = None,
) -> Dict[str, float]:
    """
    Calcula los pesos crudos (sin normalizar) para el perfil de un usuario.
    La normalización final se realiza en un paso externo.
    1. Suaviza los pesos base para reducir la disparidad inicial.
    2. Ajusta los pesos según el arquetipo de conducción.
    3. Aplica multiplicadores basados en preferencias explícitas.
    """
    # --- PASO 1: Carga del "Genoma" de Pesos Base ---
    try:
        with open('master_weights.yaml', 'r', encoding='utf-8') as f:
            master_weights = yaml.safe_load(f)
    except FileNotFoundError:
        logging.error("ERROR CRÍTICO: No se encontró 'master_weights.yaml'. El cálculo de pesos no puede continuar.")
        return {}
    except Exception as e:
        logging.error(f"Error al cargar o procesar 'master_weights.yaml': {e}")
        return {}

    # --- PASO 1.5: SUAVIZADO DE PESOS BASE CON RAÍZ CUADRADA ---
    # Se aplica la transformación, pero ya NO se re-normaliza aquí.
    master_weights = {k: math.sqrt(v) for k, v in master_weights.items()}
    
    preferencias = preferencias or {}
    pasajeros_info = info_pasajeros_dict or {}

    # --- PASO 2: Ajuste Dinámico de Pesos Base ---
    dynamic_master_weights = master_weights.copy()
    
    estilo_input = preferencias.get("estilo_conduccion", "TRANQUILO")
    try:
        estilo = EstiloConduccion(estilo_input)
    except (ValueError, NameError):
        estilo = "TRANQUILO"

    style_multipliers = {
        "DEPORTIVO": {
            'deportividad_style_score': 8.0,
            'fav_menor_rel_peso_potencia_score': 2.0,
            'potencia_maxima_style_score': 5.0,
            'par_motor_style_score': 3.5,
            'fav_menor_aceleracion_score': 3.5
        },
        "MIXTO": {
            'deportividad_style_score':4.0,
            'fav_menor_rel_peso_potencia_score': 1.0,
            'potencia_maxima_style_score': 2.0,
            'par_motor_style_score': 2.0,
            'fav_menor_aceleracion_score': 1.5
        }
    }

    current_style_name = estilo.name if hasattr(estilo, 'name') else estilo

    if current_style_name in style_multipliers:
        multipliers_to_apply = style_multipliers[current_style_name]
        for key, boost_value in multipliers_to_apply.items():
            if key in dynamic_master_weights:
                dynamic_master_weights[key] *= boost_value
        
        # --- ELIMINADO ---
        # El bloque de re-normalización que estaba aquí ha sido eliminado.
        # total_boosted_weight = sum(dynamic_master_weights.values()) ...

    # --- PASO 3: Inicialización de Multiplicadores ---
    multiplicadores = {key: 1.0 for key in dynamic_master_weights.keys()}

    # --- PASO 4: Aplicación de Reglas de Negocio (Multiplicadores) ---
    # Esta sección se mantiene igual, aplicando los multiplicadores sobre los pesos ya "boosteados".
    if is_yes(preferencias.get("valora_estetica")): multiplicadores['estetica'] *= 5.0
    if is_yes(preferencias.get("apasionado_motor")):
        multiplicadores['premium'] *= 4.0
        multiplicadores['singular'] *= 2.0
    if is_yes(preferencias.get("prefiere_diseno_exclusivo")): multiplicadores['singular'] *= 7.0
    if is_yes(preferencias.get("prioriza_baja_depreciacion")): multiplicadores['devaluacion'] *= 10.0
    if is_yes(preferencias.get("arrastra_remolque")):
        multiplicadores['par_motor_remolque_score'] *= 10.0
        multiplicadores['cap_remolque_cf_score'] *= 8.0
        multiplicadores['cap_remolque_sf_score'] *=8.0

    if km_anuales_estimados is not None and km_anuales_estimados > 60000:
        multiplicadores['autonomia_uso_maxima'] *= 5.0
        multiplicadores['autonomia_uso_2nd_drive'] *= 5.0
        multiplicadores['menor_tiempo_carga_min'] *= 5.0
        multiplicadores['potencia_maxima_carga_DC'] *= 5.0

    aventura_input = preferencias.get("aventura", "ninguna")
    aventura_map = {"ocasional": 2.5, "extrema": 5.0}
    multiplicadores['altura_libre_suelo'] *= aventura_map.get(aventura_input, 1.0)

    if is_yes(preferencias.get("altura_mayor_190")):
        multiplicadores['batalla'] *= 5.0
        multiplicadores['indice_altura_interior'] *= 10.0
   
    frecuencia_pasajeros = pasajeros_info.get("frecuencia_viaje_con_acompanantes")
    num_ninos_silla = pasajeros_info.get("num_ninos_silla", 0)
    num_otros_pasajeros = pasajeros_info.get("num_otros_pasajeros", 0)
    if frecuencia_pasajeros == "frecuente" and num_otros_pasajeros >= 2:
        multiplicadores['ancho'] *= 3.0
    elif frecuencia_pasajeros == "ocasional" and (num_ninos_silla + num_otros_pasajeros) >= 2:
        multiplicadores['ancho'] *= 2.0
        
    if is_yes(preferencias.get("transporta_carga_voluminosa")):
        multiplicadores['maletero_minimo_score'] *= 10.0 #15
        multiplicadores['maletero_maximo_score'] *= 7.0 #10
        if is_yes(preferencias.get("necesita_espacio_objetos_especiales")):
            multiplicadores['largo_vehiculo_score'] *= 7.0 #10
            multiplicadores['ancho'] *= 3.5 #5

    if is_yes(preferencias.get("circula_principalmente_ciudad")):
        multiplicadores['fav_menor_diametro_giro'] *= 3.0
    
    if preferencias.get("tiene_garage") is not None:
        if not is_yes(preferencias.get("tiene_garage")): # No tiene garaje
            if is_yes(preferencias.get("problemas_aparcar_calle")):
                multiplicadores['fav_menor_superficie_planta'] *= 10.0
                
        else: # Sí tiene garaje
            if not is_yes(preferencias.get("espacio_sobra_garage")):
                print("DEBUG (Garaje) ► Detectado: 'espacio_sobra_garage' es NO.")
                multiplicadores['fav_menor_diametro_giro'] *= 2.5
                
                # Obtenemos la lista de Enums
                problema_dim = preferencias.get("problema_dimension_garage") or []
                # --- Prints para depuración ---
                print(f"DEBUG (Garaje) ► Valor de 'problema_dimension_garage': {problema_dim}")
                if problema_dim:
                    if DimensionProblematica.LARGO in problema_dim:
                        print("DEBUG (Garaje) ► ¡CONDICIÓN LARGO CUMPLIDA! Aplicando multiplicador.")
                        multiplicadores['fav_menor_largo_garage'] *= 7.0
                    if DimensionProblematica.ANCHO in problema_dim:
                        print("DEBUG (Garaje) ► ¡CONDICIÓN ANCHO CUMPLIDA! Aplicando multiplicador.")
                        multiplicadores['fav_menor_ancho_garage'] *= 7.0
                    if DimensionProblematica.ALTO in problema_dim:
                        print("DEBUG (Garaje) ► ¡CONDICIÓN ALTO CUMPLIDA! Aplicando multiplicador.")
                        multiplicadores['fav_menor_alto_garage'] *= 7.0
    
    if es_zona_nieblas:
        multiplicadores['rating_seguridad'] *= 2.5

    # --- PASO 5: Cálculo de Pesos Crudos Finales ---
    # El nombre 'raw_weights' ahora es más preciso que nunca.
    raw_weights = {
        key: dynamic_master_weights.get(key, 0.0) * multiplicadores.get(key, 1.0)
        for key in dynamic_master_weights
    }
    
    # --- PASO 7: Clamping Final ---
    # El clamping sigue siendo útil para evitar valores crudos absurdamente altos
    # antes de la normalización externa.
    MAX_SINGLE_RAW_WEIGHT = 100.0 # Se puede ajustar este límite si es necesario
    final_raw_weights = {
        key: max(0.0, min(value, MAX_SINGLE_RAW_WEIGHT))
        for key, value in raw_weights.items()
    }
    
    logging.debug(f"Pesos Crudos Finales (Sin Normalizar): {final_raw_weights}")
    print(f"DEBUG (compute_raw_weights) ►► Pesos Crudos Finales (listos para normalizar): {final_raw_weights}")
    
    return final_raw_weights




# normalize_weights se mantiene igual (quizás con el DEBUG print que añadí antes)
def normalize_weights(raw_weights: dict) -> dict:
    """Normaliza los pesos crudos para que sumen 1.0."""
    valid_values = [v for v in raw_weights.values() if isinstance(v, (int, float))]
    total = sum(valid_values) or 1.0 
    logging.info(f"DEBUG (Weights) ► ► Suma Pesos Crudos: {total}")
    normalized = {k: (v / total) if isinstance(v, (int, float)) else 0.0 for k, v in raw_weights.items()}
    print(f"DEBUG (Normalize Weights) ► Pesos Normalizados: {normalized}")
    return normalized


