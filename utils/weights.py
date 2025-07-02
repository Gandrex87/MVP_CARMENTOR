# utils/weights.py
from typing import Optional, Dict, Any # Añadir tipos
from .conversion import is_yes
import yaml
import logging
from .enums import NivelAventura , FrecuenciaUso, DistanciaTrayecto
from graph.perfil.state import PerfilUsuario # Importar para type hint
from config.settings import (altura_map, MIN_SINGLE_RAW_WEIGHT, MAX_SINGLE_RAW_WEIGHT, AJUSTE_CRUDO_SEGURIDAD_POR_NIEBLA , PESO_CRUDO_FAV_MENOR_SUPERFICIE, PESO_CRUDO_FAV_MENOR_DIAMETRO_GIRO, PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE, UMBRAL_RATING_IMPACTO_PARA_FAV_PESO_CONSUMO, UMBRAL_RATING_COSTES_USO_PARA_FAV_CONSUMO_COSTES, UMBRAL_RATING_COMODIDAD_PARA_FAVORECER, RAW_WEIGHT_BONUS_FIABILIDAD_POR_IMPACTO,
                            RAW_WEIGHT_ADICIONAL_FAV_BAJO_PESO_POR_IMPACTO, RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_IMPACTO, RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_COSTES, RAW_WEIGHT_FAV_BAJO_COSTE_USO_DIRECTO, RAW_WEIGHT_FAV_BAJO_COSTE_MANTENIMIENTO_DIRECTO,
                            RAW_PESO_DEPORTIVIDAD_ALTO, RAW_PESO_MENOR_REL_PESO_POTENCIA_ALTO, RAW_PESO_POTENCIA_MAXIMA_ALTO, RAW_PESO_PAR_MOTOR_DEPORTIVO_ALTO, RAW_PESO_MENOR_ACELERACION_ALTO,
                            RAW_PESO_DEPORTIVIDAD_MEDIO, RAW_PESO_MENOR_REL_PESO_POTENCIA_MEDIO, RAW_PESO_POTENCIA_MAXIMA_MEDIO, RAW_PESO_PAR_MOTOR_DEPORTIVO_MEDIO, RAW_PESO_MENOR_ACELERACION_MEDIO,
                            RAW_PESO_DEPORTIVIDAD_BAJO, RAW_PESO_MENOR_REL_PESO_POTENCIA_BAJO, RAW_PESO_POTENCIA_MAXIMA_BAJO, RAW_PESO_PAR_MOTOR_DEPORTIVO_BAJO, RAW_PESO_MENOR_ACELERACION_BAJO,
                            RAW_PESO_PAR_MOTOR_REMOLQUE, RAW_PESO_CAP_REMOLQUE_CF, RAW_PESO_CAP_REMOLQUE_SF, RAW_WEIGHT_ADICIONAL_FAV_IND_ALTURA_INT_POR_COMODIDAD, RAW_WEIGHT_ADICIONAL_FAV_AUTONOMIA_VEHI_POR_COMODIDAD,
                            PESO_CRUDO_FAV_MALETERO_MAX, PESO_CRUDO_FAV_MALETERO_MIN, PESO_CRUDO_FAV_BATALLA_ALTURA_MAYOR_190, PESO_CRUDO_FAV_IND_ALTURA_INT_ALTURA_MAYOR_190,PESO_CRUDO_FAV_ANCHO_PASAJEROS_OCASIONAL, PESO_CRUDO_FAV_ANCHO_PASAJEROS_FRECUENTE , PESO_CRUDO_FAV_DEVALUACION,
                            RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_USO_INTENSIVO, WEIGHT_AUTONOMIA_PRINCIPAL_MUY_ALTO_KM,WEIGHT_AUTONOMIA_2ND_DRIVE_MUY_ALTO_KM, WEIGHT_TIEMPO_CARGA_MIN_MUY_ALTO_KM, PESO_CRUDO_FAV_SINGULAR_PREF_DISENO_EXCLUSIVO,
                            WEIGHT_POTENCIA_DC_MUY_ALTO_KM,PESO_CRUDO_FAV_ESTETICA , PESO_CRUDO_FAV_PREMIUM_APASIONADO_MOTOR, PESO_CRUDO_FAV_SINGULAR_APASIONADO_MOTOR,PESO_CRUDO_FAV_DIAMETRO_GIRO_CONDUC_CIUDAD, PESO_CRUDO_BASE, 
                            PESO_CRUDO_FAV_MALETERO_ESP_OBJ_ESPECIALES_ANCHO ,PESO_CRUDO_FAV_MALETERO_ESP_OBJ_ESPECIALES_LARGO, RAW_WEIGHT_BONUS_DURABILIDAD_POR_IMPACTO
                            )
# --- Configuración de Logging ---
logger = logging.getLogger(__name__) 

# # --- Función compute_raw_weights FUNCIONAL V1 ---
# def compute_raw_weights(
#     preferencias: Optional[PerfilUsuario], # <-- Cambiar Type Hint a PerfilUsuario
#     info_pasajeros_dict: Optional[Dict[str, Any]],
#     es_zona_nieblas: bool = False,
#     km_anuales_estimados: Optional[int] = None,
#     ) -> Dict[str, float]: 
#     """
#     Calcula pesos crudos. Accede a preferencias usando notación de punto.
#     """
#     raw = {} # Inicializar el diccionario de pesos crudos
#     pasajeros_info = info_pasajeros_dict if info_pasajeros_dict else {}
    
#     # Estética (basado en valora_estetica)
#     # Si el usuario valora la estética, "¿Es importante para ti el diseño y la estética del coche, o hay otros factores que priorizas más?"
#     raw["estetica"] = PESO_CRUDO_FAV_ESTETICA if is_yes(preferencias.get("valora_estetica")) else PESO_CRUDO_BASE
#     logging.debug(f"Weights: Peso crudo para 'estetica' basado en valora_estetica='{preferencias.get('valora_estetica')}': {raw['estetica']}")

#     # Premium (basado en apasionado_motor)
#     # Si es un apasionado del motor, favorecemos coches con carácter premium.
#     raw["premium"] = PESO_CRUDO_FAV_PREMIUM_APASIONADO_MOTOR if is_yes(preferencias.get("apasionado_motor")) else PESO_CRUDO_BASE # Base para no apasionado
#     logging.debug(f"Weights: Peso crudo para 'premium' basado en apasionado_motor='{preferencias.get('apasionado_motor')}': {raw['premium']}")
    
#     # Singularidad (Aditiva)
#     singular_raw_weight = 1.0
#     # Contribución de apasionado_motor
#     if is_yes(preferencias.get("apasionado_motor")):
#         singular_raw_weight += PESO_CRUDO_FAV_SINGULAR_APASIONADO_MOTOR
#     else: # 'no' o None (False)
#         singular_raw_weight += 0.0 
#     # Contribución prefiere_diseno_exclusivo:¿te inclinas más por un diseño exclusivo, o prefieres algo más discreto y convencional?"
#     if is_yes(preferencias.get("prefiere_diseno_exclusivo")):
#         singular_raw_weight += PESO_CRUDO_FAV_SINGULAR_PREF_DISENO_EXCLUSIVO
#     else: # 'no' o None (False)
#         singular_raw_weight += 0.0 # Un peso base bajo si no le importa la exclusividad
        
#     raw["singular"] = singular_raw_weight
#     logging.debug(f"Weights: Peso crudo para 'singular': +{raw['singular']}")
    
#     raw['autonomia_uso_principal'] = PESO_CRUDO_BASE
#     raw['autonomia_uso_2nd_drive'] = PESO_CRUDO_BASE
#     raw['menor_tiempo_carga_min'] = PESO_CRUDO_BASE
#     raw['potencia_maxima_carga_AC'] = PESO_CRUDO_BASE
#     raw['potencia_maxima_carga_DC'] = PESO_CRUDO_BASE
    
#      # ---  2. AÑADIR NUEVA LÓGICA PARA "GRAN VIAJERO" ---
#     if km_anuales_estimados is not None and km_anuales_estimados > 60000:
#         logging.info(f"DEBUG (Weights) ► Perfil 'Gran Viajero' detectado ({km_anuales_estimados} km/año). Añadiendo pesos crudos para autonomía y carga.")
#         # Añadimos estos factores como si fueran preferencias más del usuario
#         raw['autonomia_uso_principal'] = WEIGHT_AUTONOMIA_PRINCIPAL_MUY_ALTO_KM
#         raw['autonomia_uso_2nd_drive'] = WEIGHT_AUTONOMIA_2ND_DRIVE_MUY_ALTO_KM
#         raw['menor_tiempo_carga_min'] = WEIGHT_TIEMPO_CARGA_MIN_MUY_ALTO_KM
#         raw['potencia_maxima_carga_AC'] = PESO_CRUDO_BASE
#         raw['potencia_maxima_carga_DC'] = WEIGHT_POTENCIA_DC_MUY_ALTO_KM

#     # 1. Pesos de Aventura
#     # Obtener el valor de aventura del perfil de usuario.
#     aventura_val = preferencias.get("aventura")
#     # Asignar el peso usando el mapa. Si aventura_val es None o no existe,
#     raw["altura_libre_suelo"] = altura_map.get(aventura_val, 1.0)
#     print(f"DEBUG (Weights) ► Peso crudo para altura_libre_suelo (por aventura='{aventura_val}'): {raw['altura_libre_suelo']}")

#     # 2. Pesos basados en altura_mayor_190
#     altura_pref_val = preferencias.get("altura_mayor_190") if preferencias else None # <-- USO DE .get()
#     if is_yes(altura_pref_val):
#         print("DEBUG (Weights) ► Usuario alto. Asignando pesos a batalla/índice.")
#         raw["batalla"] = PESO_CRUDO_FAV_BATALLA_ALTURA_MAYOR_190 
#         raw["indice_altura_interior"] = PESO_CRUDO_FAV_IND_ALTURA_INT_ALTURA_MAYOR_190
#     else:
#         print("DEBUG (Weights) ► Usuario NO alto. Asignando pesos bajos a batalla/índice.")
#         raw["batalla"] = PESO_CRUDO_BASE
#         raw["indice_altura_interior"] = PESO_CRUDO_BASE
#     print(f"DEBUG (Weights) ► Pesos crudos tras añadir dims por altura: {raw}")
    
#     # --- 3. LÓGICA MODIFICADA PARA 'ancho' BASADA EN PASAJEROS ---
#     raw["ancho"] = PESO_CRUDO_BASE
#     frecuencia_pasajeros = pasajeros_info.get("frecuencia")
#     num_ninos_silla_X = pasajeros_info.get("num_ninos_silla", 0)
#     num_otros_pasajeros_Z = pasajeros_info.get("num_otros_pasajeros", 0)
    
#     # Caso 1: Viaje frecuente con 2 o más pasajeros que NO usan silla
#     if frecuencia_pasajeros == "frecuente" and num_otros_pasajeros_Z >= 2:
#         raw["ancho"] += PESO_CRUDO_FAV_ANCHO_PASAJEROS_FRECUENTE # Asigna 8.0
#         logging.info(f"DEBUG (Weights) ► Priorizando ANCHO: viaje frecuente con Z={num_otros_pasajeros_Z} >= 2.")
        
#     # Caso 2: Viaje ocasional (el ancho es importante si el total de pasajeros es 2 o más (X+Z >=2), no solo si son dos adultos.)
#     elif frecuencia_pasajeros == "ocasional" and (num_ninos_silla_X + num_otros_pasajeros_Z) >= 2:
#         raw["ancho"] += PESO_CRUDO_FAV_ANCHO_PASAJEROS_OCASIONAL #Asigna 4.0
#         logging.info(f"Weights: Priorizando ANCHO moderadamente por viaje ocasional con X+Z={(num_ninos_silla_X + num_otros_pasajeros_Z)} >= 2.")
    
#     # Si no se cumple ninguna de las condiciones anteriores, el peso se queda en su valor base (1.0)
#     else:
#         logging.debug(f"Weights: No se cumplen condiciones para priorizar ancho por pasajeros (frecuencia='{frecuencia_pasajeros}'). ancho se mantiene en {raw['ancho']}")
     
#     # 4. --- NUEVO PESO CRUDO PARA DEPRECIACIÓN ---
#     if is_yes(preferencias.get("prioriza_baja_depreciacion")):
#         raw["devaluacion"] = PESO_CRUDO_FAV_DEVALUACION
#     else: # 'no' o None
#         raw["devaluacion"] = PESO_CRUDO_BASE
#     print(f"DEBUG (Weights) ► Peso crudo para devaluacion (basado en prioriza_baja_depreciacion='{preferencias.get('prioriza_baja_depreciacion')}'): {raw['devaluacion']}")

#     # 5. Añadir pesos crudos directamente de los ratings del usuario    
#     if preferencias: # Verificar si el diccionario preferencias existe
#         raw["rating_durabilidad"] = float(preferencias.get("rating_fiabilidad_durabilidad") or 0.0)
#         raw["rating_fiabilidad"] = float(preferencias.get("rating_fiabilidad_durabilidad") or 0.0)
#         raw["rating_seguridad"] = float(preferencias.get("rating_seguridad") or 0.0)
#         #raw["rating_comodidad"] = float(preferencias.get("rating_comodidad") or 0.0)
#        # raw["rating_costes_uso"] = float(preferencias.get("rating_costes_uso") or 0.0)
#         raw["rating_tecnologia_conectividad"] = float(preferencias.get("rating_tecnologia_conectividad") or 0.0)
#     else: # Si preferencias es None, poner defaults para los ratings
#         raw["rating_durabilidad"] = PESO_CRUDO_BASE
#         raw["rating_fiabilidad"] = PESO_CRUDO_BASE
#         raw["rating_seguridad"] = PESO_CRUDO_BASE
#         raw["rating_comodidad"] = PESO_CRUDO_BASE
#         #raw["rating_costes_uso"] = PESO_CRUDO_BASE
#         raw["rating_tecnologia_conectividad"] = PESO_CRUDO_BASE
        
#     # --- NUEVA LÓGICA PARA PESOS DE CARGA Y ESPACIO ---
#     # Inicializar pesos crudos para las nuevas características BQ que se ponderarán
#     raw["maletero_minimo_score"] = PESO_CRUDO_BASE  # Un peso base bajo si no se necesita carga
#     raw["maletero_maximo_score"] = PESO_CRUDO_BASE # Un peso base bajo
#     raw["largo_vehiculo_score"] = PESO_CRUDO_BASE   # Un peso base bajo
    

#     if is_yes(preferencias.get("transporta_carga_voluminosa")):
#         # Si transporta carga voluminosa, aumentamos la importancia de las columnas de maletero
#         raw["maletero_minimo_score"] = PESO_CRUDO_FAV_MALETERO_MIN
#         raw["maletero_maximo_score"] = PESO_CRUDO_FAV_MALETERO_MAX
#         print(f"DEBUG (Weights) ► transporta_carga_voluminosa='sí'. Pesos crudos para maletero: {raw['maletero_minimo_score']}/{raw['maletero_maximo_score']}")

#         if is_yes(preferencias.get("necesita_espacio_objetos_especiales")):
#             # Si además necesita espacio para objetos especiales, aumentamos la importancia de largo y ancho
#             raw["largo_vehiculo_score"] = PESO_CRUDO_FAV_MALETERO_ESP_OBJ_ESPECIALES_LARGO
#             raw["ancho"] += PESO_CRUDO_FAV_MALETERO_ESP_OBJ_ESPECIALES_ANCHO # suma 5 puntos
#             print(f"DEBUG (Weights) ► necesita_espacio_objetos_especiales='sí'. Pesos crudos para largo: {raw['largo_vehiculo_score']}, ancho actualizado a: {raw['ancho']}")
    
#     # --- Favorecer índice_altura y autonomia_uso_maxima si comodidad es alta ---
#     rating_comodidad_val = preferencias.get("rating_comodidad")
#     # Inicializar peso para autonomía (nueva característica a ponderar)
#     raw["autonomia_uso_maxima"] = PESO_CRUDO_BASE
#     if rating_comodidad_val is not None and rating_comodidad_val >= UMBRAL_RATING_COMODIDAD_PARA_FAVORECER:
#         print(f"DEBUG (Weights) ► Comodidad alta ({rating_comodidad_val}). Aumentando pesos para índice_altura y autonomia_uso_maxima.")
#         # Aumentar el peso de indice_altura_interior. 
#         # Podemos sumarle al existente o establecer un valor alto. Sumar es más flexible.
#         raw["indice_altura_interior"] = raw.get("indice_altura_interior", PESO_CRUDO_BASE) + RAW_WEIGHT_ADICIONAL_FAV_IND_ALTURA_INT_POR_COMODIDAD 
#         # Asignar un peso crudo alto a la autonomía
#         raw["autonomia_uso_maxima"] = RAW_WEIGHT_ADICIONAL_FAV_AUTONOMIA_VEHI_POR_COMODIDAD 
    
#     # Pesos específicos para bajo peso y bajo consumo, activados por alto rating de impacto ambiental
#     raw["fav_bajo_peso"] = PESO_CRUDO_BASE # Default
#     raw["fav_bajo_consumo"] = PESO_CRUDO_BASE # Default
    
#     rating_ia = preferencias.get("rating_impacto_ambiental")
#     if rating_ia is not None and rating_ia >= UMBRAL_RATING_IMPACTO_PARA_FAV_PESO_CONSUMO:
#         logging.info(f"DEBUG (Weights) ► Impacto Ambiental alto ({rating_ia}). Activando bonus para eficiencia, fiabilidad y durabilidad.")
#         raw["fav_bajo_peso"] += RAW_WEIGHT_ADICIONAL_FAV_BAJO_PESO_POR_IMPACTO
#         raw["fav_bajo_consumo"] += RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_IMPACTO       
#         # Nos aseguramos de que el peso base ya exista antes de sumar
#         raw["rating_fiabilidad"] = raw.get("rating_fiabilidad", 0.0) + RAW_WEIGHT_BONUS_FIABILIDAD_POR_IMPACTO
#         raw["rating_durabilidad"] = raw.get("rating_durabilidad", 0.0) + RAW_WEIGHT_BONUS_DURABILIDAD_POR_IMPACTO
        
#     # --- NUEVA LÓGICA PARA rating_costes_uso ---
#     raw["rating_costes_uso"] = float(preferencias.get("rating_costes_uso") or PESO_CRUDO_BASE) # Peso directo para el concepto general
    
#     # Pesos específicos para bajo coste de uso, bajo coste de mantenimiento, y bajo consumo / activados por alto rating_costes_uso
#     raw["fav_bajo_coste_uso_directo"] = PESO_CRUDO_BASE
#     raw["fav_bajo_coste_mantenimiento_directo"] = PESO_CRUDO_BASE
    
#     rating_cu = preferencias.get("rating_costes_uso")
#     if rating_cu is not None and rating_cu >= UMBRAL_RATING_COSTES_USO_PARA_FAV_CONSUMO_COSTES:
#         print(f"DEBUG (Weights) ► Costes de Uso alto ({rating_cu}). Activando pesos para bajo consumo, bajo coste uso y mantenimiento.")
#         raw["fav_bajo_consumo"] += RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_COSTES #
#         raw["fav_bajo_coste_uso_directo"] = RAW_WEIGHT_FAV_BAJO_COSTE_USO_DIRECTO    # 
#         raw["fav_bajo_coste_mantenimiento_directo"] = RAW_WEIGHT_FAV_BAJO_COSTE_MANTENIMIENTO_DIRECTO 
    
#     # --- NUEVA LÓGICA DE USO INTENSIVO ---
#     frecuencia_val = preferencias.get("frecuencia_uso")
#     distancia_val = preferencias.get("distancia_trayecto")
    
#     # Comprobamos si las condiciones de uso intensivo se cumplen
#     es_uso_frecuente = frecuencia_val in [FrecuenciaUso.DIARIO.value, FrecuenciaUso.FRECUENTEMENTE.value]
#     es_trayecto_largo = distancia_val in [DistanciaTrayecto.ENTRE_51_Y_150_KM.value, DistanciaTrayecto.MAS_150_KM.value]
    
#     if es_uso_frecuente and es_trayecto_largo:
#         print(f"DEBUG (Weights) ► Uso intensivo detectado (frecuencia='{frecuencia_val}', distancia='{distancia_val}'). Aumentando peso para bajo consumo.")
#         raw["fav_bajo_consumo"] += RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_USO_INTENSIVO

#     # --- LÓGICA PARA PESOS DE ARRASTRE DE REMOLQUE ---
#     # Usaremos claves distintas para estos pesos para que sean específicos
#     raw["par_motor_remolque_score"] = PESO_CRUDO_BASE # Peso base muy bajo si no arrastra
#     raw["cap_remolque_cf_score"] = PESO_CRUDO_BASE   # Capacidad remolque con freno
#     raw["cap_remolque_sf_score"] = PESO_CRUDO_BASE   # Capacidad remolque sin freno

#     if is_yes(preferencias.get("arrastra_remolque")):
#         raw["par_motor_remolque_score"] = RAW_PESO_PAR_MOTOR_REMOLQUE
#         raw["cap_remolque_cf_score"] = RAW_PESO_CAP_REMOLQUE_CF
#         raw["cap_remolque_sf_score"] = RAW_PESO_CAP_REMOLQUE_SF
#         print(f"DEBUG (Weights) ► Usuario arrastra remolque. Aplicando pesos específicos: par_motor_remolque_score ={raw['par_motor_remolque_score']}, cap_remolque_cf_score ={raw['cap_remolque_cf_score']}, cap_remolque_sf_score ={raw['cap_remolque_sf_score']}.")
        
#     # --- NUEVA LÓGICA PARA AJUSTAR PESOS POR CLIMA ---
#     # 6. Ajustar pesos basados en información climática
#     raw["rating_seguridad"] = raw.get("rating_seguridad", 0.0)  # Aseguramos que las claves existan antes de sumarles
#     current_seguridad_rating = raw.get("rating_seguridad", 0.0) # Obtener el peso base del rating
#     if es_zona_nieblas:
#         current_seguridad_rating += AJUSTE_CRUDO_SEGURIDAD_POR_NIEBLA
#     raw["rating_seguridad"] = current_seguridad_rating
#     print(f"DEBUG (Weights) ► Zona Nieblas ({es_zona_nieblas}): Peso crudo final rating_seguridad = {raw['rating_seguridad']}")
    
#     # Tracción por Nieve y Montaña
#     # --- LÓGICA PARA PESOS DE GARAJE/APARCAMIENTO ---
#     # Inicializar los nuevos pesos con un valor base bajo
#     raw["fav_menor_superficie_planta"] = PESO_CRUDO_BASE 
#     raw["fav_menor_diametro_giro"] = PESO_CRUDO_BASE
#     raw["fav_menor_largo_garage"] = PESO_CRUDO_BASE 
#     raw["fav_menor_ancho_garage"] = PESO_CRUDO_BASE 
#     raw["fav_menor_alto_garage"] = PESO_CRUDO_BASE  

#     # circula principalmente por ciudad / si"
#     if is_yes(preferencias.get("circula_principalmente_ciudad")):
#         raw['fav_menor_diametro_giro'] += PESO_CRUDO_FAV_DIAMETRO_GIRO_CONDUC_CIUDAD
#         logging.info("Weights: Aumentando peso para diámetro de giro por conducción urbana.")
    
#     # 2. Ajustes por situación de aparcamiento
#     tiene_garage_val = preferencias.get("tiene_garage")
#     if tiene_garage_val is not None:
#         if not is_yes(tiene_garage_val): # NO tiene garaje
#             if is_yes(preferencias.get("problemas_aparcar_calle")):
#                 raw["fav_menor_superficie_planta"] += PESO_CRUDO_FAV_MENOR_SUPERFICIE
#                 logging.info("Weights: Aumentando peso para superficie por problemas al aparcar.")
#                 print(f"DEBUG (Weights) ► Problemas aparcar calle. Favoreciendo menor superficie_planta con peso: {PESO_CRUDO_FAV_MENOR_SUPERFICIE}")
#         else: # SÍ tiene garaje
#             if not is_yes(preferencias.get("espacio_sobra_garage")): # Espacio NO sobra
#                 # Se suma al peso base, no lo reemplaza
#                 raw["fav_menor_diametro_giro"] += PESO_CRUDO_FAV_MENOR_DIAMETRO_GIRO
#                 logging.info("Weights: Aumentando peso para diámetro de giro por garaje ajustado.")
                
#                 problema_dimension_lista = preferencias.get("problema_dimension_garage", [])
#                 if isinstance(problema_dimension_lista, list):
#                     if "largo" in problema_dimension_lista:
#                         raw["fav_menor_largo_garage"] += PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE
#                         print(f"DEBUG (Weights) ► Problema LARGO en garaje. Favoreciendo menor largo con peso: {PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE}")
#                     if "ancho" in problema_dimension_lista:
#                         raw["fav_menor_ancho_garage"] += PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE
#                         print(f"DEBUG (Weights) ► Problema ANCHO en garaje. Favoreciendo menor ancho con peso: {PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE}")
#                     if "alto" in problema_dimension_lista:
#                         raw["fav_menor_alto_garage"] += PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE
#                         print(f"DEBUG (Weights) ► Problema ALTO en garaje. Favoreciendo menor alto con peso: {PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE}")
    
#     # --- NUEVA LÓGICA PARA PESOS DE ESTILO DE CONDUCCIÓN ---
#     estilo_conduccion_val_str = None
#     estilo_conduccion_input = preferencias.get("estilo_conduccion")
#     if hasattr(estilo_conduccion_input, "value"): # Si es Enum
#         estilo_conduccion_val_str = estilo_conduccion_input.value 
#     elif isinstance(estilo_conduccion_input, str): # Si ya es string
#         estilo_conduccion_val_str = estilo_conduccion_input.lower()

#     if estilo_conduccion_val_str == "deportivo":
#         print(f"DEBUG (Weights) ► Estilo Conducción 'deportivo'. Aplicando pesos altos de deportividad.")
#         raw["deportividad_style_score"] = RAW_PESO_DEPORTIVIDAD_ALTO
#         raw["fav_menor_rel_peso_potencia_score"] = RAW_PESO_MENOR_REL_PESO_POTENCIA_ALTO
#         raw["potencia_maxima_style_score"] = RAW_PESO_POTENCIA_MAXIMA_ALTO
#         raw["par_motor_style_score"] = RAW_PESO_PAR_MOTOR_DEPORTIVO_ALTO
#         raw["fav_menor_aceleracion_score"] = RAW_PESO_MENOR_ACELERACION_ALTO
#     elif estilo_conduccion_val_str == "mixto":
#         print(f"DEBUG (Weights) ► Estilo Conducción 'mixto'. Aplicando pesos medios de deportividad.")
#         raw["deportividad_style_score"] = RAW_PESO_DEPORTIVIDAD_MEDIO
#         raw["fav_menor_rel_peso_potencia_score"] = RAW_PESO_MENOR_REL_PESO_POTENCIA_MEDIO
#         raw["potencia_maxima_style_score"] = RAW_PESO_POTENCIA_MAXIMA_MEDIO
#         raw["par_motor_style_score"] = RAW_PESO_PAR_MOTOR_DEPORTIVO_MEDIO
#         raw["fav_menor_aceleracion_score"] = RAW_PESO_MENOR_ACELERACION_MEDIO
#     else: # "tranquilo" o None
#         print(f"DEBUG (Weights) ► Estilo Conducción 'tranquilo' o no definido. Aplicando pesos bajos de deportividad.")
#         raw["deportividad_style_score"] = RAW_PESO_DEPORTIVIDAD_BAJO
#         raw["fav_menor_rel_peso_potencia_score"] = RAW_PESO_MENOR_REL_PESO_POTENCIA_BAJO
#         raw["potencia_maxima_style_score"] = RAW_PESO_POTENCIA_MAXIMA_BAJO
#         raw["par_motor_style_score"] = RAW_PESO_PAR_MOTOR_DEPORTIVO_BAJO
#         raw["fav_menor_aceleracion_score"] = RAW_PESO_MENOR_ACELERACION_BAJO

#      # Clamp final para todos los pesos que podrían haberse acumulado
#     for key in list(raw.keys()): # Iterar sobre una copia de las claves si modificas el dict
#         if isinstance(raw[key], (int, float)): # Solo clampear números
#             raw[key] = max(MIN_SINGLE_RAW_WEIGHT, min(MAX_SINGLE_RAW_WEIGHT, raw[key]))
#     print(f"DEBUG (Weights) ► Pesos crudos tras añadir ratings: {raw}")
#     raw_float = {k: float(v or 0.0) for k, v in raw.items()}
#     #print(f"DEBUG (Weights) ► Pesos Crudos FINALES: {raw_float}")
#     #logging.info(f"DEBUG (Weights) ► ► Pesos Crudos FINALES: {raw_float}")
#     return raw_float
    

def compute_raw_weights(
    preferencias: Optional[Dict[str, Any]],
    info_pasajeros_dict: Optional[Dict[str, Any]],
    es_zona_nieblas: bool = False,
    km_anuales_estimados: Optional[int] = None,
) -> Dict[str, float]:
    """
    Calcula los pesos crudos para la recomendación de un vehículo usando la
    arquitectura "Genoma + Multiplicadores".

    Esta versión final integra todas las reglas de negocio, manejando los ratings
    de usuario a través de umbrales para mantener la coherencia del modelo.

    Args:
        preferencias: Diccionario con las preferencias del usuario.
        info_pasajeros_dict: Diccionario con la información de los pasajeros.
        es_zona_nieblas: Flag booleano para clima con niebla.
        km_anuales_estimados: Estimación de los kilómetros anuales del usuario.

    Returns:
        Un diccionario con los pesos crudos finales para cada característica,
        listo para ser normalizado.
    """
    # --- PASO 1: Carga del "Genoma" de Pesos Base ---
    # Carga los pesos base rigurosamente calculados (ej. con BWM).
    # Este fichero es el pilar de la coherencia del sistema.
    try:
        with open('master_weights.yaml', 'r', encoding='utf-8') as f:
            master_weights = yaml.safe_load(f)
    except FileNotFoundError:
        logging.error("ERROR CRÍTICO: No se encontró 'master_weights.yaml'. El cálculo de pesos no puede continuar.")
        return {}

    # --- PASO 2: Inicialización de Multiplicadores ---
    # Cada característica empieza con un multiplicador de 1.0 (sin cambios).
    # Las reglas de negocio modificarán estos valores.
    multiplicadores = {key: 1.0 for key in master_weights.keys()}
    preferencias = preferencias or {}
    pasajeros_info = info_pasajeros_dict or {}

    # --- PASO 3: Aplicación de Reglas de Negocio como Multiplicadores ---

    # --- 3.1: Lógica de Preferencias Directas (Booleanas) ---
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

    # --- 3.2: Lógica de Escenarios de Uso y Contexto ---
    if km_anuales_estimados is not None and km_anuales_estimados > 60000:
        multiplicadores['autonomia_uso_maxima'] *= 9.0
        multiplicadores['autonomia_uso_2nd_drive'] *= 3.0
        multiplicadores['menor_tiempo_carga_min'] *= 9.0
        multiplicadores['potencia_maxima_carga_DC'] *= 9.0

    aventura_map = {"ocasional": 4.0, "extrema": 10.0}
    aventura_val = preferencias.get("aventura", "ninguna")
    multiplicadores['altura_libre_suelo'] *= aventura_map.get(aventura_val, 1.0)

    if is_yes(preferencias.get("altura_mayor_190")):
        multiplicadores['batalla'] *= 5.0
        multiplicadores['indice_altura_interior'] *= 8.0

    # --- 3.3: Lógica Condicional Compleja (Pasajeros, Carga, Garaje) ---
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
                problema_dim = preferencias.get("problema_dimension_garage", [])
                if "largo" in problema_dim: multiplicadores['fav_menor_largo_garage'] *= 8.0
                if "ancho" in problema_dim: multiplicadores['fav_menor_ancho_garage'] *= 8.0
                if "alto" in problema_dim:  multiplicadores['fav_menor_alto_garage'] *= 8.0

    
    # --- 3.5: Lógica de Ratings por Umbrales (Versión Final) ---
    def get_rating_multiplier(rating_val: Optional[float]) -> float:
        """Helper para convertir un rating de 1-10 en un multiplicador."""
        rating_val = rating_val or 0
        if rating_val >= 9: return 9.0  # Prioridad Crítica
        if rating_val >= 7: return 6.0  # Interés Fuerte
        if rating_val >= 5: return 2.0  # Interés Moderado
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

    # --- 3.6: Lógica de Factores Externos ---
    if es_zona_nieblas:
        multiplicadores['rating_seguridad'] *= 1.5 # Amplificador de seguridad por clima

    # --- PASO 4: Cálculo de Pesos Crudos Finales ---
    # Multiplicar el peso base de cada característica por su multiplicador final.
    raw_weights = {
        key: master_weights.get(key, 0.0) * multiplicadores.get(key, 1.0)
        for key in master_weights
    }

# --- PASO 4.5: Aplicar Overrides de Perfil de Comportamiento (LÓGICA CORREGIDA) ---
    # Aquí es donde sobrescribimos los pesos calculados con valores absolutos
    # para definir un "estilo de conducción" de forma contundente.
    estilo = preferencias.get("estilo_conduccion", "tranquilo")
    if estilo == "deportivo":
        logging.info("Aplicando override de perfil DEPORTIVO.")
        raw_weights.update({
            'deportividad_style_score': 4.0,
            'fav_menor_rel_peso_potencia_score': 10.0,
            'potencia_maxima_style_score': 5.0,
            'par_motor_style_score': 4.0,
            'fav_menor_aceleracion_score': 6.0
        })
    elif estilo == "mixto":
        logging.info("Aplicando override de perfil MIXTO.")
        raw_weights.update({
            'deportividad_style_score': 2.0,
            'fav_menor_rel_peso_potencia_score': 5.0,
            'potencia_maxima_style_score': 2.5,
            'par_motor_style_score': 2.0,
            'fav_menor_aceleracion_score': 3.0
        })
    
    logging.debug(f"Pesos Crudos (Antes de Clamping): {raw_weights}")
    print(f"DEBUG (Weights) ► Pesos Crudos (Antes de Clamping): {raw_weights}")


    # --- PASO 5: Clamping (Lógica Corregida) ---
    MAX_SINGLE_RAW_WEIGHT = 10.0
    for key, value in raw_weights.items():
        # El mínimo es el valor base del genoma para esa característica.
        min_weight = master_weights.get(key, 0.0)
        # El valor final es el mayor entre el valor calculado y su propio mínimo,
        # pero nunca superando el máximo global.
        raw_weights[key] = max(min_weight, min(MAX_SINGLE_RAW_WEIGHT, value))

    logging.info("Pesos crudos finales calculados con éxito usando la arquitectura 'Genoma + Multiplicadores'.")
    
    final_weights = {k: float(v or 0.0) for k, v in raw_weights.items()}
    
    # --- PRINT AÑADIDO 2: Para ver los pesos crudos FINALES que se devuelven ---
    logging.debug(f"Pesos Crudos Finales (Después de Clamping): {final_weights}")
    print(f"DEBUG (Weights) ► Pesos Crudos Finales (Después de Clamping): {final_weights}")
    
    return final_weights






# normalize_weights se mantiene igual (quizás con el DEBUG print que añadí antes)
def normalize_weights(raw_weights: dict) -> dict:
    """Normaliza los pesos crudos para que sumen 1.0."""
    valid_values = [v for v in raw_weights.values() if isinstance(v, (int, float))]
    total = sum(valid_values) or 1.0 
    logging.info(f"DEBUG (Weights) ► ► Suma Pesos Crudos: {total}")
    normalized = {k: (v / total) if isinstance(v, (int, float)) else 0.0 for k, v in raw_weights.items()}
    print(f"DEBUG (Normalize Weights) ► Pesos Normalizados: {normalized}")
    return normalized


