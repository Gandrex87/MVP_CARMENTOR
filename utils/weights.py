# utils/weights.py
# cada tuple a la prioridad relativa que quieres en ese nivel de aventura.
# “ninguna”: 0 en todo, porque no te importa nada off-road.
# “ocasional”: priorizas un poco el espacio (altura) y la tracción, pero no las reductoras.
# “extrema”: la tracción y reductoras dominan, y el espacio importa menos en comparación.
# Ademas se refactoriza compute_raw_weights para que trate batalla e indice_altura_interior como preferencias suaves, cuya importancia (peso) dependerá de si el usuario indicó ser alto (altura_mayor_190='sí').

from typing import Optional, Dict, Any # Añadir tipos
from .conversion import is_yes
import logging
from .enums import NivelAventura , FrecuenciaUso, DistanciaTrayecto
from graph.perfil.state import PerfilUsuario # Importar para type hint
from config.settings import (MAX_SINGLE_RAW_WEIGHT , MIN_SINGLE_RAW_WEIGHT , AVENTURA_RAW_WEIGHTS, AJUSTE_CRUDO_SEGURIDAD_POR_NIEBLA , AJUSTE_CRUDO_TRACCION_POR_NIEVE, AJUSTE_CRUDO_TRACCION_POR_MONTA,
                            PESO_CRUDO_FAV_MENOR_SUPERFICIE, PESO_CRUDO_FAV_MENOR_DIAMETRO_GIRO, PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE, PESO_CRUDO_BASE_BAJO_DIMENSIONES_GARAJE,
                            UMBRAL_RATING_IMPACTO_PARA_FAV_PESO_CONSUMO, UMBRAL_RATING_COSTES_USO_PARA_FAV_CONSUMO_COSTES, UMBRAL_RATING_COMODIDAD_PARA_FAVORECER,
                            RAW_WEIGHT_ADICIONAL_FAV_BAJO_PESO_POR_IMPACTO, RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_IMPACTO, RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_COSTES, RAW_WEIGHT_FAV_BAJO_COSTE_USO_DIRECTO, RAW_WEIGHT_FAV_BAJO_COSTE_MANTENIMIENTO_DIRECTO,
                            RAW_PESO_DEPORTIVIDAD_ALTO, RAW_PESO_MENOR_REL_PESO_POTENCIA_ALTO, RAW_PESO_POTENCIA_MAXIMA_ALTO, RAW_PESO_PAR_MOTOR_DEPORTIVO_ALTO, RAW_PESO_MENOR_ACELERACION_ALTO,
                            RAW_PESO_DEPORTIVIDAD_MEDIO, RAW_PESO_MENOR_REL_PESO_POTENCIA_MEDIO, RAW_PESO_POTENCIA_MAXIMA_MEDIO, RAW_PESO_PAR_MOTOR_DEPORTIVO_MEDIO, RAW_PESO_MENOR_ACELERACION_MEDIO,
                            RAW_PESO_DEPORTIVIDAD_BAJO, RAW_PESO_MENOR_REL_PESO_POTENCIA_BAJO, RAW_PESO_POTENCIA_MAXIMA_BAJO, RAW_PESO_PAR_MOTOR_DEPORTIVO_BAJO, RAW_PESO_MENOR_ACELERACION_BAJO,
                            RAW_PESO_PAR_MOTOR_REMOLQUE, RAW_PESO_CAP_REMOLQUE_CF, RAW_PESO_CAP_REMOLQUE_SF, RAW_PESO_BASE_REMOLQUE, RAW_WEIGHT_ADICIONAL_FAV_IND_ALTURA_INT_POR_COMODIDAD, RAW_WEIGHT_ADICIONAL_FAV_AUTONOMIA_VEHI_POR_COMODIDAD,
                            RAW_PESO_BASE_COSTE_USO_DIRECTO, RAW_PESO_BASE_COSTE_MANTENIMIENTO_DIRECTO, PESO_CRUDO_BASE_MALETERO,PESO_CRUDO_FAV_MALETERO_MAX, PESO_CRUDO_FAV_MALETERO_MIN, PESO_CRUDO_FAV_MALETERO_ESP_OBJ_ESPECIALES, RAW_PESO_BASE_AUT_VEHI,
                            PESO_CRUDO_BASE_BATALLA_ALTURA_MAYOR_190, PESO_CRUDO_FAV_BATALLA_ALTURA_MAYOR_190, PESO_CRUDO_BASE_ANCHO_GRAL, PESO_CRUDO_FAV_IND_ALTURA_INT_ALTURA_MAYOR_190,PESO_CRUDO_FAV_ANCHO_PASAJEROS_OCASIONAL, PESO_CRUDO_FAV_ANCHO_PASAJEROS_FRECUENTE , PESO_CRUDO_BASE_DEVALUACION, PESO_CRUDO_FAV_DEVALUACION,
                            RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_USO_INTENSIVO, WEIGHT_AUTONOMIA_PRINCIPAL_MUY_ALTO_KM,WEIGHT_AUTONOMIA_2ND_DRIVE_MUY_ALTO_KM, WEIGHT_TIEMPO_CARGA_MIN_MUY_ALTO_KM, PESO_CRUDO_FAV_SINGULAR_PREF_DISENO_EXCLUSIVO,
                            WEIGHT_POTENCIA_AC_MUY_ALTO_KM, WEIGHT_POTENCIA_DC_MUY_ALTO_KM,PESO_CRUDO_FAV_ESTETICA , PESO_CRUDO_FAV_PREMIUM_APASIONADO_MOTOR, PESO_CRUDO_FAV_SINGULAR_APASIONADO_MOTOR,PESO_CRUDO_FAV_DIAMETRO_GIRO_CONDUC_CIUDAD
                            )

# --- Función compute_raw_weights CORREGIDA ---
def compute_raw_weights(
    preferencias: Optional[PerfilUsuario], # <-- Cambiar Type Hint a PerfilUsuario
    info_pasajeros_dict: Optional[Dict[str, Any]],
    es_zona_nieblas: bool = False,
    es_zona_nieve: bool = False,
    es_zona_clima_monta: bool = False,
    km_anuales_estimados: Optional[int] = None,
    ) -> Dict[str, float]: 
    """
    Calcula pesos crudos. Accede a preferencias usando notación de punto.
    """
    
    raw = {} # Inicializar el diccionario de pesos crudos
    pasajeros_info = info_pasajeros_dict if info_pasajeros_dict else {}
    
   
    # Estética (basado en valora_estetica)
    # Si el usuario valora la estética, "¿Es importante para ti el diseño y la estética del coche, o hay otros factores que priorizas más?"
    raw["estetica"] = PESO_CRUDO_FAV_ESTETICA if is_yes(preferencias.get("valora_estetica")) else 0.0
    logging.debug(f"Weights: Peso crudo para 'estetica' basado en valora_estetica='{preferencias.get('valora_estetica')}': {raw['estetica']}")

    # Premium (basado en apasionado_motor)
    # Si es un apasionado del motor, favorecemos coches con carácter premium.
    raw["premium"] = PESO_CRUDO_FAV_PREMIUM_APASIONADO_MOTOR if is_yes(preferencias.get("apasionado_motor")) else 0.0 # Base para no apasionado
    logging.debug(f"Weights: Peso crudo para 'premium' basado en apasionado_motor='{preferencias.get('apasionado_motor')}': {raw['premium']}")
    
    # Singularidad (Aditiva)
    singular_raw_weight = 0.0
    # Contribución de apasionado_motor
    if is_yes(preferencias.get("apasionado_motor")):
        singular_raw_weight += PESO_CRUDO_FAV_SINGULAR_APASIONADO_MOTOR
    else: # 'no' o None (False)
        singular_raw_weight += 0.0 # Un peso base bajo si no es apasionado

    # Contribución prefiere_diseno_exclusivo:¿te inclinas más por un diseño exclusivo, o prefieres algo más discreto y convencional?"
    if is_yes(preferencias.get("prefiere_diseno_exclusivo")):
        singular_raw_weight += PESO_CRUDO_FAV_SINGULAR_PREF_DISENO_EXCLUSIVO
    else: # 'no' o None (False)
        singular_raw_weight += 0.0 # Un peso base bajo si no le importa la exclusividad
        
    raw["singular"] = singular_raw_weight
    logging.debug(f"Weights: Peso crudo para 'singular' (aditivo): {raw['singular']}")
    # --- FIN NUEVA LÓGICA ---
    
     # ---  2. AÑADIR NUEVA LÓGICA PARA "GRAN VIAJERO" ---
    if km_anuales_estimados is not None and km_anuales_estimados > 60000:
        logging.info(f"DEBUG (Weights) ► Perfil 'Gran Viajero' detectado ({km_anuales_estimados} km/año). Añadiendo pesos crudos para autonomía y carga.")
        # Añadimos estos factores como si fueran preferencias más del usuario
        raw['autonomia_uso_principal'] = WEIGHT_AUTONOMIA_PRINCIPAL_MUY_ALTO_KM
        raw['autonomia_uso_2nd_drive'] = WEIGHT_AUTONOMIA_2ND_DRIVE_MUY_ALTO_KM
        raw['menor_tiempo_carga_min'] = WEIGHT_TIEMPO_CARGA_MIN_MUY_ALTO_KM
        raw['potencia_maxima_carga_AC'] = WEIGHT_POTENCIA_AC_MUY_ALTO_KM
        raw['potencia_maxima_carga_DC'] = WEIGHT_POTENCIA_DC_MUY_ALTO_KM

    
    # 1. Pesos de Aventura
    aventura_level_str = None
    if preferencias: # Verificar si el diccionario preferencias existe
        aventura_level_input = preferencias.get("aventura") # <-- USO DE .get()
        if hasattr(aventura_level_input, "value"): # Por si acaso llega el Enum
            aventura_level_str = aventura_level_input.value
        elif aventura_level_input is not None:
            aventura_level_str = str(aventura_level_input).strip().lower()
        else:
            aventura_level_str = "ninguna" # Default si aventura es None en el dict
    else: # Si preferencias es None
        aventura_level_str = "ninguna" # Default
        
    aventura_weights_map = AVENTURA_RAW_WEIGHTS.get(aventura_level_str, AVENTURA_RAW_WEIGHTS["ninguna"])
    raw["altura_libre_suelo"] = float(aventura_weights_map.get("altura_libre_suelo", 0.0))
    raw["traccion"] = float(aventura_weights_map.get("traccion", 0.0))
    raw["reductoras"] = float(aventura_weights_map.get("reductoras", 0.0))
    print(f"DEBUG (Weights) ► Pesos crudos tras añadir aventura: {raw}")

    # 2. Pesos basados en altura_mayor_190
    altura_pref_val = preferencias.get("altura_mayor_190") if preferencias else None # <-- USO DE .get()
    if is_yes(altura_pref_val):
        print("DEBUG (Weights) ► Usuario alto. Asignando pesos a batalla/índice.")
        raw["batalla"] = PESO_CRUDO_FAV_BATALLA_ALTURA_MAYOR_190 
        raw["indice_altura_interior"] = PESO_CRUDO_FAV_IND_ALTURA_INT_ALTURA_MAYOR_190
    else:
        print("DEBUG (Weights) ► Usuario NO alto. Asignando pesos bajos a batalla/índice.")
        raw["batalla"] = PESO_CRUDO_BASE_BATALLA_ALTURA_MAYOR_190
        raw["indice_altura_interior"] = PESO_CRUDO_BASE_BATALLA_ALTURA_MAYOR_190
    print(f"DEBUG (Weights) ► Pesos crudos tras añadir dims por altura: {raw}")
    
    
    # --- 3. LÓGICA MODIFICADA PARA 'ancho_general_score' BASADA EN PASAJEROS ---
    raw["ancho_general_score"] = PESO_CRUDO_BASE_ANCHO_GRAL # Peso base bajo por defecto para el ancho general
    
    frecuencia_pasajeros = pasajeros_info.get("frecuencia_viaje_con_acompanantes") or pasajeros_info.get("frecuencia")
    num_ninos_silla_X = pasajeros_info.get("num_ninos_silla", 0) # Usamos .get() con default 0
    num_otros_pasajeros_Z = pasajeros_info.get("num_otros_pasajeros", 0) # Usamos .get() con default 0
    total_acompanantes = num_ninos_silla_X + num_otros_pasajeros_Z
    logging.debug(f"Weights: Info pasajeros para ancho_general_score -> frecuencia='{frecuencia_pasajeros}', X={num_ninos_silla_X}, Z={num_otros_pasajeros_Z}, Total Acompañantes={total_acompanantes}")
    print(f"DEBUG (Weights) ► Info pasajeros para ancho_general_score -> frecuencia='{frecuencia_pasajeros}', X={num_ninos_silla_X}, Z={num_otros_pasajeros_Z}, Total Acompañantes={total_acompanantes}")
    # Condición basada en el total de acompañantes y la frecuencia.
    # Solo se prioriza el ancho si la frecuencia NO es "nunca" Y hay al menos 2 acompañantes en total.
    if frecuencia_pasajeros and frecuencia_pasajeros != "nunca" and total_acompanantes >= 2:
        if frecuencia_pasajeros == "ocasional":
            raw["ancho_general_score"] = PESO_CRUDO_FAV_ANCHO_PASAJEROS_OCASIONAL
            logging.debug(f"Weights: Pasajeros ocasionales (Total Acompañantes={total_acompanantes}>=2). ancho_general_score ajustado a {raw['ancho_general_score']}")
        elif frecuencia_pasajeros == "frecuente":
            raw["ancho_general_score"] = PESO_CRUDO_FAV_ANCHO_PASAJEROS_FRECUENTE
            logging.debug(f"Weights: Pasajeros frecuentes (Total Acompañantes={total_acompanantes}>=2). ancho_general_score ajustado a {raw['ancho_general_score']}")
    else:
        # Este else es para cuando no se cumplen las condiciones para aumentar el peso del ancho.
        # El peso ya se inicializó a PESO_CRUDO_BASE_ANCHO_GRAL.
        logging.debug(f"Weights: No se cumplen condiciones para priorizar ancho por pasajeros (frecuencia='{frecuencia_pasajeros}', total_acompanantes={total_acompanantes}). ancho_general_score se mantiene en {raw['ancho_general_score']}")
    # --- FIN LÓGICA CORREGIDA ANCHO ---
        
    # 4. --- NUEVO PESO CRUDO PARA DEPRECIACIÓN ---
    if is_yes(preferencias.get("prioriza_baja_depreciacion")):
        raw["devaluacion"] = PESO_CRUDO_FAV_DEVALUACION
    else: # 'no' o None
        raw["devaluacion"] = PESO_CRUDO_BASE_DEVALUACION
    print(f"DEBUG (Weights) ► Peso crudo para devaluacion (basado en prioriza_baja_depreciacion='{preferencias.get('prioriza_baja_depreciacion')}'): {raw['devaluacion']}")

    # 5. Añadir pesos crudos directamente de los ratings del usuario    
    # Añadir pesos crudos directamente de los ratings del usuario
    if preferencias: # Verificar si el diccionario preferencias existe
        raw["rating_fiabilidad_durabilidad"] = float(preferencias.get("rating_fiabilidad_durabilidad") or 0.0)
        raw["rating_seguridad"] = float(preferencias.get("rating_seguridad") or 0.0)
        raw["rating_comodidad"] = float(preferencias.get("rating_comodidad") or 0.0)
        raw["rating_impacto_ambiental"] = float(preferencias.get("rating_impacto_ambiental") or 0.0)
        raw["rating_costes_uso"] = float(preferencias.get("rating_costes_uso") or 0.0)
        raw["rating_tecnologia_conectividad"] = float(preferencias.get("rating_tecnologia_conectividad") or 0.0)
    else: # Si preferencias es None, poner defaults para los ratings
        raw["rating_fiabilidad_durabilidad"] = 0.0
        raw["rating_seguridad"] = 0.0
        raw["rating_comodidad"] = 0.0
        raw["rating_impacto_ambiental"] = 0.0
        raw["rating_costes_uso"] = 0.0
        raw["rating_tecnologia_conectividad"] = 0.0
        
    # --- NUEVA LÓGICA PARA PESOS DE CARGA Y ESPACIO ---
    # Inicializar pesos crudos para las nuevas características BQ que se ponderarán
    raw["maletero_minimo_score"] = PESO_CRUDO_BASE_MALETERO  # Un peso base bajo si no se necesita carga
    raw["maletero_maximo_score"] = PESO_CRUDO_BASE_MALETERO # Un peso base bajo
    raw["largo_vehiculo_score"] = PESO_CRUDO_BASE_MALETERO   # Un peso base bajo

    if is_yes(preferencias.get("transporta_carga_voluminosa")):
        # Si transporta carga voluminosa, aumentamos la importancia de las columnas de maletero
        raw["maletero_minimo_score"] = PESO_CRUDO_FAV_MALETERO_MIN
        raw["maletero_maximo_score"] = PESO_CRUDO_FAV_MALETERO_MAX
        print(f"DEBUG (Weights) ► transporta_carga_voluminosa='sí'. Pesos crudos para maletero: {raw['maletero_minimo_score']}/{raw['maletero_maximo_score']}")

        if is_yes(preferencias.get("necesita_espacio_objetos_especiales")):
            # Si además necesita espacio para objetos especiales, aumentamos la importancia de largo y ancho
            raw["largo_vehiculo_score"] = PESO_CRUDO_FAV_MALETERO_ESP_OBJ_ESPECIALES
            raw["ancho"] = max(raw.get("ancho", 0.5), PESO_CRUDO_FAV_MALETERO_ESP_OBJ_ESPECIALES) # Asegurar que sea al menos 5.0
            print(f"DEBUG (Weights) ► necesita_espacio_objetos_especiales='sí'. Pesos crudos para largo: {raw['largo_vehiculo_score']}, ancho actualizado a: {raw['ancho']}")
    
    # --- Favorecer índice_altura y autonomia_uso_maxima si comodidad es alta ---
    rating_comodidad_val = preferencias.get("rating_comodidad")
    # Inicializar peso para autonomía (nueva característica a ponderar)
    raw["autonomia_vehiculo"] = RAW_PESO_BASE_AUT_VEHI

    if rating_comodidad_val is not None and rating_comodidad_val >= UMBRAL_RATING_COMODIDAD_PARA_FAVORECER:
        print(f"DEBUG (Weights) ► Comodidad alta ({rating_comodidad_val}). Aumentando pesos para índice_altura y autonomía.")
        # Aumentar el peso de indice_altura_interior. 
        # Podemos sumarle al existente o establecer un valor alto. Sumar es más flexible.
        raw["indice_altura_interior"] = raw.get("indice_altura_interior", 0.5) + RAW_WEIGHT_ADICIONAL_FAV_IND_ALTURA_INT_POR_COMODIDAD 
        # Asignar un peso crudo alto a la autonomía
        raw["autonomia_vehiculo"] = RAW_WEIGHT_ADICIONAL_FAV_AUTONOMIA_VEHI_POR_COMODIDAD # Ejemplo de peso crudo alto, ajusta según importancia
    
    # Pesos específicos para bajo peso y bajo consumo, activados por alto rating de impacto ambiental
    raw["fav_bajo_peso"] = 0.0 # Default
    raw["fav_bajo_consumo"] = 0.0 # Default
    
    rating_ia = preferencias.get("rating_impacto_ambiental")
    if rating_ia is not None and rating_ia >= UMBRAL_RATING_IMPACTO_PARA_FAV_PESO_CONSUMO:
        print(f"DEBUG (Weights) ► Impacto Ambiental alto ({rating_ia}). Activando pesos para bajo peso y bajo consumo.")
        raw["fav_bajo_peso"] += RAW_WEIGHT_ADICIONAL_FAV_BAJO_PESO_POR_IMPACTO
        raw["fav_bajo_consumo"] += RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_IMPACTO
    
    # --- NUEVA LÓGICA PARA rating_costes_uso ---
    raw["rating_costes_uso"] = float(preferencias.get("rating_costes_uso") or 0.0) # Peso directo para el concepto general
    
    # Pesos específicos para bajo coste de uso, bajo coste de mantenimiento, y bajo consumo / activados por alto rating_costes_uso
    raw["fav_bajo_coste_uso_directo"] = RAW_PESO_BASE_COSTE_USO_DIRECTO
    raw["fav_bajo_coste_mantenimiento_directo"] = RAW_PESO_BASE_COSTE_MANTENIMIENTO_DIRECTO
    
    rating_cu = preferencias.get("rating_costes_uso")
    if rating_cu is not None and rating_cu >= UMBRAL_RATING_COSTES_USO_PARA_FAV_CONSUMO_COSTES:
        print(f"DEBUG (Weights) ► Costes de Uso alto ({rating_cu}). Activando pesos para bajo consumo, bajo coste uso y mantenimiento.")
        raw["fav_bajo_consumo"] += RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_COSTES #
        raw["fav_bajo_coste_uso_directo"] = RAW_WEIGHT_FAV_BAJO_COSTE_USO_DIRECTO    # 
        raw["fav_bajo_coste_mantenimiento_directo"] = RAW_WEIGHT_FAV_BAJO_COSTE_MANTENIMIENTO_DIRECTO 
    
    # --- NUEVA LÓGICA DE USO INTENSIVO ---
    frecuencia_val = preferencias.get("frecuencia_uso")
    distancia_val = preferencias.get("distancia_trayecto")
    
    # Comprobamos si las condiciones de uso intensivo se cumplen
    es_uso_frecuente = frecuencia_val in [FrecuenciaUso.DIARIO.value, FrecuenciaUso.FRECUENTEMENTE.value]
    es_trayecto_largo = distancia_val in [DistanciaTrayecto.ENTRE_51_Y_150_KM.value, DistanciaTrayecto.MAS_150_KM.value]
    
    if es_uso_frecuente and es_trayecto_largo:
        print(f"DEBUG (Weights) ► Uso intensivo detectado (frecuencia='{frecuencia_val}', distancia='{distancia_val}'). Aumentando peso para bajo consumo.")
        raw["fav_bajo_consumo"] += RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_USO_INTENSIVO

    # --- LÓGICA PARA PESOS DE ARRASTRE DE REMOLQUE ---
    # Usaremos claves distintas para estos pesos para que sean específicos
    raw["par_motor_remolque_score"] = RAW_PESO_BASE_REMOLQUE # Peso base muy bajo si no arrastra
    raw["cap_remolque_cf_score"] = RAW_PESO_BASE_REMOLQUE   # Capacidad remolque con freno
    raw["cap_remolque_sf_score"] = RAW_PESO_BASE_REMOLQUE   # Capacidad remolque sin freno

    if is_yes(preferencias.get("arrastra_remolque")):
        print(f"DEBUG (Weights) ► Usuario arrastra remolque. Aplicando pesos específicos.")
        raw["par_motor_remolque_score"] = RAW_PESO_PAR_MOTOR_REMOLQUE
        raw["cap_remolque_cf_score"] = RAW_PESO_CAP_REMOLQUE_CF
        raw["cap_remolque_sf_score"] = RAW_PESO_CAP_REMOLQUE_SF
        
    # --- NUEVA LÓGICA PARA AJUSTAR PESOS POR CLIMA ---
    # 6. Ajustar pesos basados en información climática
    # Aseguramos que las claves existan antes de sumarles
    raw["rating_seguridad"] = raw.get("rating_seguridad", 0.0) 
    raw["traccion"] = raw.get("traccion", 0.0) 
    current_seguridad_rating = raw.get("rating_seguridad", 0.0) # Obtener el peso base del rating
    if es_zona_nieblas:
        current_seguridad_rating += AJUSTE_CRUDO_SEGURIDAD_POR_NIEBLA
    raw["rating_seguridad"] = max(MIN_SINGLE_RAW_WEIGHT, min(MAX_SINGLE_RAW_WEIGHT, current_seguridad_rating))
    print(f"DEBUG (Weights) ► Zona Nieblas ({es_zona_nieblas}): Peso crudo final rating_seguridad = {raw['rating_seguridad']}")
    
    # Tracción por Nieve y Montaña
    current_traccion_weight = raw.get("traccion", 0.0) # Obtener peso base de tracción (de aventura)
    if es_zona_nieve:
        current_traccion_weight += AJUSTE_CRUDO_TRACCION_POR_NIEVE
    if es_zona_clima_monta:
        current_traccion_weight += AJUSTE_CRUDO_TRACCION_POR_MONTA
    raw["traccion"] = max(MIN_SINGLE_RAW_WEIGHT, min(MAX_SINGLE_RAW_WEIGHT, current_traccion_weight))
    print(f"DEBUG (Weights) ► Zona Nieve ({es_zona_nieve}), Zona Montaña ({es_zona_clima_monta}): Peso crudo final traccion = {raw['traccion']}")
    # --- NUEVA LÓGICA PARA PESOS DE GARAJE/APARCAMIENTO ---
    # Inicializar los nuevos pesos con un valor base bajo
    raw["fav_menor_superficie_planta"] = PESO_CRUDO_BASE_BAJO_DIMENSIONES_GARAJE 
    raw["fav_menor_diametro_giro"] = PESO_CRUDO_BASE_BAJO_DIMENSIONES_GARAJE
    raw["fav_menor_largo_garage"] = PESO_CRUDO_BASE_BAJO_DIMENSIONES_GARAJE 
    raw["fav_menor_ancho_garage"] = PESO_CRUDO_BASE_BAJO_DIMENSIONES_GARAJE 
    raw["fav_menor_alto_garage"] = PESO_CRUDO_BASE_BAJO_DIMENSIONES_GARAJE  

    #"circula principalmente por ciudad / si"
    if is_yes(preferencias.get("circula_principalmente_ciudad")):
        logging.info("DEBUG (Weights) ► Perfil 'Conductor Urbano- Circula por ciudad' detectado. Aumentando peso para menor diámetro de giro.")
        raw['fav_menor_diametro_giro'] += PESO_CRUDO_FAV_DIAMETRO_GIRO_CONDUC_CIUDAD
    
    tiene_garage_val = preferencias.get("tiene_garage")
    
    if tiene_garage_val is not None:
        if not is_yes(tiene_garage_val): # NO tiene garaje
            if is_yes(preferencias.get("problemas_aparcar_calle")):
                raw["fav_menor_superficie_planta"] = PESO_CRUDO_FAV_MENOR_SUPERFICIE
                print(f"DEBUG (Weights) ► Problemas aparcar calle. Favoreciendo menor superficie_planta con peso: {PESO_CRUDO_FAV_MENOR_SUPERFICIE}")
        else: # SÍ tiene garaje
            if is_yes(preferencias.get("espacio_sobra_garage")) is False: # Espacio NO sobra (es 'no' o None)
                raw["fav_menor_diametro_giro"] = PESO_CRUDO_FAV_MENOR_DIAMETRO_GIRO
                print(f"DEBUG (Weights) ► Garaje ajustado. Favoreciendo menor diametro_giro con peso: {PESO_CRUDO_FAV_MENOR_DIAMETRO_GIRO}")
                
                problema_dimension_lista = preferencias.get("problema_dimension_garage") # Esto es List[DimensionProblematica.value] o None
                if isinstance(problema_dimension_lista, list):
                    if "largo" in problema_dimension_lista:
                        raw["fav_menor_largo_garage"] = PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE
                        print(f"DEBUG (Weights) ► Problema LARGO en garaje. Favoreciendo menor largo con peso: {PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE}")
                    if "ancho" in problema_dimension_lista:
                        raw["fav_menor_ancho_garage"] = PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE
                        print(f"DEBUG (Weights) ► Problema ANCHO en garaje. Favoreciendo menor ancho con peso: {PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE}")
                    if "alto" in problema_dimension_lista:
                        raw["fav_menor_alto_garage"] = PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE
                        print(f"DEBUG (Weights) ► Problema ALTO en garaje. Favoreciendo menor alto con peso: {PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE}")
    
    # --- NUEVA LÓGICA PARA PESOS DE ESTILO DE CONDUCCIÓN ---
    estilo_conduccion_val_str = None
    estilo_conduccion_input = preferencias.get("estilo_conduccion")
    if hasattr(estilo_conduccion_input, "value"): # Si es Enum
        estilo_conduccion_val_str = estilo_conduccion_input.value 
    elif isinstance(estilo_conduccion_input, str): # Si ya es string
        estilo_conduccion_val_str = estilo_conduccion_input.lower()

    if estilo_conduccion_val_str == "deportivo":
        print(f"DEBUG (Weights) ► Estilo Conducción 'deportivo'. Aplicando pesos altos de deportividad.")
        raw["deportividad_style_score"] = RAW_PESO_DEPORTIVIDAD_ALTO
        raw["fav_menor_rel_peso_potencia_score"] = RAW_PESO_MENOR_REL_PESO_POTENCIA_ALTO
        raw["potencia_maxima_style_score"] = RAW_PESO_POTENCIA_MAXIMA_ALTO
        raw["par_motor_style_score"] = RAW_PESO_PAR_MOTOR_DEPORTIVO_ALTO
        raw["fav_menor_aceleracion_score"] = RAW_PESO_MENOR_ACELERACION_ALTO
    elif estilo_conduccion_val_str == "mixto":
        print(f"DEBUG (Weights) ► Estilo Conducción 'mixto'. Aplicando pesos medios de deportividad.")
        raw["deportividad_style_score"] = RAW_PESO_DEPORTIVIDAD_MEDIO
        raw["fav_menor_rel_peso_potencia_score"] = RAW_PESO_MENOR_REL_PESO_POTENCIA_MEDIO
        raw["potencia_maxima_style_score"] = RAW_PESO_POTENCIA_MAXIMA_MEDIO
        raw["par_motor_style_score"] = RAW_PESO_PAR_MOTOR_DEPORTIVO_MEDIO
        raw["fav_menor_aceleracion_score"] = RAW_PESO_MENOR_ACELERACION_MEDIO
    else: # "tranquilo" o None
        print(f"DEBUG (Weights) ► Estilo Conducción 'tranquilo' o no definido. Aplicando pesos bajos de deportividad.")
        raw["deportividad_style_score"] = RAW_PESO_DEPORTIVIDAD_BAJO
        raw["fav_menor_rel_peso_potencia_score"] = RAW_PESO_MENOR_REL_PESO_POTENCIA_BAJO
        raw["potencia_maxima_style_score"] = RAW_PESO_POTENCIA_MAXIMA_BAJO
        raw["par_motor_style_score"] = RAW_PESO_PAR_MOTOR_DEPORTIVO_BAJO
        raw["fav_menor_aceleracion_score"] = RAW_PESO_MENOR_ACELERACION_BAJO

     # Clamp final para todos los pesos que podrían haberse acumulado
    for key in list(raw.keys()): # Iterar sobre una copia de las claves si modificas el dict
        if isinstance(raw[key], (int, float)): # Solo clampear números
            raw[key] = max(MIN_SINGLE_RAW_WEIGHT, min(MAX_SINGLE_RAW_WEIGHT, raw[key]))
    
    print(f"DEBUG (Weights) ► Pesos crudos tras añadir ratings: {raw}")
    raw_float = {k: float(v or 0.0) for k, v in raw.items()}
    #print(f"DEBUG (Weights) ► Pesos Crudos FINALES: {raw_float}")
    return raw_float


# normalize_weights se mantiene igual (quizás con el DEBUG print que añadí antes)
def normalize_weights(raw_weights: dict) -> dict:
    """Normaliza los pesos crudos para que sumen 1.0."""
    valid_values = [v for v in raw_weights.values() if isinstance(v, (int, float))]
    total = sum(valid_values) or 1.0 
    normalized = {k: (v / total) if isinstance(v, (int, float)) else 0.0 for k, v in raw_weights.items()}
    print(f"DEBUG (Normalize Weights) ► Pesos Normalizados: {normalized}")
    return normalized



