# utils/weights.py
# cada tuple a la prioridad relativa que quieres en ese nivel de aventura.
# “ninguna”: 0 en todo, porque no te importa nada off-road.
# “ocasional”: priorizas un poco el espacio (altura) y la tracción, pero no las reductoras.
# “extrema”: la tracción y reductoras dominan, y el espacio importa menos en comparación.
# Ademas se refactoriza compute_raw_weights para que trate batalla e indice_altura_interior como preferencias suaves, cuya importancia (peso) dependerá de si el usuario indicó ser alto (altura_mayor_190='sí').



from typing import Optional, Dict, Any # Añadir tipos
# Importar is_yes y Enums
from .conversion import is_yes
from .enums import NivelAventura 
from graph.perfil.state import PerfilUsuario # Importar para type hint

# En utils/weights.py

MAX_SINGLE_RAW_WEIGHT = 10.0 # Definir el tope máximo para un peso crudo individual
MIN_SINGLE_RAW_WEIGHT = 0.0  # Definir el tope mínimo
# ... (AVENTURA_RAW como lo definiste) ...
AVENTURA_RAW = {
  "ninguna":   {"altura_libre_suelo":  0,   "traccion":  0,  "reductoras":  0},
  "ocasional": {"altura_libre_suelo":  6,   "traccion":  3,  "reductoras":  1},
  "extrema":   {"altura_libre_suelo":  8,   "traccion": 8,  "reductoras":  8},
}

# --- VALORES DE PESO CRUDO PARA NUEVAS PREFERENCIAS DE GARAJE/APARCAMIENTO (¡AJUSTA ESTOS!) ---
PESO_FAV_MENOR_SUPERFICIE = 7.0 #fav_menor_superficie_planta
PESO_FAV_MENOR_DIAMETRO_GIRO = 7.0 #fav_menor_diametro_giro
PESO_FAV_MENOR_DIMENSION_GARAJE = 6.0 # Para largo, ancho, alto problemáticos fav_menor_largo_garage
PESO_BASE_BAJO_PARA_DIMENSIONES = 0.5 # Peso si no es una preocupación explícita

# --- VALORES DE AJUSTE DE PESO CRUDO POR CLIMA (¡AJUSTA ESTOS!) ---
AJUSTE_PESO_SEGURIDAD_POR_NIEBLA = 2.0 # Cuánto sumar al peso crudo de seguridad si hay niebla
AJUSTE_PESO_TRACCION_POR_NIEVE = 5.0   # Cuánto sumar al peso crudo de tracción si hay nieve
AJUSTE_PESO_TRACCION_POR_MONTA = 2.0   # Cuánto sumar al peso crudo de tracción si es clima de montaña

# --- NUEVAS CONSTANTES DE PESOS CRUDOS PARA ESTILO DE CONDUCCIÓN (¡AJUSTA ESTOS VALORES!) ---
# Si estilo es DEPORTIVO
PESO_DEPORTIVIDAD_ALTO = 5.0
PESO_MENOR_REL_PESO_POTENCIA_ALTO = 7.0
PESO_POTENCIA_MAXIMA_ALTO = 5.0
PESO_PAR_MOTOR_DEPORTIVO_ALTO = 3.0 # Distinto de par para remolque
PESO_MENOR_ACELERACION_ALTO = 6.0

# Si estilo es MIXTO
PESO_DEPORTIVIDAD_MEDIO = 2.5
PESO_MENOR_REL_PESO_POTENCIA_MEDIO = 3.5
PESO_POTENCIA_MAXIMA_MEDIO = 2.5
PESO_PAR_MOTOR_DEPORTIVO_MEDIO = 1.5
PESO_MENOR_ACELERACION_MEDIO = 3.0

# Si estilo es TRANQUILO o no definido (base)
PESO_DEPORTIVIDAD_BAJO = 1.0
PESO_MENOR_REL_PESO_POTENCIA_BAJO = 0.5
PESO_POTENCIA_MAXIMA_BAJO = 0.5
PESO_PAR_MOTOR_DEPORTIVO_BAJO = 0.5
PESO_MENOR_ACELERACION_BAJO = 1.0

# --- Función compute_raw_weights CORREGIDA ---
def compute_raw_weights(
    preferencias: Optional[PerfilUsuario], # <-- Cambiar Type Hint a PerfilUsuario
    estetica_min_val: Optional[float],      # Renombrado para claridad (viene de filtros.estetica_min)
    premium_min_val: Optional[float],       # Renombrado para claridad (viene de filtros.premium_min)
    singular_min_val: Optional[float],      # Renombrado para claridad (viene de filtros.singular_min)
    priorizar_ancho: Optional[bool], # <-- NUEVO ARGUMENTO BOOLEANO
    es_zona_nieblas: bool = False,
    es_zona_nieve: bool = False,
    es_zona_clima_monta: bool = False,
    ) -> Dict[str, float]: 
    """
    Calcula pesos crudos. Accede a preferencias usando notación de punto.
    """
    
    raw = {} # Inicializar el diccionario de pesos crudos
    # Usar 0.0 como fallback si los valores de filtro son None
    raw = {
        "estetica": float(estetica_min_val or 0.0),
        "premium":  float(premium_min_val or 0.0),
        "singular": float(singular_min_val or 0.0)
    }
    print(f"DEBUG (Weights) ► Pesos crudos iniciales (est/prem/sing): {raw}")

    # Pesos de Aventura
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
        
    aventura_weights_map = AVENTURA_RAW.get(aventura_level_str, AVENTURA_RAW["ninguna"])
    raw["altura_libre_suelo"] = float(aventura_weights_map.get("altura_libre_suelo", 0.0))
    raw["traccion"] = float(aventura_weights_map.get("traccion", 0.0))
    raw["reductoras"] = float(aventura_weights_map.get("reductoras", 0.0))
    print(f"DEBUG (Weights) ► Pesos crudos tras añadir aventura: {raw}")

    # Pesos basados en altura_mayor_190
    altura_pref_val = preferencias.get("altura_mayor_190") if preferencias else None # <-- USO DE .get()
    if is_yes(altura_pref_val):
        print("DEBUG (Weights) ► Usuario alto. Asignando pesos a batalla/índice.")
        raw["batalla"] = 5.0 
        raw["indice_altura_interior"] = 4.0 
    else:
        print("DEBUG (Weights) ► Usuario NO alto. Asignando pesos bajos a batalla/índice.")
        raw["batalla"] = 1.0 
        raw["indice_altura_interior"] = 1.0 
    print(f"DEBUG (Weights) ► Pesos crudos tras añadir dims por altura: {raw}")
    
    # Peso para 'ancho' basado en 'priorizar_ancho' (influenciado por priorizar_ancho de pasajeros Z>=2)
    # Este peso favorece MÁS ancho. Lo mantendremos separado del "fav_menor_ancho_garage".
    if priorizar_ancho: 
        raw["ancho_general_score"] = 5.0  
        print(f"DEBUG (Weights) ► Priorizar Ancho=True. Asignando peso crudo alto a ancho_general_score: {raw['ancho_general_score']}")
    else:
        raw["ancho_general_score"] = 1.0  
        print(f"DEBUG (Weights) ► Priorizar Ancho=False/None. Asignando peso crudo bajo a ancho_general_score: {raw['ancho_general_score']}")
        
    # --- NUEVO PESO CRUDO PARA DEPRECIACIÓN ---
    if is_yes(preferencias.get("prioriza_baja_depreciacion")):
        raw["devaluacion"] = 5.0 # Si 'sí', peso crudo de 5.0
    else: # 'no' o None
        raw["devaluacion"] = 1.0 # Si 'no' o no especificado, peso crudo de 1.0
    print(f"DEBUG (Weights) ► Peso crudo para devaluacion (basado en prioriza_baja_depreciacion='{preferencias.get('prioriza_baja_depreciacion')}'): {raw['devaluacion']}")

    # 5. Añadir pesos crudos directamente de los ratings del usuario    
    # Añadir pesos crudos directamente de los ratings del usuario
    if preferencias: # Verificar si el diccionario preferencias existe
        raw["rating_fiabilidad_durabilidad"] = float(preferencias.get("rating_fiabilidad_durabilidad") or 0.0)
        raw["rating_seguridad"] = float(preferencias.get("rating_seguridad") or 0.0)
        raw["rating_comodidad"] = float(preferencias.get("rating_comodidad") or 0.0)
        raw["rating_impacto_ambiental"] = float(preferencias.get("rating_impacto_ambiental") or 0.0)
        #raw["rating_costes_uso"] = float(preferencias.get("rating_costes_uso") or 0.0)
        raw["rating_tecnologia_conectividad"] = float(preferencias.get("rating_tecnologia_conectividad") or 0.0)
    else: # Si preferencias es None, poner defaults para los ratings
        raw["rating_fiabilidad_durabilidad"] = 0.0
        raw["rating_seguridad"] = 0.0
        raw["rating_comodidad"] = 0.0
        raw["rating_impacto_ambiental"] = 0.0
        #raw["rating_costes_uso"] = 0.0
        raw["rating_tecnologia_conectividad"] = 0.0
    # --- NUEVA LÓGICA PARA PESOS DE CARGA Y ESPACIO ---
    # Inicializar pesos crudos para las nuevas características BQ que se ponderarán
    raw["maletero_minimo_score"] = 1.0  # Un peso base bajo si no se necesita carga
    raw["maletero_maximo_score"] = 1.0  # Un peso base bajo
    raw["largo_vehiculo_score"] = 1.0   # Un peso base bajo

    if is_yes(preferencias.get("transporta_carga_voluminosa")):
        # Si transporta carga voluminosa, aumentamos la importancia de las columnas de maletero
        raw["maletero_minimo_score"] = 5.0 # Ejemplo de peso crudo, ojo,  ajustar según importancia
        raw["maletero_maximo_score"] = 5.0 # Ejemplo de peso crudo
        print(f"DEBUG (Weights) ► transporta_carga_voluminosa='sí'. Pesos crudos para maletero: {raw['maletero_minimo_score']}/{raw['maletero_maximo_score']}")

        if is_yes(preferencias.get("necesita_espacio_objetos_especiales")):
            # Si además necesita espacio para objetos especiales, aumentamos la importancia de largo y ancho
            raw["largo_vehiculo_score"] = 5.0 # Ejemplo de peso crudo
            # Para 'ancho', podemos sumarle al valor que ya tenía por 'priorizar_ancho' o establecer un mínimo alto.
            # Optemos por asegurar un mínimo alto si esta condición es sí.
            raw["ancho"] = max(raw.get("ancho", 0.5), 5.0) # Asegurar que sea al menos 5.0
            print(f"DEBUG (Weights) ► necesita_espacio_objetos_especiales='sí'. Pesos crudos para largo: {raw['largo_vehiculo_score']}, ancho actualizado a: {raw['ancho']}")
    
    # --- NUEVA LÓGICA: Favorecer índice_altura y autonomía si comodidad es alta ---
    UMBRAL_RATING_COMODIDAD_PARA_FAVORECER = 8 # Define tu umbral
    rating_comodidad_val = preferencias.get("rating_comodidad")

    # Inicializar peso para autonomía (nueva característica a ponderar)
    raw["autonomia_vehiculo"] = 1.0 # Peso base bajo por defecto

    if rating_comodidad_val is not None and rating_comodidad_val >= UMBRAL_RATING_COMODIDAD_PARA_FAVORECER:
        print(f"DEBUG (Weights) ► Comodidad alta ({rating_comodidad_val}). Aumentando pesos para índice_altura y autonomía.")
        # Aumentar el peso de indice_altura_interior. 
        # Podemos sumarle al existente o establecer un valor alto. Sumar es más flexible.
        raw["indice_altura_interior"] = raw.get("indice_altura_interior", 0.5) + 4.0 # Ejemplo: suma 4 puntos crudos
        # Asignar un peso crudo alto a la autonomía
        raw["autonomia_vehiculo"] = 5.0 # Ejemplo de peso crudo alto, ajusta según importancia
    
    # Pesos específicos para bajo peso y bajo consumo, activados por alto rating de impacto ambiental
    raw["fav_bajo_peso"] = 0.0 # Default
    raw["fav_bajo_consumo"] = 0.0 # Default
    
    UMBRAL_IMPACTO_PARA_PESO_CONSUMO = 8 # Mismo umbral que para el flag del distintivo
    rating_ia = preferencias.get("rating_impacto_ambiental")
    if rating_ia is not None and rating_ia >= UMBRAL_IMPACTO_PARA_PESO_CONSUMO:
        print(f"DEBUG (Weights) ► Impacto Ambiental alto ({rating_ia}). Activando pesos para bajo peso y bajo consumo.")
        raw["fav_bajo_peso"] += 5.0 # Ejemplo de peso crudo, ¡AQUI DEBEMOS AJUSTAR!
        raw["fav_bajo_consumo"] += 5.0 # Ejemplo de peso crudo, ¡AQUI DEBEMOS AJUSTAR!
    
    # --- NUEVA LÓGICA PARA rating_costes_uso ---
    raw["rating_costes_uso"] = float(preferencias.get("rating_costes_uso") or 0.0) # Peso directo para el concepto general
    
    # Pesos específicos para bajo coste de uso, bajo coste de mantenimiento, y bajo consumo / activados por alto rating_costes_uso
    raw["fav_bajo_coste_uso_directo"] = 0.0 # Default
    raw["fav_bajo_coste_mantenimiento_directo"] = 0.0 # Default
    
    UMBRAL_COSTES_USO_PARA_EXTRAS = 8 # ¡AJUSTA ESTE UMBRAL!
    rating_cu = preferencias.get("rating_costes_uso")
    if rating_cu is not None and rating_cu >= UMBRAL_COSTES_USO_PARA_EXTRAS:
        print(f"DEBUG (Weights) ► Costes de Uso alto ({rating_cu}). Activando pesos para bajo consumo, bajo coste uso y mantenimiento.")
        raw["fav_bajo_consumo"] += 5.0 # Refuerza el peso de bajo consumo (ej: 7.0) ¡AJUSTArR!
        raw["fav_bajo_coste_uso_directo"] = 7.0    # Peso específico para columna costes_de_uso, ¡AJUSTAR!
        raw["fav_bajo_coste_mantenimiento_directo"] = 7.0 # Peso específico para columna costes_mantenimiento, ¡AJUSTAR!
    
    # --- LÓGICA PARA PESOS DE ARRASTRE DE REMOLQUE ---
    # Usaremos claves distintas para estos pesos para que sean específicos
    raw["par_motor_remolque_score"] = 1.0  # Peso base muy bajo si no arrastra
    raw["cap_remolque_cf_score"] = 1.0   # Capacidad remolque con freno
    raw["cap_remolque_sf_score"] = 1.0   # Capacidad remolque sin freno

    if is_yes(preferencias.get("arrastra_remolque")):
        print(f"DEBUG (Weights) ► Usuario arrastra remolque. Aplicando pesos específicos.")
        raw["par_motor_remolque_score"] = 6.0
        raw["cap_remolque_cf_score"] = 7.0
        raw["cap_remolque_sf_score"] = 3.0
        
    # --- NUEVA LÓGICA PARA AJUSTAR PESOS POR CLIMA ---
    # 6. Ajustar pesos basados en información climática
    # Aseguramos que las claves existan antes de sumarles
    raw["rating_seguridad"] = raw.get("rating_seguridad", 0.0) 
    raw["traccion"] = raw.get("traccion", 0.0) 
    current_seguridad_rating = raw.get("rating_seguridad", 0.0) # Obtener el peso base del rating
    if es_zona_nieblas:
        current_seguridad_rating += AJUSTE_PESO_SEGURIDAD_POR_NIEBLA
    raw["rating_seguridad"] = max(MIN_SINGLE_RAW_WEIGHT, min(MAX_SINGLE_RAW_WEIGHT, current_seguridad_rating))
    print(f"DEBUG (Weights) ► Zona Nieblas ({es_zona_nieblas}): Peso crudo final rating_seguridad = {raw['rating_seguridad']}")
    
    # Tracción por Nieve y Montaña
    current_traccion_weight = raw.get("traccion", 0.0) # Obtener peso base de tracción (de aventura)
    if es_zona_nieve:
        current_traccion_weight += AJUSTE_PESO_TRACCION_POR_NIEVE
    if es_zona_clima_monta:
        current_traccion_weight += AJUSTE_PESO_TRACCION_POR_MONTA
    raw["traccion"] = max(MIN_SINGLE_RAW_WEIGHT, min(MAX_SINGLE_RAW_WEIGHT, current_traccion_weight))
    print(f"DEBUG (Weights) ► Zona Nieve ({es_zona_nieve}), Zona Montaña ({es_zona_clima_monta}): Peso crudo final traccion = {raw['traccion']}")
    # --- NUEVA LÓGICA PARA PESOS DE GARAJE/APARCAMIENTO ---
    # Inicializar los nuevos pesos con un valor base bajo
    raw["fav_menor_superficie_planta"] = PESO_BASE_BAJO_PARA_DIMENSIONES 
    raw["fav_menor_diametro_giro"] = PESO_BASE_BAJO_PARA_DIMENSIONES
    raw["fav_menor_largo_garage"] = PESO_BASE_BAJO_PARA_DIMENSIONES 
    raw["fav_menor_ancho_garage"] = PESO_BASE_BAJO_PARA_DIMENSIONES 
    raw["fav_menor_alto_garage"] = PESO_BASE_BAJO_PARA_DIMENSIONES  

    tiene_garage_val = preferencias.get("tiene_garage")
    
    if tiene_garage_val is not None:
        if not is_yes(tiene_garage_val): # NO tiene garaje
            if is_yes(preferencias.get("problemas_aparcar_calle")):
                raw["fav_menor_superficie_planta"] = PESO_FAV_MENOR_SUPERFICIE
                print(f"DEBUG (Weights) ► Problemas aparcar calle. Favoreciendo menor superficie_planta con peso: {PESO_FAV_MENOR_SUPERFICIE}")
        else: # SÍ tiene garaje
            if is_yes(preferencias.get("espacio_sobra_garage")) is False: # Espacio NO sobra (es 'no' o None)
                raw["fav_menor_diametro_giro"] = PESO_FAV_MENOR_DIAMETRO_GIRO
                print(f"DEBUG (Weights) ► Garaje ajustado. Favoreciendo menor diametro_giro con peso: {PESO_FAV_MENOR_DIAMETRO_GIRO}")
                
                problema_dimension_lista = preferencias.get("problema_dimension_garage") # Esto es List[DimensionProblematica.value] o None
                if isinstance(problema_dimension_lista, list):
                    if "largo" in problema_dimension_lista:
                        raw["fav_menor_largo_garage"] = PESO_FAV_MENOR_DIMENSION_GARAJE
                        print(f"DEBUG (Weights) ► Problema LARGO en garaje. Favoreciendo menor largo con peso: {PESO_FAV_MENOR_DIMENSION_GARAJE}")
                    if "ancho" in problema_dimension_lista:
                        raw["fav_menor_ancho_garage"] = PESO_FAV_MENOR_DIMENSION_GARAJE
                        print(f"DEBUG (Weights) ► Problema ANCHO en garaje. Favoreciendo menor ancho con peso: {PESO_FAV_MENOR_DIMENSION_GARAJE}")
                    if "alto" in problema_dimension_lista:
                        raw["fav_menor_alto_garage"] = PESO_FAV_MENOR_DIMENSION_GARAJE
                        print(f"DEBUG (Weights) ► Problema ALTO en garaje. Favoreciendo menor alto con peso: {PESO_FAV_MENOR_DIMENSION_GARAJE}")
    
    # --- NUEVA LÓGICA PARA PESOS DE ESTILO DE CONDUCCIÓN ---
    estilo_conduccion_val_str = None
    estilo_conduccion_input = preferencias.get("estilo_conduccion")
    if hasattr(estilo_conduccion_input, "value"): # Si es Enum
        estilo_conduccion_val_str = estilo_conduccion_input.value 
    elif isinstance(estilo_conduccion_input, str): # Si ya es string
        estilo_conduccion_val_str = estilo_conduccion_input.lower()

    if estilo_conduccion_val_str == "deportivo":
        print(f"DEBUG (Weights) ► Estilo Conducción 'deportivo'. Aplicando pesos altos de deportividad.")
        raw["deportividad_style_score"] = PESO_DEPORTIVIDAD_ALTO
        raw["fav_menor_rel_peso_potencia_score"] = PESO_MENOR_REL_PESO_POTENCIA_ALTO
        raw["potencia_maxima_style_score"] = PESO_POTENCIA_MAXIMA_ALTO
        raw["par_motor_style_score"] = PESO_PAR_MOTOR_DEPORTIVO_ALTO
        raw["fav_menor_aceleracion_score"] = PESO_MENOR_ACELERACION_ALTO
    elif estilo_conduccion_val_str == "mixto":
        print(f"DEBUG (Weights) ► Estilo Conducción 'mixto'. Aplicando pesos medios de deportividad.")
        raw["deportividad_style_score"] = PESO_DEPORTIVIDAD_MEDIO
        raw["fav_menor_rel_peso_potencia_score"] = PESO_MENOR_REL_PESO_POTENCIA_MEDIO
        raw["potencia_maxima_style_score"] = PESO_POTENCIA_MAXIMA_MEDIO
        raw["par_motor_style_score"] = PESO_PAR_MOTOR_DEPORTIVO_MEDIO
        raw["fav_menor_aceleracion_score"] = PESO_MENOR_ACELERACION_MEDIO
    else: # "tranquilo" o None
        print(f"DEBUG (Weights) ► Estilo Conducción 'tranquilo' o no definido. Aplicando pesos bajos de deportividad.")
        raw["deportividad_style_score"] = PESO_DEPORTIVIDAD_BAJO
        raw["fav_menor_rel_peso_potencia_score"] = PESO_MENOR_REL_PESO_POTENCIA_BAJO
        raw["potencia_maxima_style_score"] = PESO_POTENCIA_MAXIMA_BAJO
        raw["par_motor_style_score"] = PESO_PAR_MOTOR_DEPORTIVO_BAJO
        raw["fav_menor_aceleracion_score"] = PESO_MENOR_ACELERACION_BAJO
    # --- FIN NUEVA LÓGICA ---
    
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



