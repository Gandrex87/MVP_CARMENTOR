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
from pydantic import BaseModel, Field


# Mapeo de claves de peso a información para la explicación
# Esta es una versión simplificada, necesitarás el mapa completo que ya tienes
# en _generar_explicacion_simple_coche o uno similar.
MAPA_PESOS_A_INFO_EXPLICACION = {
    "batalla": {
        "nombre_amigable_caracteristica":    "una buena batalla (espacio interior)",
        "pref_usuario_campo":                 "altura_mayor_190",
        "pref_usuario_texto_si":              "eres una persona alta"
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


# =================================================================================
# 1. ENUMS Y CLASES (Simulados para que el código sea ejecutable)
# =================================================================================


# Simulación de Enums y Clases que usarías en tu proyecto real
class FrecuenciaUso(str): pass
class DistanciaTrayecto(str): pass
class FrecuenciaViajesLargos(str): pass
class TipoUsoProfesional(str): pass
class DimensionProblematica(str): pass
class NivelAventura:
    ninguna = "ninguna"
    ocasional = "ocasional"
    extrema = "extrema"
class EstiloConduccion:
    tranquilo = "tranquilo"
    deportivo = "deportivo"
    mixto = "mixto"
class Transmision(str): pass

class PerfilUsuario(BaseModel):
    apasionado_motor: Optional[str] = None
    valora_estetica: Optional[str] = None
    prefiere_diseno_exclusivo: Optional[str] = None
    aventura: Optional[str] = Field(default=NivelAventura.ninguna) # Usamos str para simplicidad aquí
    altura_mayor_190: Optional[str] = None
    rating_fiabilidad_durabilidad: Optional[int] = None
    rating_seguridad: Optional[int] = None
    rating_comodidad: Optional[int] = None
    rating_impacto_ambiental: Optional[int] = None
    rating_tecnologia_conectividad: Optional[int] = None
    prioriza_baja_depreciacion: Optional[str] = None
    transporta_carga_voluminosa: Optional[str] = None
    necesita_espacio_objetos_especiales: Optional[str] = None
    rating_costes_uso: Optional[int] = None
    arrastra_remolque: Optional[str] = None
    problemas_aparcar_calle: Optional[str] = None
    espacio_sobra_garage: Optional[str] = None
    problema_dimension_garage: Optional[List[str]] = None
    estilo_conduccion: Optional[str] = Field(default=EstiloConduccion.mixto)
    # Añade aquí cualquier otro campo de PerfilUsuario que necesites


# =================================================================================
# 2. MAPA REFACTORIZADO Y MEJORADO
# =================================================================================

UMBRAL_RATING_IMPORTANTE = 7

# MEJORA CLAVE: Ahora el mapa contiene una función `condicion_preferencia`
# que permite una lógica de validación mucho más específica y potente.
MAPA_CARACTERISTICAS_A_INFO = {
    "estetica": {
        "nombre_amigable": "un diseño atractivo",
        "campo_perfil": "valora_estetica",
        "condicion_preferencia": lambda v: is_yes(v),
        "texto_razon": "porque valoras la estética"
    },
    "premium": {
        "nombre_amigable": "un carácter premium",
        "campo_perfil": "apasionado_motor",
        "condicion_preferencia": lambda v: is_yes(v),
        "texto_razon": "para conectar con tu pasión por el motor"
    },
    "singular": {
        "nombre_amigable": "un toque de singularidad",
        "campo_perfil": "prefiere_diseno_exclusivo",
        "condicion_preferencia": lambda v: is_yes(v),
        "texto_razon": "porque prefieres un diseño que destaque"
    },
    "altura_libre_suelo": {
        "nombre_amigable": "una excelente altura libre al suelo",
        "campo_perfil": "aventura",
        "condicion_preferencia": lambda v: v in [NivelAventura.ocasional, NivelAventura.extrema],
        "texto_razon": "para tus escapadas de aventura"
    },
    "traccion": {
        "nombre_amigable": "un sistema de tracción total eficaz",
        "campo_perfil": "aventura",
        "condicion_preferencia": lambda v: v in [NivelAventura.ocasional, NivelAventura.extrema],
        "texto_razon": "para darte seguridad en cualquier terreno"
    },
    "reductoras": {
        "nombre_amigable": "capacidades off-road superiores (reductoras)",
        "campo_perfil": "aventura",
        "condicion_preferencia": lambda v: v == NivelAventura.extrema,
        "texto_razon": "para afrontar las rutas más extremas"
    },
    "indice_altura_interior": {
        "nombre_amigable": "un interior espacioso y cómodo",
        "campo_perfil": "altura_mayor_190",
        "condicion_preferencia": lambda v: is_yes(v),
        "texto_razon": "especialmente importante por tu altura"
    },
    "rating_fiabilidad_durabilidad": {
        "nombre_amigable": "una fiabilidad y durabilidad demostradas",
        "campo_perfil": "rating_fiabilidad_durabilidad",
        "condicion_preferencia": lambda v: v is not None and v >= UMBRAL_RATING_IMPORTANTE,
        "texto_razon": "porque la fiabilidad es una de tus máximas prioridades"
    },
    "rating_seguridad": {
        "nombre_amigable": "un nivel de seguridad sobresaliente",
        "campo_perfil": "rating_seguridad",
        "condicion_preferencia": lambda v: v is not None and v >= UMBRAL_RATING_IMPORTANTE,
        "texto_razon": "porque la seguridad es clave para ti y los tuyos"
    },
    "deportividad_style_score": {
        "nombre_amigable": "un comportamiento ágil y deportivo",
        "campo_perfil": "estilo_conduccion",
        "condicion_preferencia": lambda v: v == EstiloConduccion.deportivo,
        "texto_razon": "para que disfrutes de una conducción más dinámica"
    },
    # --- Añadir aquí el resto de tus características siguiendo esta estructura ---
}


# =================================================================================
# 3. FUNCIONES REFACTORIZADAS
# =================================================================================

UMBRAL_PESO_MINIMO = 0.005
UMBRAL_FEATURE_DESTACADA = 0.4

def _get_clave_feature_scaled(clave_peso: str) -> str:
    """Convierte una clave de peso a su correspondiente clave de feature escalada. (Sin cambios)"""
    # ... (la función que ya tenías)
    if clave_peso.startswith("rating_"): return clave_peso.replace("rating_", "") + "_scaled"
    if clave_peso.startswith("fav_menor_"): return clave_peso.replace("fav_menor_", "menor_") + "_scaled"
    if clave_peso.startswith("fav_bajo_"): return clave_peso.replace("fav_", "") + "_scaled"
    if clave_peso == "deportividad_style_score": return "deportividad_style_scaled"
    if clave_peso == "potencia_maxima_style_score": return "potencia_maxima_style_scaled"
    if clave_peso == "par_motor_style_score": return "par_scaled"
    if clave_peso == "ancho_general_score": return "ancho_scaled"
    if clave_peso.endswith("_score"): return clave_peso.replace("_score", "") + "_scaled"
    return clave_peso + "_scaled"


def _calcular_contribuciones_y_factores_clave_refactorizada(
    coche_dict: Dict[str, Any],
    pesos_normalizados: Dict[str, float],
    preferencias_usuario: PerfilUsuario,
    n_top_positivos: int = 2
) -> List[Dict[str, Any]]:
    """
    Calcula los puntos fuertes de un coche para un usuario, usando el nuevo mapa.
    """
    contribuciones_positivas = []

    for clave_peso, peso_norm in pesos_normalizados.items():
        if not (UMBRAL_PESO_MINIMO < peso_norm < 1.0):
            continue

        # 1. Comprobar si la característica existe en nuestro nuevo mapa y en el coche
        if clave_peso not in MAPA_CARACTERISTICAS_A_INFO:
            continue

        info_mapa = MAPA_CARACTERISTICAS_A_INFO[clave_peso]
        clave_feature_scaled = _get_clave_feature_scaled(clave_peso)
        valor_escalado_coche = coche_dict.get(clave_feature_scaled)

        if valor_escalado_coche is None or valor_escalado_coche <= UMBRAL_FEATURE_DESTACADA:
            continue

        # 2. Usar la función lambda del mapa para validar la preferencia del usuario
        valor_pref_usuario = getattr(preferencias_usuario, info_mapa["campo_perfil"], None)
        
        if not info_mapa["condicion_preferencia"](valor_pref_usuario):
            continue

        # 3. Si todo coincide, se añade la contribución
        contribucion_al_score = valor_escalado_coche * peso_norm
        contribuciones_positivas.append({
            "caracteristica_coche": info_mapa["nombre_amigable"],
            "razon_usuario": info_mapa["texto_razon"],
            "contrib_score_abs": contribucion_al_score
        })

    contribuciones_positivas.sort(key=lambda x: x["contrib_score_abs"], reverse=True)
    return contribuciones_positivas[:n_top_positivos]


def _extraer_prioridades_clave(perfil: PerfilUsuario, limite: int = 2) -> List[str]:
    """
    Inspecciona el perfil del usuario y extrae una lista legible de sus prioridades más importantes.
    """
    prioridades_detectadas = []
    mapa_prioridades = {
        "rating_seguridad": "la alta seguridad",
        "rating_fiabilidad_durabilidad": "la máxima fiabilidad",
        "rating_comodidad": "el confort en viaje",
        "rating_tecnologia_conectividad": "la tecnología y conectividad",
        "rating_costes_uso": "un bajo coste de uso y mantenimiento",
        "rating_impacto_ambiental": "el respeto por el medioambiente",
        "aventura": {
            NivelAventura.extrema: "la aventura más extrema",
            NivelAventura.ocasional: "las escapadas de aventura"
        },
        "estilo_conduccion": {
            EstiloConduccion.deportivo: "la conducción deportiva"
        },
        "apasionado_motor": "la pasión por el motor",
        "prefiere_diseno_exclusivo": "un diseño exclusivo"
    }

    # Procesar ratings primero por ser los más explícitos
    ratings = sorted(
        [(k, getattr(perfil, k)) for k in mapa_prioridades if k.startswith("rating_") and getattr(perfil, k) is not None],
        key=lambda item: item[1],
        reverse=True
    )
    for campo, valor in ratings:
        if len(prioridades_detectadas) < limite and valor >= 8:
            prioridades_detectadas.append(mapa_prioridades[campo])
    
    # Si no hemos llenado con ratings, buscar en otras preferencias clave
    campos_adicionales = ["aventura", "estilo_conduccion", "apasionado_motor", "prefiere_diseno_exclusivo"]
    for campo in campos_adicionales:
        if len(prioridades_detectadas) >= limite: break
        valor_perfil = getattr(perfil, campo, None)
        if not valor_perfil: continue

        if isinstance(mapa_prioridades[campo], dict): # Para enums como Aventura
            if valor_perfil in mapa_prioridades[campo]:
                prioridades_detectadas.append(mapa_prioridades[campo][valor_perfil])
        elif is_yes(valor_perfil): # Para sí/no
            prioridades_detectadas.append(mapa_prioridades[campo])

    return prioridades_detectadas[:limite]


UMBRAL_LOW_COST_PENALIZABLE_SCALED = 0.6
UMBRAL_DEPORTIVIDAD_PENALIZABLE_SCALED = 0.6

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
    Función orquestadora final que usa los componentes refactorizados.
    """
    nombre_coche = coche_dict_completo.get("nombre", "Este vehículo")

    # 1. Extraer prioridades clave directamente del perfil del usuario.
    prioridades_list = _extraer_prioridades_clave(preferencias_usuario, limite=2)
    prioridades_str = " y ".join(prioridades_list)

    # 2. Calcular los puntos fuertes usando la lógica refactorizada.
    puntos_fuertes_list = _calcular_contribuciones_y_factores_clave_refactorizada(
        coche_dict_completo, pesos_normalizados, preferencias_usuario, n_top_positivos=2
    )

    # 3. Formatear los puntos fuertes para el prompt.
    puntos_fuertes_formateados = []
    for punto in puntos_fuertes_list:
        # Ejemplo de formato para el prompt: "Su [característica] es ideal [razón]"
        puntos_fuertes_formateados.append(f"Su **{punto['caracteristica_coche']}** es ideal {punto['razon_usuario']}.")

    # 4. CONSTRUIR LAS CONSIDERACIONES ADICIONALES (LÓGICA DE FLAGS IMPLEMENTADA)
    consideraciones_finales = []
    
    # --- Lógica de Conducción y Confort ---
    if flag_penalizar_lc_comod and coche_dict_completo.get("acceso_low_cost_scaled", 0) >= UMBRAL_LOW_COST_PENALIZABLE_SCALED:
        consideraciones_finales.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_low_cost_por_comodidad_aplicada"])
    if flag_penalizar_dep_comod and coche_dict_completo.get("deportividad_bq_scaled", 0) >= UMBRAL_DEPORTIVIDAD_PENALIZABLE_SCALED:
        consideraciones_finales.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_deportividad_por_comodidad_aplicada"])

    # --- Lógica Ambiental (con prioridad para ZBE para evitar redundancia) ---
    distintivo = str(coche_dict_completo.get("distintivo_ambiental", "")).upper()
    es_ocasion = coche_dict_completo.get("ocasion") is True
    
    if flag_es_zbe:
        if distintivo in ('CERO', '0', 'ECO', 'C'):
            consideraciones_finales.append(MAPA_AJUSTES_SCORE_A_TEXTO["bonus_zbe_distintivo_favorable_aplicado"])
        elif distintivo in ('B', 'NA'):
            consideraciones_finales.append(MAPA_AJUSTES_SCORE_A_TEXTO["penalty_zbe_distintivo_desfavorable_aplicado"])
    elif flag_aplicar_dist_gen:
        if distintivo in ('CERO', '0', 'ECO', 'C'):
            consideraciones_finales.append(MAPA_AJUSTES_SCORE_A_TEXTO["bonus_distintivo_general_favorable_aplicado"])
    
    # El bonus por ser de ocasión se puede añadir si es relevante para el perfil ecológico
    if flag_aplicar_dist_gen and es_ocasion:
        consideraciones_finales.append(MAPA_AJUSTES_SCORE_A_TEXTO["bonus_ocasion_por_impacto_ambiental_aplicado"])
        
    # --- Lógica de Antigüedad y Tecnología ---
    anos_vehiculo = coche_dict_completo.get("anos_vehiculo")
    if flag_penalizar_ant_tec and anos_vehiculo is not None:
        if anos_vehiculo > 10:
            consideraciones_finales.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_antiguedad_mas_10_anos_aplicada"])
        elif anos_vehiculo > 7:
            consideraciones_finales.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_antiguedad_5_a_7_anos_aplicada"])

    # --- Lógica Práctica (Puertas) ---
    # Asume que la necesidad de penalizar puertas ya se ha determinado por el perfil del usuario (ej: tiene hijos)
    if flag_penalizar_puertas and coche_dict_completo.get("puertas", 5) <= 3:
        consideraciones_finales.append(MAPA_AJUSTES_SCORE_A_TEXTO["penaliza_puertas_bajas_aplicada"])
        
    consideraciones_str = "\n- ".join(consideraciones_finales) if consideraciones_finales else "Sin consideraciones destacables."
    # 5. Ensamblar el contexto para el LLM.
    puntos_fuertes_str = "\n- ".join(puntos_fuertes_formateados) if puntos_fuertes_formateados else "Se ajusta bien a tus criterios generales."
    
    contexto_para_llm = f"""
    ## Prioridades Clave del Usuario
    - {prioridades_str if prioridades_str else "Tus preferencias generales"}

    ## Coche Recomendado
    - {nombre_coche}

    ## Argumentos de Venta Principales
    - {puntos_fuertes_str}
    
    ## Otras Consideraciones
    - {consideraciones_str}
    """
    
    print("--- CONTEXTO GENERADO PARA EL LLM ---")
    print(contexto_para_llm)
    print("------------------------------------")
    
    #6. Llamada al LLM (usa tu system prompt de "copywriter experto")
    try:
        messages = [SystemMessage(content=system_prompt_explicacion_coche_mejorado), HumanMessage(content=contexto_para_llm)]
        response = llm_explicacion_coche.invoke(messages)
        return response.content
    except Exception as e:
        logging.error(f"Error en LLM: {e}")
        return "Este coche es una excelente opción que se ajusta a tus necesidades."

    # Devolvemos el contexto para la depuración
    return contexto_para_llm
