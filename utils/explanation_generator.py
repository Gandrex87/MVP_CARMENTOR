#usada en el Nodo final para explicar el coche recomendado
import pandas as pd
import traceback
from typing import Dict, List, Optional, Any
import logging # Asegúrate de tener logging
from langchain_core.messages import AIMessage
from graph.perfil.state import EstadoAnalisisPerfil, PerfilUsuario 
from utils.conversion import is_yes
# Modelos LLM y prompts
from config.llm import llm_explicacion_coche 
from prompts.loader import system_prompt_explicacion_coche_mejorado
from langchain_core.messages import SystemMessage, HumanMessage

try:
    from config.settings import (
        UMBRAL_LOW_COST_PENALIZABLE_SCALED,
        UMBRAL_DEPORTIVIDAD_PENALIZABLE_SCALED
    )
except ImportError:
    logging.warning("WARN (ExplanationGenerator) ► Constantes de umbral no encontradas en config.settings. Usando valores default.")
    UMBRAL_LOW_COST_PENALIZABLE_SCALED = 0.6 # Valor por defecto
    UMBRAL_DEPORTIVIDAD_PENALIZABLE_SCALED = 0.6 # Valor por defecto


# Mapeo de claves de peso a información para la explicación
# Esta es una versión simplificada, necesitarás el mapa completo que ya tienes
# en _generar_explicacion_simple_coche o uno similar.
# ¡DEBES COMPLETAR Y REFINAR ESTE MAPA!
MAPA_PESOS_A_INFO_EXPLICACION = {
    "estetica": {
        "nombre_amigable_caracteristica":    "un buen diseño",
        "pref_usuario_campo":                 "valora_estetica",
        "pref_usuario_texto_si":              "valoras la estética"
    },
    "premium": {
        "nombre_amigable_caracteristica":    "un carácter premium",
        "pref_usuario_campo":                 "apasionado_motor",
        "pref_usuario_texto_si":              "eres un apasionado del motor"
    },
    "singular": {
        "nombre_amigable_caracteristica":    "un toque de singularidad",
        "pref_usuario_campo":                 "prefiere_diseno_exclusivo",
        "pref_usuario_texto_si":              "prefieres un diseño exclusivo"
    },
    "altura_libre_suelo": {
        "nombre_amigable_caracteristica":    "buena altura libre al suelo",
        "pref_usuario_campo":                 "aventura",
        "pref_usuario_texto_si":              "buscas aventura"
    },
    "traccion": {
        "nombre_amigable_caracteristica":    "un sistema de tracción eficaz",
        "pref_usuario_campo":                 "aventura",
        "pref_usuario_texto_si":              "buscas aventura"
    },
    "reductoras": {
        "nombre_amigable_caracteristica":    "capacidades off-road (reducción)",
        "pref_usuario_campo":                 "aventura",
        "pref_usuario_texto_si":              "buscas aventura extrema"
    },
    "batalla": {
        "nombre_amigable_caracteristica":    "una buena batalla (espacio interior)",
        "pref_usuario_campo":                 "altura_mayor_190",
        "pref_usuario_texto_si":              "eres una persona alta"
    },
    "indice_altura_interior": {
        "nombre_amigable_caracteristica":    "un buen índice de altura interior",
        "pref_usuario_campo":                 "altura_mayor_190",
        "pref_usuario_texto_si":              "eres una persona alta"
    },
    "rating_fiabilidad_durabilidad": {
        "nombre_amigable_caracteristica":    "alta fiabilidad y durabilidad",
        "pref_usuario_campo":                 "rating_fiabilidad_durabilidad",
        "pref_usuario_texto_si":              "la fiabilidad y durabilidad son muy importantes para ti"
    },
    "rating_seguridad": {
        "nombre_amigable_caracteristica":    "un alto nivel de seguridad",
        "pref_usuario_campo":                 "rating_seguridad",
        "pref_usuario_texto_si":              "la seguridad es clave para ti"
    },
    "rating_comodidad": {
        "nombre_amigable_caracteristica":    "un gran confort",
        "pref_usuario_campo":                 "rating_comodidad",
        "pref_usuario_texto_si":              "el confort es una prioridad"
    },
    "rating_impacto_ambiental": {
        "nombre_amigable_caracteristica":    "un menor impacto ambiental",
        "pref_usuario_campo":                 "rating_impacto_ambiental",
        "pref_usuario_texto_si":              "te preocupa el impacto ambiental"
    },
    "rating_tecnologia_conectividad": {
        "nombre_amigable_caracteristica":    "buena tecnología y conectividad",
        "pref_usuario_campo":                 "rating_tecnologia_conectividad",
        "pref_usuario_texto_si":              "la tecnología es importante para ti"
    },
    "devaluacion": {
        "nombre_amigable_caracteristica":    "una baja depreciación esperada",
        "pref_usuario_campo":                 "prioriza_baja_depreciacion",
        "pref_usuario_texto_si":              "te importa la baja depreciación"
    },
    "maletero_minimo_score": {
        "nombre_amigable_caracteristica":    "un maletero mínimo adecuado",
        "pref_usuario_campo":                 "transporta_carga_voluminosa",
        "pref_usuario_texto_si":              "necesitas transportar carga"
    },
    "maletero_maximo_score": {
        "nombre_amigable_caracteristica":    "un maletero máximo generoso",
        "pref_usuario_campo":                 "transporta_carga_voluminosa",
        "pref_usuario_texto_si":              "necesitas transportar carga"
    },
    "largo_vehiculo_score": {
        "nombre_amigable_caracteristica":    "un buen tamaño general (largo)",
        "pref_usuario_campo":                 "necesita_espacio_objetos_especiales",
        "pref_usuario_texto_si":              "necesitas espacio para objetos especiales"
    },
    "ancho_general_score": {
        "nombre_amigable_caracteristica":    "una buena anchura general",
        "pref_usuario_campo":                 "priorizar_ancho",
        "pref_usuario_texto_si":              "necesitas un coche ancho para pasajeros u objetos"
    },
    "autonomia_vehiculo": {
        "nombre_amigable_caracteristica":    "una buena autonomía",
        "pref_usuario_campo":                 "rating_comodidad",
        "pref_usuario_texto_si":              "valoras el confort (que incluye viajes largos)"
    },
    "fav_bajo_peso": {
        "nombre_amigable_caracteristica":    "un peso contenido (eficiencia)",
        "pref_usuario_campo":                 "rating_impacto_ambiental",
        "pref_usuario_texto_si":              "te preocupa el impacto ambiental"
    },
    "fav_bajo_consumo": {
        "nombre_amigable_caracteristica":    "un bajo consumo",
        "pref_usuario_campo":                 "rating_impacto_ambiental",
        "pref_usuario_texto_si":              "te preocupa el impacto ambiental y/o los costes"
    },
    "fav_bajo_coste_uso_directo": {
        "nombre_amigable_caracteristica":    "bajos costes de uso",
        "pref_usuario_campo":                 "rating_costes_uso",
        "pref_usuario_texto_si":              "los costes de uso son importantes para ti"
    },
    "fav_bajo_coste_mantenimiento_directo": {
        "nombre_amigable_caracteristica":    "bajos costes de mantenimiento",
        "pref_usuario_campo":                 "rating_costes_uso",
        "pref_usuario_texto_si":              "los costes de mantenimiento son importantes para ti"
    },
    "par_motor_remolque_score": {
        "nombre_amigable_caracteristica":    "buen par motor para remolcar",
        "pref_usuario_campo":                 "arrastra_remolque",
        "pref_usuario_texto_si":              "necesitas arrastrar remolque"
    },
    "cap_remolque_cf_score": {
        "nombre_amigable_caracteristica":    "buena capacidad de remolque con freno",
        "pref_usuario_campo":                 "arrastra_remolque",
        "pref_usuario_texto_si":              "necesitas arrastrar remolque"
    },
    "cap_remolque_sf_score": {
        "nombre_amigable_caracteristica":    "buena capacidad de remolque sin freno",
        "pref_usuario_campo":                 "arrastra_remolque",
        "pref_usuario_texto_si":              "necesitas arrastrar remolque"
    },
    "fav_menor_superficie_planta": {
        "nombre_amigable_caracteristica":    "un tamaño compacto para aparcar",
        "pref_usuario_campo":                 "problemas_aparcar_calle",
        "pref_usuario_texto_si":              "tienes problemas para aparcar en la calle"
    },
    "fav_menor_diametro_giro": {
        "nombre_amigable_caracteristica":    "un buen diámetro de giro (maniobrabilidad)",
        "pref_usuario_campo":                 "espacio_sobra_garage",
        "pref_usuario_texto_si":              "tu garaje es ajustado"
    },
    "fav_menor_largo_garage": {
        "nombre_amigable_caracteristica":    "un largo adecuado para tu garaje",
        "pref_usuario_campo":                 "problema_dimension_garage",
        "pref_usuario_texto_si":              "el largo es un problema en tu garaje"
    },
    "fav_menor_ancho_garage": {
        "nombre_amigable_caracteristica":    "un ancho contenido para tu garaje",
        "pref_usuario_campo":                 "problema_dimension_garage",
        "pref_usuario_texto_si":              "el ancho es un problema en tu garaje"
    },
    "fav_menor_alto_garage": {
        "nombre_amigable_caracteristica":    "una altura adecuada para tu garaje",
        "pref_usuario_campo":                 "problema_dimension_garage",
        "pref_usuario_texto_si":              "la altura es un problema en tu garaje"
    },
    "deportividad_style_score": {
        "nombre_amigable_caracteristica":    "un carácter deportivo",
        "pref_usuario_campo":                 "estilo_conduccion",
        "pref_usuario_texto_si":              "prefieres un estilo de conducción deportivo"
    },
    "fav_menor_rel_peso_potencia_score": {
        "nombre_amigable_caracteristica":    "una buena relación peso/potencia",
        "pref_usuario_campo":                 "estilo_conduccion",
        "pref_usuario_texto_si":              "prefieres un estilo de conducción deportivo"
    },
    "potencia_maxima_style_score": {
        "nombre_amigable_caracteristica":    "una potencia considerable",
        "pref_usuario_campo":                 "estilo_conduccion",
        "pref_usuario_texto_si":              "prefieres un estilo de conducción deportivo"
    },
    "par_motor_style_score": {
        "nombre_amigable_caracteristica":    "un buen par motor para dinamismo",
        "pref_usuario_campo":                 "estilo_conduccion",
        "pref_usuario_texto_si":              "prefieres un estilo de conducción deportivo"
    },
    "fav_menor_aceleracion_score": {
        "nombre_amigable_caracteristica":    "una buena aceleración",
        "pref_usuario_campo":                 "estilo_conduccion",
        "pref_usuario_texto_si":              "prefieres un estilo de conducción deportivo"
    },
    # Si en el futuro agregas más keys en pesos_normalizados, añádelas aquí con la misma estructura.
}

MAPA_AJUSTES_SCORE_A_TEXTO = {
    # Penalizaciones activadas por flags de COMODIDAD
    "penaliza_low_cost_por_comodidad_aplicada": 
        "aunque, dado que priorizas mucho el confort, se ha considerado que sus acabados o equipamiento son más sencillos de lo esperado",
    "penaliza_deportividad_por_comodidad_aplicada":
        "aunque, debido a tu alta preferencia por el confort, se ha tenido en cuenta que su carácter es marcadamente deportivo",
    
    # Penalizaciones por ANTIGÜEDAD (si tecnología es alta)
    "penaliza_antiguedad_mas_10_anos_aplicada":
        "a pesar de ser un modelo con más de 10 años, lo que se ha considerado por tu interés en la tecnología",
    "penaliza_antiguedad_7_a_10_anos_aplicada":
        "considerando que es un vehículo de entre 7 y 10 años y tu interés en la tecnología",
    "penaliza_antiguedad_5_a_7_anos_aplicada":
        "teniendo en cuenta que tiene entre 5 y 7 años, aspecto relevante por tu preferencia tecnológica",

    # Lógica DISTINTIVO AMBIENTAL (General - activada por alto rating de impacto ambiental)
    "bonus_distintivo_general_favorable_aplicado": # CERO, 0, ECO, C
        "y además, su distintivo ambiental favorable (C, ECO o 0) suma a su perfil ecológico",
    "penalty_distintivo_general_desfavorable_aplicado": # B, NA
        "aunque es importante notar que su distintivo ambiental (B o NA) no es el más ventajoso desde una perspectiva ecológica general",
    "bonus_ocasion_por_impacto_ambiental_aplicado":
        "y el hecho de ser un vehículo de ocasión también contribuye positivamente a su valoración de impacto ambiental",

    # Lógica DISTINTIVO AMBIENTAL (Específica ZBE - activada si CP está en ZBE)
    "bonus_zbe_distintivo_favorable_aplicado": # CERO, 0, ECO, C
        "lo cual es especialmente positivo dado que te encuentras en una Zona de Bajas Emisiones (ZBE) gracias a su distintivo ambiental",
    "penalty_zbe_distintivo_desfavorable_aplicado": # B, NA
        "sin embargo, dado que te encuentras en una Zona de Bajas Emisiones (ZBE), su distintivo ambiental (B o NA) es una consideración importante",
        
    # Penalización por PUERTAS BAJAS (si aplica)
    "penaliza_puertas_bajas_aplicada":
        "aunque para el uso familiar con niños que necesitas, se ha tenido en cuenta el número de puertas"
}

# MEJORA: Definimos constantes para mejorar la legibilidad y facilitar la configuración.
UMBRAL_PESO_MINIMO = 0.005
UMBRAL_FEATURE_DESTACADA = 0.4
UMBRAL_RATING_USUARIO_IMPORTANTE = 7

# MEJORA: Se extrae la lógica de construcción de claves a una función con una única responsabilidad.
def _get_clave_feature_scaled(clave_peso: str) -> str:
    """Convierte una clave de peso a su correspondiente clave de feature escalada."""
    if clave_peso.startswith("rating_"):
        return clave_peso.replace("rating_", "") + "_scaled"
    if clave_peso.startswith("fav_menor_"):
        return clave_peso.replace("fav_menor_", "menor_") + "_scaled"
    if clave_peso.startswith("fav_bajo_"):
        return clave_peso.replace("fav_", "") + "_scaled"
    
    # Casos especiales que terminan en _score
    if clave_peso == "deportividad_style_score": return "deportividad_style_scaled"
    if clave_peso == "potencia_maxima_style_score": return "potencia_maxima_style_scaled"
    if clave_peso == "par_motor_style_score": return "par_scaled"
    if clave_peso == "ancho_general_score": return "ancho_scaled"
    
    if clave_peso.endswith("_score"):
        return clave_peso.replace("_score", "") + "_scaled"
    
    return clave_peso + "_scaled"

# MEJORA: Se extrae la lógica de validación de preferencias a una función dedicada.
def _es_preferencia_activa(valor_preferencia: Any, clave_peso_original: str) -> bool:
    """
    Determina si el valor de una preferencia de usuario se considera "activa" o "importante".
    """
    if isinstance(valor_preferencia, (int, float)):
        return valor_preferencia >= UMBRAL_RATING_USUARIO_IMPORTANTE
    
    if isinstance(valor_preferencia, bool):
        return valor_preferencia is True
        
    if isinstance(valor_preferencia, str):
        # Asume que tienes una función is_yes() como en el código original
        return is_yes(valor_preferencia)

    # MEJORA: Lógica avanzada para listas. Comprueba si parte de la clave_peso
    # (ej: 'largo' de 'fav_menor_largo_garage') está en la lista de problemas del usuario.
    if isinstance(valor_preferencia, list) and valor_preferencia:
        for item_lista in valor_preferencia:
            if item_lista in clave_peso_original:
                return True
        return False

    # MEJORA: Manejo de Enums u otros objetos.
    # Si no es un tipo primitivo y no es None, asumimos que es una preferencia activa.
    if valor_preferencia is not None and not isinstance(valor_preferencia, (int, float, bool, str, list)):
        return True
    return False

# --- FUNCIÓN PRINCIPAL REFACTORIZADA ---
def _calcular_contribuciones_y_factores_clave_mejorada(
    coche_dict: Dict[str, Any], 
    pesos_normalizados: Dict[str, float],
    preferencias_usuario: PerfilUsuario,
    n_top_positivos: int = 2
) -> Dict[str, Any]:
    """
    Calcula la contribución de cada factor al score y selecciona los más relevantes.
    Versión refactorizada para mayor claridad, robustez y mantenibilidad.
    """
    contribuciones_positivas = []
    
    # MEJORA: El bucle principal es ahora mucho más limpio y fácil de leer.
    for clave_peso, peso_norm in pesos_normalizados.items():
        if not (UMBRAL_PESO_MINIMO < peso_norm < 1.0):
            continue

        clave_feature_scaled = _get_clave_feature_scaled(clave_peso)
        valor_escalado_coche = coche_dict.get(clave_feature_scaled)

        # 1. Comprobar si la característica es destacada en el coche
        if valor_escalado_coche is None or valor_escalado_coche <= UMBRAL_FEATURE_DESTACADA:
            continue

        # 2. Comprobar si la característica es relevante para el usuario
        if clave_peso not in MAPA_PESOS_A_INFO_EXPLICACION:
            continue
            
        info_mapa = MAPA_PESOS_A_INFO_EXPLICACION[clave_peso]
        valor_pref_usuario = getattr(preferencias_usuario, info_mapa["pref_usuario_campo"], None)
        
        if not _es_preferencia_activa(valor_pref_usuario, clave_peso):
            continue

        # 3. Si ambas condiciones se cumplen, se añade la contribución
        contribucion_al_score = valor_escalado_coche * peso_norm
        
        # Formatear el texto final (para casos con {valor}, como enums)
        pref_texto_final = info_mapa["pref_usuario_texto_si"]
        if hasattr(valor_pref_usuario, 'value'): # Para Enums
            pref_texto_final = pref_texto_final.replace("{valor}", str(valor_pref_usuario.value))
        
        contribuciones_positivas.append({
            "caracteristica_coche": info_mapa["nombre_amigable_caracteristica"],
            "razon_usuario": pref_texto_final,
            "contrib_score_abs": contribucion_al_score
        })
    
    contribuciones_positivas.sort(key=lambda x: x["contrib_score_abs"], reverse=True)
    
    return {
        "puntos_fuertes": contribuciones_positivas[:n_top_positivos]
        # La lógica de penalizaciones se mantiene fuera, lo cual es correcto.
    }
    
    
# Asumimos que los mapas y constantes de la PARTE 1 están disponibles
# MAPA_PESOS_A_INFO_EXPLICACION, MAPA_AJUSTES_SCORE_A_TEXTO, etc.
def generar_explicacion_coche_mejorada(
    coche_dict_completo: Dict[str, Any], 
    preferencias_usuario: PerfilUsuario,
    pesos_normalizados: Dict[str, float],
    flag_penalizar_lc_comod: bool,
    flag_penalizar_dep_comod: bool,
    flag_penalizar_ant_tec: bool,
    flag_es_zbe: bool,
    flag_aplicar_dist_gen: bool,
    flag_penalizar_puertas: bool,
) -> str:
    """
    Genera una explicación natural y personalizada sobre la recomendación de un coche,
    utilizando un LLM con un contexto enriquecido.
    """
    nombre_coche = coche_dict_completo.get("nombre", "Este vehículo")
    logging.info(f"INFO (Explicacion LLM Mejorada) ► Generando explicación para: {nombre_coche}")

    # --- 1. OBTENER Y FORMATEAR LOS PUNTOS FUERTES (LÓGICA CORREGIDA) ---
    factores_clave_dict = _calcular_contribuciones_y_factores_clave_mejorada(
        coche_dict_completo, pesos_normalizados, preferencias_usuario, n_top_positivos=2
    )
    puntos_fuertes_list = factores_clave_dict.get("puntos_fuertes", [])
    puntos_fuertes_formateados = []
    for punto_fuerte in puntos_fuertes_list:
        # Formato: "destaca por [su buen diseño] ya que tú [valoras la estética]"
        texto_punto_fuerte = f"destaca por {punto_fuerte['caracteristica_coche']} porque {punto_fuerte['razon_usuario']}"
        puntos_fuertes_formateados.append(texto_punto_fuerte)

    # --- 2. IDENTIFICAR LAS PRIORIDADES CLAVE DEL USUARIO (NUEVO Y DINÁMICO) ---
    ## MEJORA: En lugar de una lista estática, detectamos dinámicamente qué es lo más
    ## importante para el usuario basándonos en los pesos más altos de esta recomendación.
    top_pesos = sorted(pesos_normalizados.items(), key=lambda item: item[1], reverse=True)[:2]
    prioridades_clave_usuario = []
    textos_usados = set() # Para evitar duplicados como "aventura" y "aventura extrema"
    for clave_peso, _ in top_pesos:
        if clave_peso in MAPA_PESOS_A_INFO_EXPLICACION:
            # Extraemos la "esencia" de la preferencia del usuario
            texto_pref = MAPA_PESOS_A_INFO_EXPLICACION[clave_peso]["pref_usuario_texto_si"]
            # Simplificamos el texto para que suene más natural
            texto_base = texto_pref.split(" ")[-1] # Ej: "deportivo", "alta", "ti" -> necesitamos refinar
            if "seguridad" in texto_pref: texto_base = "la seguridad"
            elif "confort" in texto_pref: texto_base = "el confort"
            elif "tecnología" in texto_pref: texto_base = "la tecnología"
            elif "deportivo" in texto_pref: texto_base = "un carácter deportivo"
            elif "fiabilidad" in texto_pref: texto_base = "la fiabilidad"
            elif "aventura" in texto_pref: texto_base = "la aventura"
            else: texto_base = "tus prioridades" # Fallback
            
            if texto_base not in textos_usados:
                prioridades_clave_usuario.append(texto_base)
                textos_usados.add(texto_base)
    
    # --- 3. AGRUPAR CONSIDERACIONES ADICIONALES POR TEMÁTICA (NUEVO) ---
    ## MEJORA: En lugar de una lista plana, agrupamos los ajustes. Esto ayuda al LLM
    ## a entender el contexto de cada punto y a tejer una narrativa más coherente.
    consideraciones = []
    
    # Lógica de Conducción y Confort
    if flag_penalizar_lc_comod and coche_dict_completo.get("acceso_low_cost_scaled", 0) >= UMBRAL_LOW_COST_PENALIZABLE_SCALED:
        consideraciones.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_low_cost_por_comodidad_aplicada"])
    if flag_penalizar_dep_comod and coche_dict_completo.get("deportividad_bq_scaled", 0) >= UMBRAL_DEPORTIVIDAD_PENALIZABLE_SCALED:
        consideraciones.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_deportividad_por_comodidad_aplicada"])

    # Lógica Ambiental (con la mejora anti-redundancia)
    distintivo = str(coche_dict_completo.get("distintivo_ambiental", "")).upper()
    es_ocasion = coche_dict_completo.get("ocasion") is True
    if flag_es_zbe:
        if distintivo in ('CERO', '0', 'ECO', 'C'):
            consideraciones.append(MAPA_AJUSTES_SCORE_A_TEXTO["bonus_zbe_distintivo_favorable_aplicado"])
        elif distintivo in ('B', 'NA'):
            consideraciones.append(MAPA_AJUSTES_SCORE_A_TEXTO["penalty_zbe_distintivo_desfavorable_aplicado"])
    elif flag_aplicar_dist_gen:
        if distintivo in ('CERO', '0', 'ECO', 'C'):
            consideraciones.append(MAPA_AJUSTES_SCORE_A_TEXTO["bonus_distintivo_general_favorable_aplicado"])
    # El bonus de ocasión se puede añadir si es relevante para el perfil ecológico
    if flag_aplicar_dist_gen and es_ocasion:
        consideraciones.append(MAPA_AJUSTES_SCORE_A_TEXTO["bonus_ocasion_por_impacto_ambiental_aplicado"])
        
    # Lógica de Antigüedad y Tecnología
    anos_vehiculo = coche_dict_completo.get("anos_vehiculo")
    if flag_penalizar_ant_tec and anos_vehiculo is not None:
        if anos_vehiculo > 10:
            consideraciones.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_antiguedad_mas_10_anos_aplicada"])
        elif anos_vehiculo > 7:
            consideraciones.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_antiguedad_7_a_10_anos_aplicada"])

    # Lógica Práctica (Puertas)
    if flag_penalizar_puertas and coche_dict_completo.get("puertas", 5) <= 3:
        consideraciones.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_puertas_bajas_aplicada"])
        
    # --- 4. CONSTRUIR EL CONTEXTO FINAL PARA EL LLM (ESTRUCTURA MEJORADA) ---
    # MEJORA: Creamos las cadenas de las listas con viñetas ANTES del f-string.
    puntos_fuertes_str = "\n- ".join(puntos_fuertes_formateados) if puntos_fuertes_formateados else "Se ajusta bien a tus criterios."
    consideraciones_str = "\n- ".join(consideraciones) if consideraciones else "Sin consideraciones particulares."
    
    contexto_para_llm = f"""
    ## Perfil del Coche
    - Nombre: {nombre_coche}

    ## Tus Prioridades Clave Detectadas
    - {", ".join(prioridades_clave_usuario) if prioridades_clave_usuario else "Tus preferencias generales"}

    ## Razones Principales de la Recomendación (Puntos Fuertes)
    - {puntos_fuertes_str}

    ## Otras Consideraciones Relevantes (Matices y detalles)
    - {consideraciones_str}
    """
    
    logging.debug(f"DEBUG (Explicacion LLM Mejorada) ► Contexto para LLM:\n{contexto_para_llm}")

    # --- 5. INVOCAR AL LLM Y GESTIONAR LA RESPUESTA (SIN CAMBIOS, YA ERA ROBUSTO) ---
    try:
        messages = [
            SystemMessage(content=system_prompt_explicacion_coche_mejorado), 
            HumanMessage(content=contexto_para_llm) 
        ]
        response = llm_explicacion_coche.invoke(messages)
        explicacion_texto = response.content if hasattr(response, 'content') else str(response)
        logging.info(f"INFO (Explicacion LLM Mejorada) ► Explicación generada: {explicacion_texto}")
        return explicacion_texto.strip()
    except Exception as e:
        logging.error(f"ERROR (Explicacion LLM Mejorada) ► Fallo al generar explicación: {e}")
        traceback.print_exc()
        return "Después de analizar tus preferencias, he encontrado que este coche es una opción muy interesante que se ajusta bien a lo que buscas." # Fallback mejorado




# def generar_explicacion_coche_con_llm(
#     coche_dict_completo: Dict[str, Any], 
#     preferencias_usuario: PerfilUsuario, # Recibe el objeto Pydantic
#     pesos_normalizados: Dict[str, float],
#     flag_penalizar_lc_comod: bool,
#     flag_penalizar_dep_comod: bool,
#     flag_penalizar_ant_tec: bool,
#     flag_es_zbe: bool,
#     flag_aplicar_dist_gen: bool,
#     flag_penalizar_puertas: bool,
# ) -> str:
#     """
#     Genera una explicación de por qué un coche es recomendado, usando un LLM.
#     """
#     logging.info(f"INFO (Explicacion LLM) ► Generando explicación para coche: {coche_dict_completo.get('nombre')}")

#     factores_clave_dict = _calcular_contribuciones_y_factores_clave(
#         coche_dict_completo, pesos_normalizados, preferencias_usuario, n_top_positivos=3
#     )

#     #puntos_fuertes_para_prompt_list = []
#     # --- CONSTRUIR LISTA DE PENALIZACIONES/BONUS RELEVANTES APLICADOS ---
#     ajustes_score_textos = []
    
#     # 1. Penalizaciones por Comodidad
#     if flag_penalizar_lc_comod and coche_dict_completo.get("acceso_low_cost_scaled", 0) >= UMBRAL_LOW_COST_PENALIZABLE_SCALED:
#         ajustes_score_textos.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_low_cost_por_comodidad_aplicada"])
#     if flag_penalizar_dep_comod and coche_dict_completo.get("deportividad_bq_scaled", 0) >= UMBRAL_DEPORTIVIDAD_PENALIZABLE_SCALED: # Asume que tienes 'deportividad_bq_scaled'
#         ajustes_score_textos.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_deportividad_por_comodidad_aplicada"])
    
#     # 2. Penalizaciones por Antigüedad (si tecnología es alta)
#     anos_vehiculo = coche_dict_completo.get("anos_vehiculo")
#     if flag_penalizar_ant_tec and anos_vehiculo is not None:
#         if anos_vehiculo > 10:
#             ajustes_score_textos.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_antiguedad_mas_10_anos_aplicada"])
#         elif anos_vehiculo > 7:
#             ajustes_score_textos.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_antiguedad_7_a_10_anos_aplicada"])
#         elif anos_vehiculo > 5:
#             ajustes_score_textos.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_antiguedad_5_a_7_anos_aplicada"])

#     # 3. Lógica Distintivo Ambiental (General y Ocasión)
#     distintivo = str(coche_dict_completo.get("distintivo_ambiental", "")).upper() # Asegurar que sea string y mayúsculas
#     es_ocasion = coche_dict_completo.get("ocasion") is True

#     if flag_aplicar_dist_gen: # Activado por alto rating de impacto ambiental
#         if distintivo in ('CERO', '0', 'ECO', 'C'):
#             ajustes_score_textos.append(MAPA_AJUSTES_SCORE_A_TEXTO["bonus_distintivo_general_favorable_aplicado"])
#         elif distintivo in ('B', 'NA'):
#             ajustes_score_textos.append(MAPA_AJUSTES_SCORE_A_TEXTO["penalty_distintivo_general_desfavorable_aplicado"])
        
#         if es_ocasion:
#             ajustes_score_textos.append(MAPA_AJUSTES_SCORE_A_TEXTO["bonus_ocasion_por_impacto_ambiental_aplicado"])

#     # 4. Lógica Distintivo Ambiental por ZBE (tiene prioridad o se añade)
#     if flag_es_zbe:
#         if distintivo in ('CERO', '0', 'ECO', 'C'):
#             # Podríamos tener un texto diferente si queremos evitar redundancia con el bonus general
#             # o asumir que el prompt del LLM lo manejará.
#             # Por ahora, si es ZBE y favorable, el prompt puede enfatizar esto.
#             # La función MAPA_AJUSTES_SCORE_A_TEXTO ya tiene textos específicos para ZBE.
#             ajustes_score_textos.append(MAPA_AJUSTES_SCORE_A_TEXTO["bonus_zbe_distintivo_favorable_aplicado"])
#         elif distintivo in ('B', 'NA'):
#             ajustes_score_textos.append(MAPA_AJUSTES_SCORE_A_TEXTO["penalty_zbe_distintivo_desfavorable_aplicado"])
            
#     # 5. Penalización por Puertas Bajas
#     # Necesitamos saber si la penalización de puertas se aplicó.
#     # `buscar_coches_bq` calcula `puertas_penalty`. Si este valor es negativo, se aplicó.
#     # Necesitaríamos que `buscar_coches_bq` devuelva `puertas_penalty` con el coche.
#     # O, más simple, si el flag `penalizar_puertas` está activo Y el coche tiene pocas puertas:
#     if flag_penalizar_puertas and coche_dict_completo.get("puertas", 5) <= 3: # Asumiendo que BQ devuelve 'puertas'
#         ajustes_score_textos.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_puertas_bajas_aplicada"])
#     # --- FIN CONSTRUCCIÓN DE PENALIZACIONES/BONUS ---
#     # Formatear preferencias relevantes del usuario para el prompt
#     prefs_resumidas_para_prompt_list = []
#     # Ejemplo: Tomar los N ratings más altos o las N preferencias "sí" más importantes
#     # Esta parte necesita ser más robusta para seleccionar las preferencias más relevantes para el coche específico.
#     # Por ahora, una lista simple basada en ratings altos:
#     if preferencias_usuario.rating_seguridad and preferencias_usuario.rating_seguridad >= 7:
#         prefs_resumidas_para_prompt_list.append(f"alta seguridad (calificada con {preferencias_usuario.rating_seguridad}/10)")
#     if preferencias_usuario.rating_comodidad and preferencias_usuario.rating_comodidad >= 7:
#         prefs_resumidas_para_prompt_list.append(f"gran comodidad (calificada con {preferencias_usuario.rating_comodidad}/10)")
#     if preferencias_usuario.rating_tecnologia_conectividad and preferencias_usuario.rating_tecnologia_conectividad >= 7:
#         prefs_resumidas_para_prompt_list.append(f"buena tecnología (calificada con {preferencias_usuario.rating_tecnologia_conectividad}/10)")
#     if not prefs_resumidas_para_prompt_list:
#         prefs_resumidas_para_prompt_list.append("tus criterios generales")


#     # Construir el contexto para el LLM
#     contexto_para_llm = f"""
#     Nombre del Coche: {coche_dict_completo.get("nombre", "Este vehículo")}
#     Preferencias Relevantes del Usuario: {", ".join(prefs_resumidas_para_prompt_list)}.
#     Puntos Fuertes del Coche para este Usuario:
#     {". ".join(ajustes_score_textos) if ajustes_score_textos else "Se ajusta bien en general."}
#     Consideraciones Adicionales (Ajustes al Score):
#     {". ".join(ajustes_score_textos) if ajustes_score_textos else "Ningún ajuste particular destacable."}
#     """
    
#     logging.debug(f"DEBUG (Explicacion LLM) ► Contexto para LLM:\n{contexto_para_llm}")

#     try:
#         messages_for_explanation = [
#             SystemMessage(content=system_prompt_explicacion_coche), 
#             HumanMessage(content=contexto_para_llm) 
#         ]
        
#         response = llm_explicacion_coche.invoke(messages_for_explanation)
        
#         explicacion_texto = response.content if hasattr(response, 'content') else str(response)
#         logging.info(f"INFO (Explicacion LLM) ► Explicación generada para {coche_dict_completo.get('nombre')}: {explicacion_texto}")
#         return explicacion_texto.strip()
#     except Exception as e:
#         logging.error(f"ERROR (Explicacion LLM) ► Fallo al generar explicación para {coche_dict_completo.get('nombre')}: {e}")
#         traceback.print_exc()
#         return "Es una opción interesante que se ajusta a varias de tus preferencias clave." # Fallback







