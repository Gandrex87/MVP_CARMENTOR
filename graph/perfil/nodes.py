from utils.explanation_generator import generar_explicacion_coche_mejorada # <-- NUEVO IMPORT
from langchain_core.messages import HumanMessage, BaseMessage,AIMessage
from pydantic import ValidationError # Importar para manejo de errores si es necesario
from .state import (EstadoAnalisisPerfil, 
                    PerfilUsuario, ResultadoSoloPerfil , 
                    FiltrosInferidos, ResultadoSoloFiltros,
                    EconomiaUsuario,ResultadoEconomia ,
                    InfoPasajeros, ResultadoPasajeros,
                    InfoClimaUsuario, ResultadoCP, NivelAventura , FrecuenciaUso, DistanciaTrayecto, FrecuenciaViajesLargos
)
from config.llm import llm_solo_perfil, llm_economia, llm_pasajeros, llm_cp_extractor
from prompts.loader import system_prompt_perfil, prompt_economia_structured_sys_msg, system_prompt_pasajeros, system_prompt_cp
from utils.postprocessing import aplicar_postprocesamiento_perfil, aplicar_postprocesamiento_filtros
from utils.validation import check_perfil_usuario_completeness , check_economia_completa, check_pasajeros_completo
from utils.formatters import formatear_preferencias_en_tabla
from utils.weights import compute_raw_weights, normalize_weights
from utils.bigquery_tools import buscar_coches_bq
from utils.bq_data_lookups import obtener_datos_climaticos_por_cp # IMPORT para la función de búsqueda de clima ---
from utils.conversion import is_yes 
from utils.bq_logger import log_busqueda_a_bigquery
from utils.sanitize_dict_for_json import sanitize_dict_for_json
from utils.question_bank import QUESTION_BANK
import traceback
from langchain_core.runnables import RunnableConfig
import pandas as pd
from utils.enums import EstiloConduccion
import json # Para construir el contexto del prompt
from typing import Literal, Optional ,Dict, Any
from config.settings import (MAPA_RATING_A_PREGUNTA_AMIGABLE, UMBRAL_COMODIDAD_PARA_PENALIZAR_FLAGS, UMBRAL_TECNOLOGIA_PARA_PENALIZAR_ANTIGUEDAD_FLAG, UMBRAL_IMPACTO_AMBIENTAL_PARA_LOGICA_DISTINTIVO_FLAG, UMBRAL_COMODIDAD_PARA_FAVORECER_CARROCERIA)
import random
import logging

# --- Configuración de Logging ---
logger = logging.getLogger(__name__)  # ayuda a tener logs mas claros INFO:graph.perfil.nodes:Calculando flags dinámicos...

# En graph/nodes.py

# --- INICIO: NUEVOS NODOS PARA ETAPA DE CÓDIGO POSTAL ---

# En graph/perfil/nodes.py
def preguntar_cp_inicial_node(state: EstadoAnalisisPerfil) -> dict:
    print("--- Ejecutando Nodo: preguntar_cp_inicial_node ---")
    mensaje_pendiente = state.get("pregunta_pendiente")
    historial_actual = state.get("messages", [])
    historial_nuevo = list(historial_actual) # Crear copia

    mensaje_a_mostrar = "Por favor, introduce tu código postal de 5 dígitos." # Fallback muy básico

    if mensaje_pendiente and mensaje_pendiente.strip():
        mensaje_a_mostrar = mensaje_pendiente
        print(f"DEBUG (Preguntar CP Inicial) ► Usando mensaje pendiente: {mensaje_a_mostrar}")
    else:
        # Esto podría pasar si validar_cp_node no puso un mensaje de fallback
        # cuando tipo_mensaje_cp_llm era None o inesperado.
        print("WARN (Preguntar CP Inicial) ► No había mensaje pendiente válido, usando fallback.")

    ai_msg = AIMessage(content=mensaje_a_mostrar)
    if not historial_actual or historial_actual[-1].content != ai_msg.content:
        historial_nuevo.append(ai_msg)
        print(f"DEBUG (Preguntar CP Inicial) ► Mensaje final añadido: {mensaje_a_mostrar}")
    else:
        print("DEBUG (Preguntar CP Inicial) ► Mensaje duplicado, no se añade.")

    # Devolver solo los campos modificados
    return {
        "messages": historial_nuevo,
        "pregunta_pendiente": None # Siempre limpiar
    }


def recopilar_cp_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Llama a llm_cp_extractor para obtener el código postal del usuario.
    Guarda el mensaje del LLM (pregunta de aclaración o confirmación) 
    y el CP extraído (si lo hay) en el estado.
    """
    print("--- Ejecutando Nodo: recopilar_cp_node ---")
    historial = state.get("messages", [])
    
    # No necesitamos la guarda de AIMessage aquí si este es el primer nodo real
    # o si el nodo anterior (preguntar_cp_inicial) ya es un AIMessage.
    # Si el flujo es START -> recopilar_cp_node, no habrá AIMessage previo.
    
    codigo_postal_extraido_llm = None
    contenido_msg_llm = "Lo siento, no pude procesar tu código postal en este momento." # Default
    tipo_msg_llm = "ERROR"

    try:
        # llm_cp_extractor devuelve ResultadoCP
        response: ResultadoCP = llm_cp_extractor.invoke(
            [system_prompt_cp, *historial], # Pasa el prompt y el historial
            config={"configurable": {"tags": ["llm_cp_extractor"]}} 
        )
        print(f"DEBUG (CP) ► Respuesta llm_cp_extractor: {response}")

        codigo_postal_extraido_llm = response.codigo_postal_extraido
        tipo_msg_llm = response.tipo_mensaje
        contenido_msg_llm = response.contenido_mensaje
        
        print(f"DEBUG (CP) ► CP extraído por LLM: '{codigo_postal_extraido_llm}', Tipo Mensaje: '{tipo_msg_llm}'")

    except ValidationError as e_val:
        print(f"ERROR (CP) ► Error de Validación Pydantic en llm_cp_extractor: {e_val}")
        contenido_msg_llm = f"Hubo un problema al procesar tu código postal (formato inválido): {e_val}. ¿Podrías intentarlo de nuevo?"
        tipo_msg_llm = "PREGUNTA_ACLARACION" # Forzar pregunta si hay error de validación
    except Exception as e:
        print(f"ERROR (CP) ► Fallo general al invocar llm_cp_extractor: {e}")
        traceback.print_exc()
        # contenido_msg_llm ya tiene un default de error

    # Guardar el CP extraído temporalmente en el estado para validación,
    # y el mensaje del LLM en pregunta_pendiente.
    # El CP final validado se guardará en state['codigo_postal_usuario'] en el nodo de validación.
    return {
        #**state,
        "pregunta_pendiente": contenido_msg_llm,
        "codigo_postal_extraido_temporal": codigo_postal_extraido_llm,
        "tipo_mensaje_cp_llm": tipo_msg_llm
    }

def validar_cp_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Valida el código postal extraído por el LLM.
    Si es válido, lo guarda en state['codigo_postal_usuario'].
    Si no es válido, prepara para re-preguntar.
    Devuelve una clave para la arista condicional: 'cp_valido' o 'repreguntar_cp'.
    """
    print("--- Ejecutando Nodo: validar_cp_node ---")
    cp_extraido = state.get("codigo_postal_extraido_temporal")
    tipo_mensaje_cp_llm = state.get("tipo_mensaje_cp_llm")
    
    decision = "repreguntar_cp" # Por defecto, repreguntar
    cp_validado_para_estado = None
    mensaje_para_siguiente_pregunta = state.get("pregunta_pendiente") # Mensaje del LLM

    if tipo_mensaje_cp_llm == "CP_OBTENIDO":
        if cp_extraido and cp_extraido.isdigit() and len(cp_extraido) == 5:
            print(f"DEBUG (CP Validation) ► CP '{cp_extraido}' parece válido. Procediendo a buscar clima.")
            cp_validado_para_estado = cp_extraido
            decision = "cp_valido_listo_para_clima"
            # No necesitamos un mensaje pendiente si el CP es válido y el LLM ya confirmó
            # o dio mensaje vacío. El siguiente nodo (buscar_info_clima) no necesita pregunta_pendiente.
            mensaje_para_siguiente_pregunta = None 
        elif cp_extraido is None and tipo_mensaje_cp_llm == "CP_OBTENIDO":
            # Caso donde el usuario se negó a dar CP, y el LLM lo manejó (según prompt)
            print("DEBUG (CP Validation) ► Usuario no proporcionó CP, pero LLM manejó la situación. Avanzando sin CP.")
            decision = "cp_valido_listo_para_clima" # Avanza, pero cp_validado_para_estado será None
            mensaje_para_siguiente_pregunta = None
        else:
            # El LLM dijo que obtuvo CP, pero no es válido en formato
            print(f"WARN (CP Validation) ► LLM indicó CP_OBTENIDO, pero CP '{cp_extraido}' es inválido. Repreguntando.")
            # El mensaje_para_siguiente_pregunta ya debería ser la pregunta de aclaración del LLM
            # Si no lo es, el nodo preguntar_cp_node debería tener un fallback.
            if not mensaje_para_siguiente_pregunta or mensaje_para_siguiente_pregunta.strip() == "":
                 mensaje_para_siguiente_pregunta = "El código postal no parece correcto. ¿Podrías darme los 5 dígitos de tu CP?"
            decision = "repreguntar_cp"
            
    elif tipo_mensaje_cp_llm == "PREGUNTA_ACLARACION":
        print("DEBUG (CP Validation) ► LLM necesita aclarar CP. Repreguntando.")
        # mensaje_para_siguiente_pregunta ya contiene la pregunta del LLM
        decision = "repreguntar_cp"
    else: # ERROR o tipo inesperado
        print(f"ERROR (CP Validation) ► Tipo de mensaje LLM inesperado o error: '{tipo_mensaje_cp_llm}'. Repreguntando por seguridad.")
        mensaje_para_siguiente_pregunta = "Hubo un problema con el código postal. ¿Podrías intentarlo de nuevo con 5 dígitos?"
        decision = "repreguntar_cp"

    # Actualizar el estado con el CP validado (si lo hay) y la decisión para el router
    # Limpiar los campos temporales
    return {
        "codigo_postal_usuario": cp_validado_para_estado,
        "pregunta_pendiente": mensaje_para_siguiente_pregunta,
        "codigo_postal_extraido_temporal": None,
        "tipo_mensaje_cp_llm": None,
        "_decision_cp_validation": decision
    }

def buscar_info_clima_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Si hay un código postal válido, busca la información climática en BQ.
    Actualiza state['info_clima_usuario'].
    """
    print("--- Ejecutando Nodo: buscar_info_clima_node ---")
    cp_usuario = state.get("codigo_postal_usuario")
    info_clima_calculada = None # Default

    if cp_usuario:
        print(f"DEBUG (Clima) ► Buscando datos climáticos para CP: {cp_usuario}")
        try:
            info_clima_calculada = obtener_datos_climaticos_por_cp(cp_usuario)
            if info_clima_calculada and info_clima_calculada.cp_valido_encontrado:
                print(f"DEBUG (Clima) ► Datos climáticos encontrados: {info_clima_calculada.model_dump()}")
            elif info_clima_calculada: # cp_valido_encontrado fue False
                 print(f"WARN (Clima) ► CP {cp_usuario} procesado por BQ pero no arrojó datos de zona específicos o no se encontró.")
                 # info_clima_calculada tendrá los booleanos en False y cp_valido_encontrado=False
            else: # La función devolvió None (error en la función)
                 print(f"ERROR (Clima) ► obtener_datos_climaticos_por_cp devolvió None para CP {cp_usuario}.")
                 info_clima_calculada = InfoClimaUsuario(codigo_postal_consultado=cp_usuario, cp_valido_encontrado=False)
        except Exception as e_clima:
            print(f"ERROR (Clima) ► Fallo al buscar info de clima: {e_clima}")
            traceback.print_exc()
            info_clima_calculada = InfoClimaUsuario(codigo_postal_consultado=cp_usuario, cp_valido_encontrado=False) # Guardar con error
    else:
        print("INFO (Clima) ► No hay código postal de usuario, omitiendo búsqueda de clima.")
        # Crear un objeto InfoClimaUsuario con defaults (todos False) si no hay CP
        info_clima_calculada = InfoClimaUsuario(cp_valido_encontrado=False) 

    return {"info_clima_usuario": info_clima_calculada}

# --- FIN NUEVOS NODOS PARA ETAPA DE CÓDIGO POSTAL ---

# --- Etapa 1: Recopilación de Preferencias del Usuario ---



# def recopilar_preferencias_node(state: EstadoAnalisisPerfil) -> dict:
#     """
#     Procesa entrada humana, llama a llm_solo_perfil, actualiza preferencias_usuario,
#     y guarda el contenido del mensaje devuelto en 'pregunta_pendiente'.
#     Maneja errores de validación de Pydantic para ratings fuera de rango.
#     """
#     print("--- Ejecutando Nodo: recopilar_preferencias_node ---")
#     logging.debug("--- Ejecutando Nodo: recopilar_preferencias_node ---")
    
#     historial = state.get("messages", [])
#     # Obtener el estado actual de preferencias. Si no existe, inicializar uno nuevo.
#     preferencias_actuales_obj = state.get("preferencias_usuario") or PerfilUsuario()

#     # Si el último mensaje es de la IA, no llamar al LLM de nuevo.
#     if historial and isinstance(historial[-1], AIMessage):
#         logging.debug("(Perfil) ► Último mensaje es AIMessage, omitiendo llamada a llm_solo_perfil.")
#         return {"pregunta_pendiente": state.get("pregunta_pendiente")}

#     logging.debug("(Perfil) ► Último mensaje es HumanMessage o historial vacío, llamando a llm_solo_perfil...")
    
#     # Inicializar variables para la salida del nodo
#     preferencias_para_actualizar_estado = preferencias_actuales_obj # Default: mantener las actuales si todo falla
#     mensaje_para_pregunta_pendiente = "Lo siento, tuve un problema técnico al procesar tus preferencias." # Default

#     try:
#         response: ResultadoSoloPerfil = llm_solo_perfil.invoke(
#             [system_prompt_perfil, *historial],
#             config={"configurable": {"tags": ["llm_solo_perfil"]}} 
#         )
#         logging.debug(f"DEBUG (Perfil) ► Respuesta llm_solo_perfil: {response}")
#         # --- FIN DEL BLOQUE DE DEPURACIÓN ---
        
#         preferencias_del_llm = response.preferencias_usuario # Objeto PerfilUsuario del LLM
#         mensaje_para_pregunta_pendiente = response.contenido_mensaje # Mensaje del LLM

#         # Aplicar post-procesamiento a las preferencias obtenidas del LLM
#         if preferencias_del_llm is None: # Si el LLM no devolvió un objeto de preferencias
#             logging.warning("WARN (Perfil) ► llm_solo_perfil devolvió preferencias_usuario como None.")
#             preferencias_del_llm = PerfilUsuario() # Usar uno vacío para el post-procesador

#         preferencias_post_proc = aplicar_postprocesamiento_perfil(preferencias_del_llm)
        
#         if preferencias_post_proc is not None:
#             preferencias_para_actualizar_estado = preferencias_post_proc
#             logging.debug(f"DEBUG (Perfil) ► Preferencias TRAS post-procesamiento: {preferencias_para_actualizar_estado.model_dump_json(indent=2) if hasattr(preferencias_para_actualizar_estado, 'model_dump_json') else preferencias_para_actualizar_estado}")
#         else:
#             logging.warning("WARN (Perfil) ► aplicar_postprocesamiento_perfil devolvió None. Usando preferencias del LLM sin post-procesar (o las actuales si LLM falló).")
#             preferencias_para_actualizar_estado = preferencias_del_llm if preferencias_del_llm else preferencias_actuales_obj

#     except ValidationError as e_val:
#         logging.error(f"ERROR (Perfil) ► Error de Validación Pydantic en llm_solo_perfil: {e_val.errors()}")
        
#         custom_error_message = None
#         campo_rating_erroneo_para_reset = None
#         preferencias_para_reset = preferencias_actuales_obj.model_copy(deep=True) # Trabajar sobre una copia de las actuales

#         for error in e_val.errors():
#             loc = error.get('loc', ())
#             # El error de Pydantic v2 para modelos anidados puede tener 'preferencias_usuario' como primer elemento de 'loc'
#             if len(loc) > 0 and str(loc[0]) == 'preferencias_usuario' and len(loc) > 1 and str(loc[1]).startswith('rating_'):
#                 campo_rating = str(loc[1])
#                 tipo_error_pydantic = error.get('type')
#                 valor_input = error.get('input')

#                 if tipo_error_pydantic in ['less_than_equal', 'greater_than_equal', 'less_than', 'greater_than', 'finite_number', 'int_parsing']: # Añadir int_parsing
#                     nombre_amigable = MAPA_RATING_A_PREGUNTA_AMIGABLE.get(campo_rating, f"el campo '{campo_rating}'")
#                     custom_error_message = (
#                         f"Para {nombre_amigable}, necesito una puntuación entre 0 y 10. "
#                         f"Parece que ingresaste '{valor_input}'. ¿Podrías darme un valor en la escala de 0 a 10, por favor?"
#                     )
#                     campo_rating_erroneo_para_reset = campo_rating
#                     break 
        
#         if custom_error_message:
#             mensaje_para_pregunta_pendiente = custom_error_message
#             if campo_rating_erroneo_para_reset and hasattr(preferencias_para_reset, campo_rating_erroneo_para_reset):
#                 setattr(preferencias_para_reset, campo_rating_erroneo_para_reset, None)
#                 logging.debug(f"DEBUG (Perfil) ► Campo erróneo '{campo_rating_erroneo_para_reset}' reseteado a None.")
#             preferencias_para_actualizar_estado = preferencias_para_reset # Usar la versión con el campo reseteado
#         else:
#             error_msg_detalle = e_val.errors()[0]['msg'] if e_val.errors() else 'Error desconocido'
#             mensaje_para_pregunta_pendiente = f"Hubo un problema al entender tus preferencias (formato inválido). ¿Podrías reformular? Detalle: {error_msg_detalle}"
#             preferencias_para_actualizar_estado = preferencias_actuales_obj # Revertir a las preferencias antes de la llamada LLM

#     except Exception as e_general:
#         logging.error(f"ERROR (Perfil) ► Fallo general al invocar llm_solo_perfil o en post-procesamiento: {e_general}", exc_info=True)
#         mensaje_para_pregunta_pendiente = "Lo siento, tuve un problema técnico al procesar tus preferencias. ¿Podríamos intentarlo de nuevo con la última pregunta?"
#         preferencias_para_actualizar_estado = preferencias_actuales_obj # Revertir a las preferencias antes de la llamada LLM

#     # Asegurar que pregunta_pendiente tenga un valor si no se estableció
#     if not mensaje_para_pregunta_pendiente or not mensaje_para_pregunta_pendiente.strip():
#         # Esto podría pasar si el LLM devuelve tipo_mensaje=CONFIRMACION y contenido_mensaje=""
#         # pero el perfil aún no está completo según check_perfil_usuario_completeness.
#         # En ese caso, el nodo preguntar_preferencias_node usará su fallback.
#         logging.debug(f"DEBUG (Perfil) ► No hay mensaje específico para pregunta_pendiente, se limpiará o usará fallback.")
#         mensaje_para_pregunta_pendiente = None
#     logging.debug(f"DEBUG (Perfil) ► Estado preferencias_usuario a actualizar: {preferencias_para_actualizar_estado.model_dump_json(indent=2) if hasattr(preferencias_para_actualizar_estado, 'model_dump_json') else None}")
#     logging.debug(f"DEBUG (Perfil) ► Guardando mensaje para pregunta_pendiente: {mensaje_para_pregunta_pendiente}")
        
#     return {
#         "preferencias_usuario": preferencias_para_actualizar_estado,
#         "pregunta_pendiente": mensaje_para_pregunta_pendiente
#     }


def recopilar_preferencias_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Procesa la entrada del usuario, llama al LLM para extraer nueva información,
    y FUSIONA esa nueva información con el perfil existente para evitar la pérdida de estado.
    """
    logging.info("--- Ejecutando Nodo: recopilar_preferencias_node ---")
    
    historial = state.get("messages", [])
    # Obtenemos el perfil completo que ya tenemos guardado.
    preferencias_actuales_obj = state.get("preferencias_usuario") or PerfilUsuario()
    
    # 🔍 DEBUGGING: Log del estado inicial
    logging.info(f"DEBUG (Perfil) ► Estado inicial del perfil: {preferencias_actuales_obj.model_dump_json(indent=2) if preferencias_actuales_obj else 'None'}")
    logging.info(f"DEBUG (Perfil) ► Historial tiene {len(historial)} mensajes")
    
    # 🚨 CAMBIO CRÍTICO: Condición más específica para evitar pérdida de estado
    if historial and isinstance(historial[-1], AIMessage):
        logging.debug("(Perfil) ► Último mensaje es AIMessage, omitiendo llamada a llm_solo_perfil.")
        # ✅ IMPORTANTE: Siempre retornar el perfil actual para evitar pérdida de estado
        return {
            "preferencias_usuario": preferencias_actuales_obj,
            "pregunta_pendiente": state.get("pregunta_pendiente")
        }

    # 🔍 Verificación adicional: ¿hay un mensaje del usuario para procesar?
    mensajes_usuario = [msg for msg in historial if isinstance(msg, HumanMessage)]
    if not mensajes_usuario:
        logging.warning("WARN (Perfil) ► No hay mensajes del usuario para procesar.")
        return {
            "preferencias_usuario": preferencias_actuales_obj,
            "pregunta_pendiente": state.get("pregunta_pendiente")
        }

    logging.debug("(Perfil) ► Llamando a llm_solo_perfil...")
    
    perfil_final_a_guardar = preferencias_actuales_obj
    mensaje_para_siguiente_nodo = "Lo siento, tuve un problema técnico."

    try:
        response: ResultadoSoloPerfil = llm_solo_perfil.invoke(
            [system_prompt_perfil, *historial],
            config={"configurable": {"tags": ["llm_solo_perfil"]}} 
        )
        
        preferencias_del_llm = response.preferencias_usuario
        mensaje_para_siguiente_nodo = response.contenido_mensaje

        # --- ✅ INICIO DE LA LÓGICA DE FUSIÓN INTELIGENTE ---
        if preferencias_del_llm:
            # 1. Creamos una copia del perfil actual para trabajar sobre ella.
            perfil_actualizado = preferencias_actuales_obj.model_copy(deep=True)

            # 2. Convertimos la respuesta del LLM en un diccionario, pero SOLO
            #    con los campos que el LLM realmente ha rellenado (excluye los no establecidos).
            #    exclude_unset=True es crucial aquí.
            nuevos_datos = preferencias_del_llm.model_dump(exclude_unset=True)
            
            if nuevos_datos:
                logging.info(f"DEBUG (Perfil) ► Fusionando nuevos datos del LLM: {nuevos_datos}")
                
                # 🔍 DEBUGGING: Comparación antes y después
                datos_antes = perfil_actualizado.model_dump()
                logging.info(f"DEBUG (Perfil) ► Datos ANTES de fusión: {datos_antes}")
                
                # 3. Usamos .model_copy(update=...) para fusionar los nuevos datos en el perfil existente.
                #    Esto actualiza los campos nuevos sin borrar los antiguos.
                perfil_consolidado = perfil_actualizado.model_copy(update=nuevos_datos)
                
                # 🔍 DEBUGGING: Verificación post-fusión
                datos_despues = perfil_consolidado.model_dump()
                logging.info(f"DEBUG (Perfil) ► Datos DESPUÉS de fusión: {datos_despues}")
                
                # 🔍 Verificación de que no se perdieron datos
                campos_perdidos = []
                for campo, valor in datos_antes.items():
                    if valor is not None and datos_despues.get(campo) is None:
                        campos_perdidos.append(campo)
                
                if campos_perdidos:
                    logging.warning(f"WARN (Perfil) ► Posibles campos perdidos en fusión: {campos_perdidos}")
                    
            else:
                # Si el LLM se ejecutó pero no extrajo datos (ej. por un meta-comentario),
                # mantenemos el perfil tal como estaba.
                logging.info("DEBUG (Perfil) ► El LLM no extrajo nuevos datos, se mantiene el perfil actual.")
                perfil_consolidado = perfil_actualizado
            
            # 4. Aplicamos el post-procesamiento sobre el perfil ya fusionado y completo.
            perfil_final_a_guardar = aplicar_postprocesamiento_perfil(perfil_consolidado)
            
            # 🔍 DEBUGGING: Verificación post-procesamiento
            if perfil_final_a_guardar:
                logging.info(f"DEBUG (Perfil) ► Perfil después del post-procesamiento: {perfil_final_a_guardar.model_dump_json(indent=2)}")
            
        else:
            logging.warning("WARN (Perfil) ► El LLM no devolvió un objeto de preferencias. Se mantiene el perfil actual.")
            perfil_final_a_guardar = preferencias_actuales_obj
        # --- FIN DE LA LÓGICA DE FUSIÓN ---

    except Exception as e_general:
        logging.error(f"ERROR (Perfil) ► Fallo general al invocar llm_solo_perfil o en post-procesamiento: {e_general}", exc_info=True)
        mensaje_para_siguiente_nodo = "Lo siento, tuve un problema técnico. ¿Podríamos intentarlo de nuevo?"
        # 🚨 IMPORTANTE: En caso de error, mantener el perfil actual
        perfil_final_a_guardar = preferencias_actuales_obj

    # 🔍 DEBUGGING: Estado final antes de retornar
    logging.info(f"DEBUG (Perfil) ► Estado final de 'preferencias_usuario' a guardar: {perfil_final_a_guardar.model_dump_json(indent=2) if perfil_final_a_guardar else 'None'}")
    logging.info(f"DEBUG (Perfil) ► Guardando 'pregunta_pendiente': {mensaje_para_siguiente_nodo}")
    
    # 🚨 VERIFICACIÓN FINAL: Asegurarse de que no retornamos None
    if perfil_final_a_guardar is None:
        logging.error("ERROR (Perfil) ► perfil_final_a_guardar es None! Usando perfil actual como fallback.")
        perfil_final_a_guardar = preferencias_actuales_obj
        
    return {
        "preferencias_usuario": perfil_final_a_guardar,
        "pregunta_pendiente": mensaje_para_siguiente_nodo
    }


def validar_preferencias_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Comprueba si el PerfilUsuario en el estado está completo usando una función de utilidad.
    Este nodo es simple: solo realiza la comprobación. La decisión de qué hacer
    (repetir pregunta o avanzar) se tomará en la condición del grafo.
    """
    print("--- Ejecutando Nodo: validar_preferencias_node ---")
    preferencias = state.get("preferencias_usuario")
    
    # Llamar a la función de utilidad para verificar la completitud SOLO del perfil
    # ¡Asegúrate de que esta función exista en utils.validation!
    if check_perfil_usuario_completeness(preferencias):
        print("DEBUG (Perfil) ► Validación: PerfilUsuario considerado COMPLETO.")
    else:
        print("DEBUG (Perfil) ► Validación: PerfilUsuario considerado INCOMPLETO.")

    # La lógica de enrutamiento (volver a preguntar o avanzar a filtros) 
    # se definirá en la arista condicional que salga de este nodo.
    return {**state} 

def _obtener_siguiente_pregunta_perfil(prefs: Optional[PerfilUsuario]) -> str:
    """Genera una pregunta específica basada en el primer campo obligatorio que falta."""
    if prefs is None:  
        return "¿Podrías contarme un poco sobre qué buscas o para qué usarás el coche?"
    # Revisa los campos en orden de prioridad deseado para preguntar
    if prefs.apasionado_motor is None: return random.choice(QUESTION_BANK["apasionado_motor"])
    if prefs.valora_estetica is None: return random.choice(QUESTION_BANK["valora_estetica"])
    if prefs.coche_principal_hogar is None: return random.choice(QUESTION_BANK["coche_principal_hogar"])
    if prefs.frecuencia_uso is None: return random.choice(QUESTION_BANK["frecuencia_uso"])
    if prefs.distancia_trayecto is None: return random.choice(QUESTION_BANK["distancia_trayecto"])
    # Lógica anidada para viajes largos
    if (prefs.distancia_trayecto is not None and
            prefs.distancia_trayecto != DistanciaTrayecto.MAS_150_KM.value and
            prefs.realiza_viajes_largos is None):
        return random.choice(QUESTION_BANK["realiza_viajes_largos"])    
    if is_yes(prefs.realiza_viajes_largos) and prefs.frecuencia_viajes_largos is None:
        return random.choice(QUESTION_BANK["frecuencia_viajes_largos"])
    if prefs.circula_principalmente_ciudad is None: return random.choice(QUESTION_BANK["circula_principalmente_ciudad"])
    if prefs.uso_profesional is None: return random.choice(QUESTION_BANK["uso_profesional"])
    if is_yes(prefs.uso_profesional) and prefs.tipo_uso_profesional is None:
        return random.choice(QUESTION_BANK["tipo_uso_profesional"])
    if prefs.prefiere_diseno_exclusivo is None: return random.choice(QUESTION_BANK["prefiere_diseno_exclusivo"])
    if prefs.altura_mayor_190 is None: return random.choice(QUESTION_BANK["altura_mayor_190"])
    if prefs.transporta_carga_voluminosa is None: return random.choice(QUESTION_BANK["transporta_carga_voluminosa"])
    if is_yes(prefs.transporta_carga_voluminosa) and prefs.necesita_espacio_objetos_especiales is None:
        return random.choice(QUESTION_BANK["necesita_espacio_objetos_especiales"])
    if prefs.arrastra_remolque is None: return random.choice(QUESTION_BANK["arrastra_remolque"])
    if prefs.aventura is None: return random.choice(QUESTION_BANK["aventura"])
    if prefs.estilo_conduccion is None: return random.choice(QUESTION_BANK["estilo_conduccion"])
        # --- ✅ LÓGICA DE GARAJE REFACTORIZADA ---
    if prefs.tiene_garage is None:
        return random.choice(QUESTION_BANK["tiene_garage"]) 
    else:
        # Si ya sabemos si tiene garaje, entramos en las sub-preguntas
        if is_yes(prefs.tiene_garage): # --- CASO SÍ TIENE GARAJE ---
            if prefs.espacio_sobra_garage is None:
                return "¡Genial lo del garaje/plaza! Y dime, ¿el espacio que tienes es amplio y te permite aparcar un coche de cualquier tamaño con comodidad?"
            # Esta sub-pregunta solo se hace si el espacio NO sobra
            elif not is_yes(prefs.espacio_sobra_garage) and not prefs.problema_dimension_garage:
                return "Comprendo que el espacio es ajustado. ¿Cuál es la principal limitación de dimensión?\n ↔️ Ancho\n ↕️ Alto\n ⬅️➡️ Largo"
        else: # --- CASO NO TIENE GARAJE ---
            if prefs.problemas_aparcar_calle is None:
                return "Entendido. En ese caso, al aparcar en la calle, ¿sueles encontrar dificultades por el tamaño del coche o la disponibilidad de sitios?\n\n* ✅ Sí\n* ❌ No",
    # --- FIN NUEVA LÓGICA DE PREGUNTAS ---
    # --- FIN DE LA REFACTORIZACIÓN ---
    if prefs.tiene_punto_carga_propio is None: return random.choice(QUESTION_BANK["tiene_punto_carga_propio"])
    if prefs.solo_electricos is None: return random.choice(QUESTION_BANK["solo_electricos"])
    if prefs.transmision_preferida is None: return random.choice(QUESTION_BANK["transmision_preferida"])
    if prefs.prioriza_baja_depreciacion is None: return random.choice(QUESTION_BANK["prioriza_baja_depreciacion"])
    # Ratings en el orden correcto para coincidir con la validación
    if prefs.rating_fiabilidad_durabilidad is None: return random.choice(QUESTION_BANK["rating_fiabilidad_durabilidad"])
    if prefs.rating_seguridad is None: return random.choice(QUESTION_BANK["rating_seguridad"])
    if prefs.rating_comodidad is None: return random.choice(QUESTION_BANK["rating_comodidad"])
    if prefs.rating_impacto_ambiental is None: return random.choice(QUESTION_BANK["rating_impacto_ambiental"])
    if prefs.rating_costes_uso is None: return random.choice(QUESTION_BANK["rating_costes_uso"])
    if prefs.rating_tecnologia_conectividad is None: return random.choice(QUESTION_BANK["rating_tecnologia_conectividad"])
    # Si todos los campos están llenos, devuelve una pregunta de fallback al azar.
    return random.choice(QUESTION_BANK["fallback"])



def preguntar_preferencias_node(state: EstadoAnalisisPerfil) -> Dict:
    """
    Formula la siguiente pregunta para el perfil de usuario.

    Esta función actúa como el "compositor" final de la respuesta del agente.
    Combina la posible respuesta empática generada por el LLM (en caso de un
    meta-comentario) con la pregunta lógicamente correcta y formateada
    que se obtiene del QUESTION_BANK.
    """
    print("--- Ejecutando Nodo: preguntar_preferencias_node ---")
    
    # 1. Obtenemos todas las piezas necesarias del estado al principio
    preferencias = state.get("preferencias_usuario")
    mensaje_pendiente = state.get("pregunta_pendiente") 
    historial_actual = state.get("messages", [])
    
    mensaje_a_enviar = None

    # 2. Verificamos si el perfil ya está completo
    if not check_perfil_usuario_completeness(preferencias):
        # --- CASO A: El perfil está INCOMPLETO, debemos formular una pregunta ---
        logging.info("DEBUG (Preguntar Perfil) ► Perfil incompleto. Construyendo la siguiente pregunta.")
        
        # Obtenemos la posible frase empática o de bienvenida que generó el LLM.
        # Si no hay nada, es un string vacío.
        frase_contextual = mensaje_pendiente.strip() if (mensaje_pendiente and mensaje_pendiente.strip()) else ""
        
        # Generamos la pregunta correcta y formateada desde nuestra lógica determinista.
        try:
             pregunta_logica = _obtener_siguiente_pregunta_perfil(preferencias)
             logging.info(f"DEBUG (Preguntar Perfil) ► Pregunta generada desde QUESTION_BANK: {pregunta_logica}")
        except Exception as e_fallback:
             logging.error(f"ERROR (Preguntar Perfil) ► Error generando pregunta: {e_fallback}")
             pregunta_logica = "¿Podrías darme más detalles sobre tus preferencias?"

        # Combinamos ambas partes. El .strip() final elimina dobles espacios.
        # Si frase_contextual está vacía, el resultado es solo la pregunta_logica.
        mensaje_a_enviar = f"{frase_contextual} {pregunta_logica}".strip()
        
    else: 
        # --- CASO B: El perfil está COMPLETO ---
        logging.info("DEBUG (Preguntar Perfil) ► Perfil COMPLETO. Preparando mensaje de transición.")
        # Usamos el mensaje de confirmación que ya debería haber generado el LLM.
        if mensaje_pendiente and mensaje_pendiente.strip():
             mensaje_a_enviar = mensaje_pendiente
        else:
             # Si no hay mensaje, usamos uno genérico como fallback.
             mensaje_a_enviar = "¡Perfecto! He recopilado todas tus preferencias. Continuemos."

    # --- 3. Añadimos el mensaje final al historial ---
    historial_nuevo = list(historial_actual)
    if mensaje_a_enviar and mensaje_a_enviar.strip():
        ai_msg = AIMessage(content=mensaje_a_enviar)
        # Evitamos añadir mensajes duplicados
        if not historial_actual or historial_actual[-1].content != ai_msg.content:
            historial_nuevo.append(ai_msg)
            logging.info(f"DEBUG (Preguntar Perfil) ► Mensaje final añadido: {mensaje_a_enviar}")
        else:
             logging.warning("DEBUG (Preguntar Perfil) ► Mensaje final duplicado, no se añade.")
    else:
         logging.error("ERROR (Preguntar Perfil) ► No se determinó ningún mensaje a enviar.")
         ai_msg = AIMessage(content="No estoy seguro de qué preguntar ahora. ¿Puedes darme más detalles?")
         historial_nuevo.append(ai_msg)

    # Devolvemos el estado actualizado
    return {
        **state,
        "messages": historial_nuevo,
        "pregunta_pendiente": None # Limpiamos la pregunta pendiente una vez usada
    }

# --- NUEVA ETAPA: PASAJEROS ---
def recopilar_info_pasajeros_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Llama a llm_pasajeros y FUSIONA la nueva información con el estado existente
    de InfoPasajeros para evitar la pérdida de datos.
    """
    logger.debug("--- Ejecutando Nodo: recopilar_info_pasajeros_node ---")
    
    historial = state.get("messages", [])
    info_pasajeros_actual_obj = state.get("info_pasajeros") or InfoPasajeros()

    if historial and isinstance(historial[-1], AIMessage):
        logger.debug("DEBUG (Pasajeros) ► Último mensaje es AIMessage, omitiendo llamada.")
        return {"pregunta_pendiente": state.get("pregunta_pendiente")}

    logger.debug("DEBUG (Pasajeros) ► Llamando a llm_pasajeros...")
    
    info_pasajeros_final = info_pasajeros_actual_obj
    mensaje_para_siguiente_nodo = "Lo siento, tuve un problema técnico."

    try:
        response: ResultadoPasajeros = llm_pasajeros.invoke(
            [system_prompt_pasajeros, *historial],
            config={"configurable": {"tags": ["llm_pasajeros"]}} 
        )
        logger.debug(f"DEBUG (Pasajeros) ► Respuesta llm_pasajeros: {response}")

        info_pasajeros_del_llm = response.info_pasajeros 
        mensaje_para_siguiente_nodo = response.contenido_mensaje
        
        # --- ✅ INICIO DE LA LÓGICA DE FUSIÓN INTELIGENTE ---
        if info_pasajeros_del_llm:
            # 1. Creamos una copia del estado actual para trabajar sobre ella.
            info_pasajeros_actualizado = info_pasajeros_actual_obj.model_copy(deep=True)

            # 2. Convertimos la respuesta del LLM en un diccionario solo con los
            #    campos que el LLM ha rellenado activamente.
            nuevos_datos = info_pasajeros_del_llm.model_dump(exclude_unset=True)
            
            if nuevos_datos:
                logging.info(f"DEBUG (Pasajeros) ► Fusionando nuevos datos del LLM: {nuevos_datos}")
                # 3. Fusionamos los nuevos datos en nuestro objeto de estado.
                info_pasajeros_consolidado = info_pasajeros_actualizado.model_copy(update=nuevos_datos)
            else:
                logging.info("DEBUG (Pasajeros) ► El LLM no aportó nuevos datos, se mantiene el estado actual.")
                info_pasajeros_consolidado = info_pasajeros_actualizado

            # 4. Aplicamos la lógica de inferencia sobre el objeto ya fusionado y completo.
            if info_pasajeros_consolidado.suele_llevar_acompanantes is False:
                info_pasajeros_consolidado.frecuencia = "nunca"
                info_pasajeros_consolidado.num_ninos_silla = 0
                info_pasajeros_consolidado.num_otros_pasajeros = 0
            elif info_pasajeros_consolidado.suele_llevar_acompanantes is True:
                if info_pasajeros_consolidado.frecuencia_viaje_con_acompanantes:
                    info_pasajeros_consolidado.frecuencia = info_pasajeros_consolidado.frecuencia_viaje_con_acompanantes
            
            info_pasajeros_final = info_pasajeros_consolidado
        else:
            logger.warning("WARN (Pasajeros) ► El LLM no devolvió un objeto InfoPasajeros.")
            info_pasajeros_final = info_pasajeros_actual_obj
        # --- FIN DE LA LÓGICA DE FUSIÓN ---

    except ValidationError as e_val:
        logger.error(f"ERROR (Pasajeros) ► Error de Validación Pydantic: {e_val.errors()}")
        mensaje_para_siguiente_nodo = f"Hubo un problema al procesar la info de pasajeros: {e_val.errors()[0]['msg']}"
        info_pasajeros_final = info_pasajeros_actual_obj

    except Exception as e_general:
        logger.error(f"ERROR (Pasajeros) ► Fallo general: {e_general}", exc_info=True)
        mensaje_para_siguiente_nodo = "Lo siento, tuve un problema técnico."
        info_pasajeros_final = info_pasajeros_actual_obj

    logger.debug(f"DEBUG (Pasajeros) ► Estado info_pasajeros a actualizar: {info_pasajeros_final.model_dump_json(indent=2)}")
        
    return {
        **state,
        "info_pasajeros": info_pasajeros_final,
        "pregunta_pendiente": mensaje_para_siguiente_nodo
    }


def validar_info_pasajeros_node(state: EstadoAnalisisPerfil) -> dict:
    """Nodo simple que comprueba si la información de pasajeros está completa."""
    print("--- Ejecutando Nodo: validar_info_pasajeros_node ---")
    info_pasajeros = state.get("info_pasajeros")
    # Llama a la función de utilidad (que crearemos en el siguiente paso)
    if check_pasajeros_completo(info_pasajeros):
        print("DEBUG (Pasajeros) ► Validación: Info Pasajeros considerada COMPLETA.")
    else:
        print("DEBUG (Pasajeros) ► Validación: Info Pasajeros considerada INCOMPLETA.")
    # No modifica el estado, solo valida para la condición
    return {**state}


def _obtener_siguiente_pregunta_pasajeros(info: Optional[InfoPasajeros]) -> str:
    """
    Genera la siguiente pregunta de fallback para la información de pasajeros,
    siguiendo el nuevo flujo condicional.
    """
    if info is None: # Si no hay objeto InfoPasajeros, empezar por la primera pregunta
        return "¿Sueles viajar con acompañantes en el coche habitualmente?\n\n* ✅ Sí\n* ❌ No"

    # 1. Pregunta inicial
    if info.suele_llevar_acompanantes is None:
        return "¿Sueles viajar con acompañantes en el coche habitualmente?\n\n* ✅ Sí\n* ❌ No"

    # Si la respuesta fue 'no', no debería llegar aquí si el LLM y la validación funcionan,
    # ya que se consideraría completo. Pero por si acaso:
    if info.suele_llevar_acompanantes is False:
        return "Entendido, normalmente viajas solo. (No se necesitan más preguntas de pasajeros)" # O un mensaje para indicar fin de esta etapa

    # Si la respuesta fue 'sí', continuar con las sub-preguntas:
    if info.suele_llevar_acompanantes is True:
        if info.frecuencia_viaje_con_acompanantes is None:
            return "Entendido. Y, ¿con qué frecuencia sueles llevar a estos acompañantes? Por ejemplo, ¿de manera ocasional o frecuentemente?"
        
        # Preguntar por composición si los números finales no están definidos
        # El campo composicion_pasajeros_texto es más una ayuda para el LLM.
        # Nos centramos en los campos numéricos finales.
        if info.num_otros_pasajeros is None: # Podríamos preguntar por composición antes
            frecuencia_texto = info.frecuencia_viaje_con_acompanantes or "con esa frecuencia"
            return (f"De acuerdo, los llevas de forma {frecuencia_texto}. "
                    "Cuéntame un poco más, ¿quiénes suelen ser estos acompañantes y cuántos son en total (sin contarte a ti)? "
                    "Por ejemplo, 'dos adultos', 'un niño y un adulto', 'dos nińos pequeños'.")

        # Preguntar por sillas si hay niños implícitos o explícitos y num_ninos_silla es None
        # Esta lógica puede ser compleja para un fallback simple. El LLM debería manejarla mejor.
        # Si num_otros_pasajeros ya tiene un valor, y num_ninos_silla es None, es el siguiente.
        if info.num_ninos_silla is None:
            # Podríamos intentar ser más inteligentes si 'composicion_pasajeros_texto' mencionó niños.
            # Por ahora, una pregunta genérica si num_otros_pasajeros ya se obtuvo.
            return "¿Alguno de estos acompañantes necesita silla infantil?"

    # Si todos los campos necesarios según el flujo están llenos,
    # esta función no debería ser llamada por un nodo "preguntar" que ya validó.
    # Pero si llega aquí, es un estado inesperado.
    logging.warning("WARN (_obtener_siguiente_pregunta_pasajeros) ► Todos los campos de pasajeros parecen estar completos según esta lógica, pero se pidió una pregunta fallback.")
    return "¿Podrías darme más detalles sobre tus acompañantes habituales?"


def preguntar_info_pasajeros_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Añade la pregunta de seguimiento correcta de pasajeros al historial.
    Verifica si la info de pasajeros está completa ANTES de añadir un mensaje 
    de confirmación. Si no lo está, asegura que se añada una pregunta real.
    """
    print("--- Ejecutando Nodo: preguntar_info_pasajeros_node ---")
    mensaje_pendiente = state.get("pregunta_pendiente") # Mensaje del nodo anterior (LLM)
    info_pasajeros = state.get("info_pasajeros") 
    historial_actual = state.get("messages", [])
    historial_nuevo = list(historial_actual) 
    
    mensaje_a_enviar = None # El mensaje final que añadiremos

    # 1. Comprobar si la info de pasajeros está REALMENTE completa AHORA
    pasajeros_esta_completo = check_pasajeros_completo(info_pasajeros)

    if not pasajeros_esta_completo:
        print("DEBUG (Preguntar Pasajeros) ► Info Pasajeros aún INCOMPLETA según checker.")
        pregunta_generada_fallback = None 

        # Generar la pregunta específica AHORA por si la necesitamos
        try:
             pregunta_generada_fallback = _obtener_siguiente_pregunta_pasajeros(info_pasajeros)
             print(f"DEBUG (Preguntar Pasajeros) ► Pregunta fallback generada: {pregunta_generada_fallback}")
        except Exception as e_fallback:
             print(f"ERROR (Preguntar Pasajeros) ► Error generando pregunta fallback: {e_fallback}")
             pregunta_generada_fallback = "¿Podrías darme más detalles sobre los pasajeros?" 

        # ¿Tenemos un mensaje pendiente del LLM?
        if mensaje_pendiente and mensaje_pendiente.strip():
            # Comprobar si el mensaje pendiente PARECE una confirmación
            # Puedes añadir más frases si detectas otras confirmaciones erróneas
            es_confirmacion = (
                mensaje_pendiente.startswith("¡Perfecto!") or 
                mensaje_pendiente.startswith("¡Genial!") or 
                mensaje_pendiente.startswith("¡Estupendo!") or 
                mensaje_pendiente.startswith("Ok,") or 
                mensaje_pendiente.startswith("Entendido,") # <-- ¡Tu caso reciente!
            )

            if es_confirmacion:
                # IGNORAR la confirmación errónea y USAR el fallback
                print(f"WARN (Preguntar Pasajeros) ► Mensaje pendiente ('{mensaje_pendiente}') parece confirmación, pero pasajeros incompleto. IGNORANDO y usando fallback.")
                mensaje_a_enviar = pregunta_generada_fallback
            else:
                # El mensaje pendiente parece una pregunta válida, la usamos.
                 print(f"DEBUG (Preguntar Pasajeros) ► Usando mensaje pendiente (pregunta LLM): {mensaje_pendiente}")
                 mensaje_a_enviar = mensaje_pendiente
        else:
            # No había mensaje pendiente, usamos la fallback generada.
            print("WARN (Preguntar Pasajeros) ► Nodo ejecutado para preguntar, pero no había mensaje pendiente válido. Generando pregunta fallback.")
            mensaje_a_enviar = pregunta_generada_fallback
            
    else: # La info de pasajeros SÍ está completa
        print("DEBUG (Preguntar Pasajeros) ► Info Pasajeros COMPLETA según checker.")
        # Usamos el mensaje pendiente (que debería ser de confirmación)
        if mensaje_pendiente and mensaje_pendiente.strip():
             print(f"DEBUG (Preguntar Pasajeros) ► Usando mensaje de confirmación pendiente: {mensaje_pendiente}")
             mensaje_a_enviar = mensaje_pendiente
        else:
             print("WARN (Preguntar Pasajeros) ► Info Pasajeros completa pero no había mensaje pendiente. Usando confirmación genérica.")
             mensaje_a_enviar = "¡Entendido! Información de pasajeros registrada."

    # Añadir el mensaje decidido al historial
    if mensaje_a_enviar and mensaje_a_enviar.strip():
        ai_msg = AIMessage(content=mensaje_a_enviar)
        if not historial_actual or historial_actual[-1].content != ai_msg.content:
            historial_nuevo.append(ai_msg)
            print(f"DEBUG (Preguntar Pasajeros) ► Mensaje final añadido: {mensaje_a_enviar}") 
        else:
             print("DEBUG (Preguntar Pasajeros) ► Mensaje final duplicado, no se añade.")
    else:
         print("ERROR (Preguntar Pasajeros) ► No se determinó ningún mensaje a enviar.")
         ai_msg = AIMessage(content="No estoy seguro de qué preguntar sobre pasajeros. ¿Continuamos?")
         historial_nuevo.append(ai_msg)

    # Devolver estado
    return {**state, "messages": historial_nuevo, "pregunta_pendiente": None}



def aplicar_filtros_pasajeros_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Calcula filtros/indicadores basados en la información de pasajeros completa
    y los actualiza en el estado.
    Calcula: plazas_min (siempre), penalizar_puertas_bajas.
    """
    print("--- Ejecutando Nodo: aplicar_filtros_pasajeros_node ---")
    logger.debug("--- Ejecutando Nodo: aplicar_filtros_pasajeros_node ---")
    info_pasajeros_obj = state.get("info_pasajeros") # <-- Renombrado para claridad
    filtros_actuales_obj = state.get("filtros_inferidos") or FiltrosInferidos() 

    # Valores por defecto para los flags penalizar_puertas
    penalizar_p = False 
    
    # Valores para X y Z (default 0)
    X = 0
    Z = 0
    frecuencia = None

    if info_pasajeros_obj: 
        # Usar frecuencia_viaje_con_acompanantes si está, sino la general 'frecuencia'
        # La nueva lógica de InfoPasajeros debería priorizar frecuencia_viaje_con_acompanantes
        frecuencia = info_pasajeros_obj.frecuencia_viaje_con_acompanantes or info_pasajeros_obj.frecuencia
        X = info_pasajeros_obj.num_ninos_silla or 0
        Z = info_pasajeros_obj.num_otros_pasajeros or 0
        logger.debug(f"DEBUG (Aplicar Filtros Pasajeros) ► Info recibida: freq='{frecuencia}', X={X}, Z={Z}")
        print(f"DEBUG (Aplicar Filtros Pasajeros) ► Info recibida: freq='{frecuencia}', X={X}, Z={Z}")
    else:
        logger.error("ERROR (Aplicar Filtros Pasajeros) ► No hay información de pasajeros en el estado. Se usarán defaults.")
        frecuencia = "nunca" # Asumir 'nunca' si no hay info

    plazas_calc = X + Z + 1 
    logger.debug(f"DEBUG (Aplicar Filtros Pasajeros) ► Calculado plazas_min = {plazas_calc}")

    if frecuencia and frecuencia != "nunca": # Nota: frecuencia ahora puede ser 'ocasional' o 'frecuente'
        # Regla Penalizar Puertas Bajas (solo si frecuente y X>=1)
        if frecuencia == "frecuente" and X >= 1:
            penalizar_p = True
            logger.debug("DEBUG (Aplicar Filtros Pasajeros) ► Indicador penalizar_puertas_bajas = True")
    else:
        logger.debug("DEBUG (Aplicar Filtros Pasajeros) ► Frecuencia es 'nunca' o None. penalizar_puertas se mantiene False.")

    update_filtros_dict = {"plazas_min": plazas_calc}
    filtros_actualizados = filtros_actuales_obj.model_copy(update=update_filtros_dict)
    logger.debug(f"DEBUG (Aplicar Filtros Pasajeros) ► Filtros actualizados (con plazas_min): {filtros_actualizados}")
    return {
    **state, # Pasa todas las claves existentes del estado
    "filtros_inferidos": filtros_actualizados, # Sobrescribe solo la clave que has modificado
    "penalizar_puertas_bajas": penalizar_p,      # Y la nueva flag que has calculado
}

# --- Fin Nueva Etapa Pasajeros ---
# --- Fin Etapa 1 ---

# --- Etapa 2: Inferencia y Validación de Filtros Técnicos ---
def construir_filtros_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Construye y refina los filtros de búsqueda de forma determinista
    llamando a la función de post-procesamiento. No utiliza LLM.
    """
    print("--- Ejecutando Nodo: inferir_filtros_node/construir_filtros_node ---")
    
    preferencias_obj = state.get("preferencias_usuario")
    info_clima_obj = state.get("info_clima_usuario")

    # Verificar pre-condiciones
    if not preferencias_obj:
        print("ERROR (Filtros) ► Nodo ejecutado pero 'preferencias_usuario' no existe. No se pueden construir filtros.")
        # Devolvemos un objeto vacío para no romper el flujo
        return {"filtros_inferidos": FiltrosInferidos()}

    print("DEBUG (Filtros) ► Preferencias e info_clima disponibles. Construyendo filtros...")

    filtros_finales = None
    try:
        # 1. Creamos un objeto FiltrosInferidos vacío para empezar.
        #    Ya no dependemos de una inferencia inicial del LLM.
        filtros_iniciales = FiltrosInferidos()
        
        # 2. El único trabajo del nodo es llamar a esta función determinista.
        filtros_finales = aplicar_postprocesamiento_filtros(
            filtros=filtros_iniciales,
            preferencias=preferencias_obj,
            info_clima=info_clima_obj 
        )
        print(f"DEBUG (Filtros) ► Filtros finales construidos: {filtros_finales}")

    except Exception as e_post:
        print(f"ERROR (Filtros) ► Fallo construyendo los filtros: {e_post}")
        traceback.print_exc()
        # En caso de un error inesperado, devolvemos filtros vacíos para seguridad.
        filtros_finales = FiltrosInferidos()
        
    # 3. Devolvemos el estado actualizado. Ya no necesitamos 'pregunta_pendiente'.
    return {
        "filtros_inferidos": filtros_finales
    }

# --- Fin Etapa 2 ---


# --- Etapa 3: Inferencia y Validación de Recopilación de Economía ---
def preguntar_economia_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Toma la pregunta económica pendiente y la añade como AIMessage al historial.
    Limpia la pregunta pendiente. Podría generar pregunta default si no hay pendiente.
    """
    print("--- Ejecutando Nodo: preguntar_economia_node ---")
    pregunta = state.get("pregunta_pendiente")
    historial_actual = state.get("messages", [])
    historial_nuevo = historial_actual 

    mensaje_a_enviar = None

    # Usamos la pregunta guardada si existe
    if pregunta and pregunta.strip():
        print(f"DEBUG (Preguntar Economía) ► Usando pregunta guardada: {pregunta}")
        mensaje_a_enviar = pregunta
    else:
        # Si no había pregunta pendiente (raro, pero podría pasar si el LLM no la generó)
        # podríamos poner una pregunta genérica de economía.
        print("WARN (Preguntar Economía) ► Nodo ejecutado pero no había pregunta pendiente. Usando pregunta genérica.")
        # TODO: Podríamos llamar aquí a _obtener_siguiente_pregunta_economia si tuviéramos esa función
        mensaje_a_enviar = "Necesito algo más de información sobre tu presupuesto. ¿Podrías darme más detalles?"

    # Añadir el mensaje decidido al historial (evitando duplicados)
    if mensaje_a_enviar and mensaje_a_enviar.strip():
        ai_msg = AIMessage(content=mensaje_a_enviar)
        if not historial_actual or historial_actual[-1].content != ai_msg.content:
            historial_nuevo = historial_actual + [ai_msg]
            print(f"DEBUG (Preguntar Economía) ► Mensaje final añadido: {mensaje_a_enviar}")
        else:
             print("DEBUG (Preguntar Economía) ► Mensaje final duplicado, no se añade.")
    else:
         print("WARN (Preguntar Economía) ► No se determinó ningún mensaje a enviar.")

    # Devolver estado: historial actualizado y pregunta_pendiente reseteada
    return {
        **state,
        "messages": historial_nuevo,
        "pregunta_pendiente": None # Limpiar la pregunta pendiente
    }


def recopilar_economia_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Gestiona la recopilación de datos económicos. Llama a llm_economia,
    actualiza el estado 'economia' y guarda la pregunta pendiente.
    """
    print("--- Ejecutando Nodo: recopilar_economia_node ---")
    historial = state.get("messages", [])
    econ_actual = state.get("economia") or EconomiaUsuario() 
    
    print("DEBUG (Economía) ► Llamando a llm_economia...")
    
    mensaje_validacion = None # Inicializar
    economia_actualizada = econ_actual # Inicializar con el estado actual

    # Llamar al LLM de Economía
    try:
        parsed: ResultadoEconomia = llm_economia.invoke(
            [prompt_economia_structured_sys_msg, *historial],
            config={"configurable": {"tags": ["llm_economia"]}} 
        )
        print(f"DEBUG (Economía) ► Respuesta llm_economia: {parsed}")

        economia_nueva = parsed.economia 
        mensaje_validacion = parsed.mensaje_validacion

        # Actualizar el estado 'economia' fusionando lo nuevo
        if economia_nueva:
             update_data = economia_nueva.model_dump(exclude_unset=True) 
             economia_actualizada = econ_actual.model_copy(update=update_data)
             print(f"DEBUG (Economía) ► Estado economía actualizado: {economia_actualizada}")
        # else: # Si no devuelve nada, mantenemos econ_actual que ya tenía el valor antes del try

    except ValidationError as e_val:
        print(f"ERROR (Economía) ► Error de Validación Pydantic en llm_economia: {e_val}")
        mensaje_validacion = f"Hubo un problema al procesar tu información económica: faltan datos requeridos ({e_val}). ¿Podrías aclararlo?"
        # Mantenemos el estado económico anterior en caso de error de validación LLM
        economia_actualizada = econ_actual 
    except Exception as e:
        print(f"ERROR (Economía) ► Fallo al invocar llm_economia: {e}")
        mensaje_validacion = "Lo siento, tuve un problema técnico procesando tus datos económicos."
        # Mantenemos el estado económico anterior
        economia_actualizada = econ_actual

    # --- Guardar Pregunta Pendiente ---
    pregunta_para_siguiente_nodo = None
    if mensaje_validacion and mensaje_validacion.strip():
        pregunta_para_siguiente_nodo = mensaje_validacion.strip()
        print(f"DEBUG (Economía) ► Guardando pregunta pendiente: {pregunta_para_siguiente_nodo}")
    else:
        print(f"DEBUG (Economía) ► No hay pregunta de validación pendiente.")
        
    # Devolver estado actualizado SIN modificar messages, pero CON pregunta_pendiente
    return {
        **state,
        "economia": economia_actualizada, # Guardar economía actualizada
        # 'messages' NO se modifica aquí
        "pregunta_pendiente": pregunta_para_siguiente_nodo # Guardar la pregunta
    }

def validar_economia_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Comprueba si la información económica ('economia') en el estado está completa
    utilizando la función de utilidad `check_economia_completa`.
    """
    print("--- Ejecutando Nodo: validar_economia_node ---")
    economia = state.get("economia")
    
    # Llamar a la función de utilidad que usa el validador Pydantic
    if check_economia_completa(economia):
        print("DEBUG (Economía) ► Validación: Economía considerada COMPLETA.")
    else:
        print("DEBUG (Economía) ► Validación: Economía considerada INCOMPLETA.")
        
    # Este nodo solo valida, no modifica el estado.
    # La condición del grafo decidirá si volver a recopilar_economia_node o avanzar.
    return {**state}
# --- Fin Etapa 3 ---


# --- Etapa 4: Finalización y Presentación ---
def calcular_recomendacion_economia_modo1_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Calcula la recomendación económica (modo_adquisicion_recomendado, 
    precio_max_contado_recomendado, cuota_max_calculada) si el usuario
    eligió el Modo 1 y proporcionó los datos necesarios.
    Actualiza filtros_inferidos en el estado.
    """
    print("--- Ejecutando Nodo: calcular_recomendacion_economia_modo1_node ---")
    logging.debug("--- Ejecutando Nodo: calcular_recomendacion_economia_modo1_node ---")
    
    economia_obj = state.get("economia")
    filtros_obj = state.get("filtros_inferidos")

    # Si no hay filtros_obj (poco probable si el flujo es correcto), inicializar uno
    if filtros_obj is None:
        logging.warning("WARN (CalcEconModo1) ► filtros_inferidos era None. Inicializando uno nuevo.")
        filtros_obj = FiltrosInferidos()
        
    filtros_actualizados = filtros_obj.model_copy(deep=True)
    cambios_realizados = False

    if economia_obj and economia_obj.modo == 1:
        logging.debug("DEBUG (CalcEconModo1) ► Modo 1 detectado. Intentando calcular recomendación económica...")
        try:
            ingresos = economia_obj.ingresos
            ahorro = economia_obj.ahorro
            anos_posesion = economia_obj.anos_posesion
            
            if ingresos is not None and ahorro is not None and anos_posesion is not None:
                t = min(anos_posesion, 8) # años para cálculo de ahorro, max 8
                ahorro_utilizable = ahorro * 0.75 # Usar el 75% del ahorro
                
                # Estimación de capacidad de ahorro mensual dedicada al coche (ej: 10% de ingresos netos mensuales)
                # Si 'ingresos' son anuales, dividir por 12. Asumamos que 'ingresos' son anuales.
                capacidad_ahorro_mensual_coche = (ingresos / 12) * 0.10 
                
                # Potencial de ahorro total durante el plazo de posesión
                potencial_ahorro_total_plazo = capacidad_ahorro_mensual_coche * 12 * t
                
                # Decisión Contado vs. Financiado para Modo 1
                # Si el ahorro utilizable cubre una buena parte o todo el potencial de gasto vía cuotas
                # o si el potencial de gasto es bajo, podría sugerir contado.
                # Esta lógica puede necesitar refinamiento según tus criterios de "inteligencia financiera".
                # Ejemplo simple: si el ahorro cubre al menos la mitad del gasto potencial total
                modo_adq_rec = "Financiado" # Default
                precio_max_rec = None
                cuota_max_calc = capacidad_ahorro_mensual_coche # La cuota máxima sería su capacidad de ahorro mensual

                if ahorro_utilizable >= (potencial_ahorro_total_plazo * 0.5) and potencial_ahorro_total_plazo <= 30000 : # Umbral ejemplo para "bajo gasto"
                    modo_adq_rec = "Contado"
                    # Si es contado, el precio máximo podría ser el ahorro utilizable más lo que ahorraría en 1-2 años
                    precio_max_rec = ahorro_utilizable + (capacidad_ahorro_mensual_coche * 12 * 2) 
                    cuota_max_calc = None # No hay cuota si es contado
                
                logging.debug(f"DEBUG (CalcEconModo1) ► Modo Adq Rec: {modo_adq_rec}, Precio Max Rec: {precio_max_rec}, Cuota Max Calc: {cuota_max_calc}")

                update_dict = {
                    "modo_adquisicion_recomendado": modo_adq_rec,
                    "precio_max_contado_recomendado": precio_max_rec,
                    "cuota_max_calculada": cuota_max_calc
                }
                filtros_actualizados = filtros_actualizados.model_copy(update=update_dict) 
                cambios_realizados = True
                logging.debug(f"DEBUG (CalcEconModo1) ► Filtros actualizados con recomendación Modo 1: {filtros_actualizados.modo_adquisicion_recomendado}, PrecioMax: {filtros_actualizados.precio_max_contado_recomendado}, CuotaMax: {filtros_actualizados.cuota_max_calculada}")
            else:
                 logging.warning("WARN (CalcEconModo1) ► Faltan datos (ingresos, ahorro o años) para cálculo Modo 1.")
        except Exception as e_calc:
            logging.error(f"ERROR (CalcEconModo1) ► Fallo durante cálculo de recomendación Modo 1: {e_calc}")
            traceback.print_exc()
            # En caso de error, filtros_actualizados mantiene la copia inicial (sin estos campos o con los anteriores)
    else:
         logging.debug("DEBUG (CalcEconModo1) ► Modo no es 1 o no hay datos de economía, omitiendo cálculo de recomendación económica.")

    if cambios_realizados:
        return {"filtros_inferidos": filtros_actualizados}
    else:
        # Si no hubo cambios, devolvemos el estado sin modificar esta clave para evitar escrituras innecesarias
        # o devolvemos el filtros_actualizados que es una copia del original si no se tocó.
        # Para LangGraph, es mejor devolver el objeto aunque no haya cambiado, si la clave existe en el estado.
        return {"filtros_inferidos": filtros_actualizados} 

def calcular_flags_dinamicos_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Calcula todos los flags booleanos dinámicos basados en las preferencias del usuario
    y la información climática. Estos flags se usarán para la lógica de scoring en BQ.
    Actualiza el estado con estos flags.
    """
    print("--- Ejecutando Nodo: calcular_flags_dinamicos_node ---")
    logging.debug("--- Ejecutando Nodo: calcular_flags_dinamicos_node ---")
    preferencias_obj = state.get("preferencias_usuario")
    info_clima_obj = state.get("info_clima_usuario")
    penalizar_puertas_bajas_actual = state.get("penalizar_puertas_bajas", False) # # Los flags 'penalizar_puertas_bajas' y 'priorizar_ancho' vienen de aplicar_filtros_pasajeros_node ya deberían estar en el estado si esa lógica se ejecutó.
    info_pasajeros_obj = state.get("info_pasajeros") # <-- Obtener info de pasajeros
    print(f"DEBUG contenido de los objetos:  preferencias_obj: {preferencias_obj} - pasajeros {info_pasajeros_obj} - clima {info_clima_obj}") # Debug para ver qué contiene el objeto
    flag_pen_bev_reev_avent_ocas = False
    flag_pen_phev_avent_ocas = False
    flag_pen_electrif_avent_extr = False # Para BEV, REEV, PHEV en aventura extrema
    flag_penalizar_lc_comod = False
    flag_penalizar_dep_comod = False
    flag_penalizar_ant_tec = False
    flag_aplicar_dist_amb = False
    flag_es_zbe = False
    flag_fav_car_montana = False #  # --- NUEVOS FLAGS PARA LÓGICA DE CARROCERÍA ---
    flag_fav_car_comercial = False
    flag_fav_car_pasajeros_pro = False
    flag_desfav_car_no_aventura = False#  
    flag_fav_suv_aventura_ocasional = False
    flag_fav_pickup_todoterreno_aventura_extrema = False
    flag_aplicar_logica_objetos_especiales = False
    flag_fav_carroceria_confort = False# --- NUEVOS FLAGS PARA LÓGICA DE CARROCERÍA ---
    flag_logica_uso_ocasional = False # 
    flag_pen_bev_reev_avent_ocas = False
    flag_favorecer_bev_uso_definido = False 
    flag_penalizar_phev_uso_intensivo = False
    flag_favorecer_electrificados_por_punto_carga = False
    flag_logica_diesel_ciudad = False
    penalizar_awd_ninguna_aventura = False
    favorecer_awd_aventura_ocasional = False
    favorecer_awd_aventura_extrema = False
    flag_bonus_awd_nieve = False
    flag_bonus_awd_montana = False
    flag_logica_reductoras_aventura = False
    flag_bonus_awd_clima_adverso = False
    flag_bonus_seguridad_critico = False
    flag_bonus_seguridad_fuerte= False
    flag_bonus_fiab_dur_critico = False
    flag_bonus_fiab_dur_fuerte= False
    flag_bonus_costes_critico = False
    flag_penalizar_tamano_no_compacto = False
    flag_bonus_singularidad_lifestyle = False
    flag_deportividad_lifestyle = False
    flag_ajuste_maletero_personal = False

     
    # Verificar que preferencias_obj exista para acceder a sus atributos
    if not preferencias_obj:
        logging.error("ERROR (CalcFlags) ► 'preferencias_usuario' no existe en el estado. No se pueden calcular flags dinámicos.")
        # Devolver los flags con sus valores por defecto y mantener los existentes
        return {
            "penalizar_puertas_bajas": penalizar_puertas_bajas_actual,
            #"priorizar_ancho": priorizar_ancho_actual,
            "flag_penalizar_low_cost_comodidad": flag_penalizar_lc_comod,
            "flag_penalizar_deportividad_comodidad": flag_penalizar_dep_comod,
            "flag_penalizar_antiguo_por_tecnologia": flag_penalizar_ant_tec,
            "aplicar_logica_distintivo_ambiental": flag_aplicar_dist_amb,
            "penalizar_bev_reev_aventura_ocasional": flag_pen_bev_reev_avent_ocas,
            "penalizar_phev_aventura_ocasional": flag_pen_phev_avent_ocas,
            "penalizar_electrificados_aventura_extrema": flag_pen_electrif_avent_extr,
            "es_municipio_zbe": flag_es_zbe,
            "favorecer_carroceria_montana": flag_fav_car_montana,
            "favorecer_carroceria_comercial": flag_fav_car_comercial,
            "favorecer_carroceria_pasajeros_pro": flag_fav_car_pasajeros_pro,
            "desfavorecer_carroceria_no_aventura": flag_desfav_car_no_aventura,
            "favorecer_suv_aventura_ocasional": flag_fav_suv_aventura_ocasional,
            "favorecer_pickup_todoterreno_aventura_extrema": flag_fav_pickup_todoterreno_aventura_extrema,
            "aplicar_logica_objetos_especiales": flag_aplicar_logica_objetos_especiales,
            "favorecer_carroceria_confort": flag_fav_carroceria_confort,  
            "flag_logica_uso_ocasional": flag_logica_uso_ocasional,
            "flag_favorecer_bev_uso_definido": flag_favorecer_bev_uso_definido, 
            "flag_penalizar_phev_uso_intensivo": flag_penalizar_phev_uso_intensivo, #
            "flag_favorecer_electrificados_por_punto_carga" : flag_favorecer_electrificados_por_punto_carga,
            "flag_logica_diesel_ciudad" : flag_logica_diesel_ciudad,
            "penalizar_awd_ninguna_aventura" : penalizar_awd_ninguna_aventura,
            "favorecer_awd_aventura_ocasional" : favorecer_awd_aventura_ocasional,
            "favorecer_awd_aventura_extrema" : favorecer_awd_aventura_extrema,
            "flag_bonus_awd_nieve" : flag_bonus_awd_nieve,
            "flag_bonus_awd_montana" : flag_bonus_awd_montana,
            "flag_logica_reductoras_aventura" : flag_logica_reductoras_aventura,
            "flag_bonus_awd_clima_adverso" : flag_bonus_awd_clima_adverso,
            "flag_bonus_seguridad_critico": flag_bonus_seguridad_critico,
            "flag_bonus_seguridad_fuerte": flag_bonus_seguridad_fuerte,
            'flag_bonus_fiab_dur_critico': flag_bonus_fiab_dur_critico,
            'flag_bonus_fiab_dur_fuerte': flag_bonus_fiab_dur_fuerte,
            "flag_bonus_costes_critico": flag_bonus_costes_critico,
            "flag_penalizar_tamano_no_compacto" : flag_penalizar_tamano_no_compacto,
            "flag_bonus_singularidad_lifestyle": flag_bonus_singularidad_lifestyle,
            "flag_deportividad_lifestyle": flag_deportividad_lifestyle,
            "flag_ajuste_maletero_personal" : flag_ajuste_maletero_personal
        }
    # --- NUEVA LÓGICA PARA FLAGS DE CARROCERÍA ---
    # Regla 1: Zona de Montaña favorece SUV/TODOTERRENO
    if info_clima_obj and hasattr(info_clima_obj, 'ZONA_CLIMA_MONTA') and info_clima_obj.ZONA_CLIMA_MONTA is True:
        flag_fav_car_montana = True
        logging.info(f"DEBUG (CalcFlags) ► ZONA_CLIMA_MONTA=True. Activando flag para favorecer carrocería de montaña.")
    # --- FLAGS DE TRACCIÓN Y CLIMA ---
    if info_clima_obj: # Solo si existe el objeto de info climática
        if getattr(info_clima_obj, 'ZONA_NIEVE', False):
            flag_bonus_awd_nieve = True
            logging.info("DEBUG (CalcFlags) ► Zona de nieve detectada. Activando bonus para ALL.")
        if getattr(info_clima_obj, 'ZONA_CLIMA_MONTA', False):
            flag_bonus_awd_montana = True
            logging.info("DEBUG (CalcFlags) ► Zona de montaña detectada. Activando bonus para ALL.")    
    
    # Regla 2 y 3: Uso profesional con/sin pasajeros
    if is_yes(preferencias_obj.uso_profesional):
        if info_pasajeros_obj and info_pasajeros_obj.suele_llevar_acompanantes is False:
            flag_fav_car_comercial = True
            logging.info(f"DEBUG (CalcFlags) ► Uso profesional sin pasajeros. Activando flag para favorecer carrocería COMERCIAL.")
        elif info_pasajeros_obj and info_pasajeros_obj.suele_llevar_acompanantes is True:
            flag_fav_car_pasajeros_pro = True
            logging.info(f"DEBUG (CalcFlags) ► Uso profesional con pasajeros. Activando flag para favorecer 3VOL/MONOVOLUMEN.")

    # Regla 4: Aventura nula y no en montaña desfavorece PICKUP/TODOTERRENO
    if (hasattr(preferencias_obj, 'aventura') and preferencias_obj.aventura == NivelAventura.ninguna and
        (not info_clima_obj or not getattr(info_clima_obj, 'ZONA_CLIMA_MONTA', False))):
        flag_desfav_car_no_aventura = True
        logging.info(f"DEBUG (CalcFlags) ► Aventura 'Ninguna' y no es clima de montaña. Activando flag para desfavorecer PICKUP/TODOTERRENO.")
    
    
    # Regla 5 y 6: Aventura
    aventura_val = preferencias_obj.aventura
    if aventura_val:
        if aventura_val == NivelAventura.ocasional:
            flag_fav_suv_aventura_ocasional = True
            logging.info(f"DEBUG (CalcFlags) ► Aventura OCASIONAL. Activando flag para favorecer carrocería SUV.")
        elif aventura_val == NivelAventura.extrema:
            flag_fav_pickup_todoterreno_aventura_extrema = True
            logging.info(f"DEBUG (CalcFlags) ► Aventura EXTREMA. Activando flag para favorecer PICKUP/TODOTERRENO.")
            
      # ---  AVENTURA ---
    if hasattr(preferencias_obj, 'aventura'):
        aventura_val = preferencias_obj.aventura
        print(f"DEBUG (CalcFlags) ► Valor de preferencias_obj.aventura: {aventura_val} (Tipo: {type(aventura_val)})")
        logger.debug(f"DEBUG (CalcFlags) ► Valor de preferencias_obj.aventura: {aventura_val} (Tipo: {type(aventura_val)})")
        logger.debug(f"DEBUG (CalcFlags) ► Comparando con NivelAventura.OCASIONAL (Valor: {NivelAventura.ocasional}, Tipo: {type(NivelAventura.ocasional)})")
        logger.debug(f"DEBUG (CalcFlags) ► Comparando con NivelAventura.EXTREMA (Valor: {NivelAventura.extrema}, Tipo: {type(NivelAventura.extrema)})")

        if aventura_val is not None:
            if aventura_val == NivelAventura.ocasional:
                flag_pen_bev_reev_avent_ocas = True
                flag_pen_phev_avent_ocas = True
                logger.debug(f"INFO (CalcFlags) ► Aventura OCASIONAL. Activando penalizaciones para BEV/REEV y PHEV.") # Cambiado a INFO
            elif aventura_val == NivelAventura.extrema:
                flag_pen_electrif_avent_extr = True 
                logger.debug(f"INFO (CalcFlags) ► Aventura EXTREMA. Activando penalización para todos los electrificados.") # Cambiado a INFO
            else:
                logger.debug(f"DEBUG (CalcFlags) ► Nivel de aventura es '{aventura_val}', no OCASIONAL ni EXTREMA. No se activan penalizaciones específicas de aventura/mecánica.")
        else:
            logger.debug("DEBUG (CalcFlags) ► Nivel de aventura es None. No se activan penalizaciones de mecánica por aventura.")
    else:
        logging.warning("WARN (CalcFlags) ► El objeto 'preferencias_usuario' no tiene el atributo 'aventura'.")

     # --- LÓGICA REVISADA PARA FLAGS DE TRACCIÓN, AVENTURA Y CLIMA ---
    aventura_val = preferencias_obj.aventura
    vive_en_clima_adverso = False
    if info_clima_obj:
        vive_en_clima_adverso = getattr(info_clima_obj, 'ZONA_NIEVE', False) or getattr(info_clima_obj, 'ZONA_CLIMA_MONTA', False)

    if aventura_val == NivelAventura.ninguna.value:
        if vive_en_clima_adverso:
            # EXCEPCIÓN: El clima anula la preferencia. Se activa el bonus por clima.
            flag_bonus_awd_clima_adverso = True
            logging.info("DEBUG (CalcFlags) ► Nivel Aventura 'ninguna' pero clima adverso(montaña - Nieve). Activando BONUS favorecer traccion ALL.")
        else:
            # Caso normal: Sin aventura y sin clima adverso. Se activa la penalización.
            penalizar_awd_ninguna_aventura = True
            logging.info("DEBUG (CalcFlags) ► Nivel Aventura 'ninguna'. Activando PENALIZACIÓN para ALL.")
    elif aventura_val == NivelAventura.ocasional.value:
        favorecer_awd_aventura_ocasional = True
        logging.info("DEBUG (CalcFlags) ► Nivel Aventura 'ocasional'. Activando bonus para ALL.")
    elif aventura_val == NivelAventura.extrema.value:
        favorecer_awd_aventura_extrema = True
        logging.info("DEBUG (CalcFlags) ► Nivel Aventura 'extrema'. Activando bonus para ALL.")
    
    
    # ---  LÓGICA PARA FLAG DE REDUCTORAS Y AVENTURA ---
    if aventura_val == NivelAventura.ocasional.value:
        # Si la aventura es ocasional, establecemos el flag para el bonus moderado.
        flag_logica_reductoras_aventura = "FAVORECER_OCASIONAL"
        logging.info("DEBUG (CalcFlags) ► Nivel Aventura 'ocasional'. Activando flag para bonus moderado en Reductoras.")

    elif aventura_val == NivelAventura.extrema.value:
        # Si la aventura es extrema, establecemos el flag para el bonus alto.
        flag_logica_reductoras_aventura = "FAVORECER_EXTREMA"
        logging.info("DEBUG (CalcFlags) ► Nivel Aventura 'extrema'. Activando flag para bonus alto en Reductoras.")
                
    # Regla 7: Objetos Especiales
    if is_yes(preferencias_obj.necesita_espacio_objetos_especiales) :
        flag_aplicar_logica_objetos_especiales = True
        logging.info(f"DEBUG (CalcFlags) ► necesita_espacio_objetos_especiales=True. Activando lógica de carrocería para objetos especiales.")
    
    # RATINGS--------------------:
    # Regla 8: Alta Comodidad
    rating_comodidad_val = preferencias_obj.rating_comodidad
    if rating_comodidad_val is not None and rating_comodidad_val > UMBRAL_COMODIDAD_PARA_FAVORECER_CARROCERIA:
        flag_fav_carroceria_confort = True
        logging.info(f"DEBUG (CalcFlags) ► Rating Comodidad ({rating_comodidad_val}) > {UMBRAL_COMODIDAD_PARA_FAVORECER_CARROCERIA}. Activando flag para favorecer carrocerías confortables.")
        
    
    # Lógica para Flags de Penalización por Comodidad
    if preferencias_obj.rating_comodidad is not None:
        if preferencias_obj.rating_comodidad > UMBRAL_COMODIDAD_PARA_PENALIZAR_FLAGS:
            flag_penalizar_lc_comod = True
            flag_penalizar_dep_comod = True
            logging.debug(f"DEBUG (CalcFlags) ► Rating Comodidad ({preferencias_obj.rating_comodidad}). Activando flags penalización comodidad flag penalizar depor comod y flag penalizar lowcost comod")

    # Lógica para Flag de Penalización por Antigüedad y Tecnología
    if preferencias_obj.rating_tecnologia_conectividad is not None:
        if preferencias_obj.rating_tecnologia_conectividad > UMBRAL_TECNOLOGIA_PARA_PENALIZAR_ANTIGUEDAD_FLAG:
            flag_penalizar_ant_tec = True
            logging.debug(f"DEBUG (CalcFlags) ► Rating Tecnología ({preferencias_obj.rating_tecnologia_conectividad}). Activando flag penalización antigüedad.")

    # Lógica para Flag de Distintivo Ambiental (basado en rating_impacto_ambiental)
    if preferencias_obj.rating_impacto_ambiental is not None:
        if preferencias_obj.rating_impacto_ambiental > UMBRAL_IMPACTO_AMBIENTAL_PARA_LOGICA_DISTINTIVO_FLAG:
            flag_aplicar_dist_amb = True
            logging.debug(f"DEBUG (CalcFlags) ► Rating Impacto Ambiental ({preferencias_obj.rating_impacto_ambiental}). Activando lógica de distintivo ambiental.")
    
    if preferencias_obj.rating_seguridad is not None:
        if preferencias_obj.rating_seguridad >=9:   
            flag_bonus_seguridad_critico = True
            logging.info("Flags: Rating de seguridad CRÍTICO. Activando bonus x1.5.")
        elif preferencias_obj.rating_seguridad >= 7:
            flag_bonus_seguridad_fuerte = True
            logging.info("Flags: Rating de seguridad FUERTE. Activando bonus x1.2.")
    
    # ✅ NUEVA LÓGICA PARA FIABILIDAD/DURABILIDAD
    if preferencias_obj.rating_fiabilidad_durabilidad is not None:
        if preferencias_obj.rating_fiabilidad_durabilidad >= 9:
            flag_bonus_fiab_dur_critico = True
            logging.info("Flags: Rating de Fiabilidad/Durabilidad CRÍTICO. Activando bonus.")
        elif preferencias_obj.rating_fiabilidad_durabilidad >= 7:
            flag_bonus_fiab_dur_fuerte = True
            logging.info("Flags: Rating de Fiabilidad/Durabilidad FUERTE. Activando bonus.")
            
       # ✅ NUEVA LÓGICA PARA COSTES DE USO
    if preferencias_obj.rating_costes_uso is not None:
        if preferencias_obj.rating_costes_uso >= 7:
            flag_bonus_costes_critico = True
            logging.info("Flags: Rating de Costes de Uso CRÍTICO. Activando bonus.")
    #-------------------------
    # Primero, comprobamos si el usuario NO suele llevar acompañantes.
    # Usamos getattr para evitar errores si el atributo no existiera.
    if getattr(info_pasajeros_obj, 'suele_llevar_acompanantes', True) is False:
        flag_penalizar_tamano_no_compacto = True
        logging.info("Flags: Usuario no suele llevar acompañantes. Activando penalización para coches grandes.")
    
    # Si sí lleva acompañantes, comprobamos la frecuencia.
    elif getattr(info_pasajeros_obj, 'frecuencia_viaje_con_acompanantes', 'frecuente') == "ocasional":
        flag_penalizar_tamano_no_compacto = True
        logging.info("Flags: Frecuencia de pasajeros es 'ocasional'. Activando penalización para coches grandes.")

    # --- FIN DE LA LÓGICA CORREGIDA ---
    
    # Lógica para Flag ZBE (basado en info_clima_obj)
    if info_clima_obj and hasattr(info_clima_obj, 'cp_valido_encontrado') and info_clima_obj.cp_valido_encontrado and \
       hasattr(info_clima_obj, 'MUNICIPIO_ZBE') and info_clima_obj.MUNICIPIO_ZBE is True:
        flag_es_zbe = True
        logging.debug(f"DEBUG (CalcFlags) ► CP en MUNICIPIO_ZBE. Activando flag es_municipio_zbe.")
    
    # --- LÓGICA PARA EL NUEVO FLAG DE USO OCASIONAL ---
    if preferencias_obj.frecuencia_uso == FrecuenciaUso.OCASIONALMENTE.value:
        flag_logica_uso_ocasional = True
        logging.info("DEBUG (CalcFlags) ► Uso OCASIONAL detectado. Activando lógica de bonus para 'OCASION' y penalización para electrificados.")
   
    # --- LÓGICA PARA FAVORECER BEV/REEV EN PERFIL DE USO IDEAL ---
    # Parte 1: El uso principal es intensivo
    es_uso_diario_frecuente = preferencias_obj.frecuencia_uso in [FrecuenciaUso.DIARIO.value, FrecuenciaUso.FRECUENTEMENTE.value]
    es_trayecto_medio_largo = preferencias_obj.distancia_trayecto in [DistanciaTrayecto.ENTRE_10_Y_50_KM.value, DistanciaTrayecto.ENTRE_51_Y_150_KM.value]
    
    # Parte 2: El problema de los viajes muy largos está mitigado
    sin_viajes_largos = not is_yes(preferencias_obj.realiza_viajes_largos) # Cubre 'no' y None
    viajes_largos_esporadicos = preferencias_obj.frecuencia_viajes_largos == FrecuenciaViajesLargos.ESPORADICAMENTE.value
    
    # Condición final combinada
    if (es_uso_diario_frecuente and es_trayecto_medio_largo) and (sin_viajes_largos or viajes_largos_esporadicos):
        flag_favorecer_bev_uso_definido = True
        print("DEBUG (CalcFlags) ► Perfil de uso ideal para BEV/REEV detectado. Activando bonus.")
        logging.info("DEBUG (CalcFlags) ► Perfil de uso BEV/REEV detectado: FrecuenciaUso.DIARIO o FRECUENTEMENTE y DistanciaTrayecto.ENTRE_10_Y_50_KM.value o ENTRE_51_Y_150_KM. Activando bonus.")
 
    # --- LÓGICA PARA PENALIZAR PHEV EN TRAYECTOS LARGOS Y FRECUENTES ---
    es_uso_diario_frecuente = preferencias_obj.frecuencia_uso in [FrecuenciaUso.DIARIO.value, FrecuenciaUso.FRECUENTEMENTE.value]
    es_trayecto_muy_largo = preferencias_obj.distancia_trayecto == DistanciaTrayecto.MAS_150_KM.value
    #Falta revisar condiciones en el documento
    if es_uso_diario_frecuente and es_trayecto_muy_largo:
        flag_penalizar_phev_uso_intensivo = True
        logging.info("DEBUG (CalcFlags) ► Patrón de uso intensivo y larga distancia detectado. Activando penalización para PHEVs.")

     # --- LÓGICA PARA PUNTO DE CARGA PROPIO ---
    if is_yes(preferencias_obj.tiene_punto_carga_propio):
        flag_favorecer_electrificados_por_punto_carga = True
        logging.info("DEBUG (CalcFlags) ► Usuario tiene punto de carga propio. Activando bonus para BEV/PHEV/REEV.")
   
   # --- LÓGICA PARA FLAG DIÉSEL - RECORRE CAMINOS CIUDAD - circula principalmente ciudad ---
    if is_yes(preferencias_obj.circula_principalmente_ciudad):
        if preferencias_obj.frecuencia_uso == FrecuenciaUso.OCASIONALMENTE.value and FrecuenciaViajesLargos.OCASIONALMENTE:
            # Caso excepcional: uso ocasional en ciudad, no se penaliza, se bonifica
            flag_logica_diesel_ciudad = "BONIFICAR"
            logging.info("DEBUG (CalcFlags) ► Conductor urbano ocasional/ FrecuenciaUso.OCASIONALMENTE y FrecuenciaViajesLargos.OCASIONALMENTE. Activando pequeño bonus para diésel.")
        else:
            # Caso general: conductor urbano, se penaliza diésel
            flag_logica_diesel_ciudad = "PENALIZAR"
            logging.info("DEBUG (CalcFlags) ► Conductor urbano frecuente. Activando penalización para diésel.")
    
    logging.debug(f"DEBUG (CalcFlags) ► Flags calculados: lowcost_comodidad={flag_penalizar_lc_comod}, deportividad_comodidad={flag_penalizar_dep_comod}, antiguo_por_tecnolog={flag_penalizar_ant_tec}, distint_ambiental={flag_aplicar_dist_amb}, zbe={flag_es_zbe}, penali_bev_reev_aventura_ocasional= {flag_pen_bev_reev_avent_ocas}...")

    # --- ✅ NUEVA LÓGICA PARA FLAG DE SINGULARIDAD/LIFESTYLE ---
    if info_pasajeros_obj and preferencias_obj:
        # Condición 1: El usuario valora un diseño exclusivo
        quiere_diseno_exclusivo = is_yes(preferencias_obj.prefiere_diseno_exclusivo)
        
        # Condición 2: El usuario no suele llevar muchos pasajeros
        frecuencia_pasajeros = info_pasajeros_obj.frecuencia_viaje_con_acompanantes
        uso_poco_acompaniado = frecuencia_pasajeros in ["nunca", "ocasional"]

        # Si ambas condiciones se cumplen, activamos el flag
        if quiere_diseno_exclusivo and uso_poco_acompaniado:
            flag_bonus_singularidad_lifestyle = True
            logging.info(f"Flags: Perfil 'Lifestyle' detectado. Activando bonus para Coupés y Descapotables.")
            
    # Condición 1: El estilo de conducción debe ser DEPORTIVO
    es_estilo_deportivo = getattr(preferencias_obj, 'estilo_conduccion', None) == EstiloConduccion.DEPORTIVO.value
    # Condición 2: El usuario no suele llevar muchos pasajeros
    # Usamos 'frecuencia' como el campo consolidado que ya tienes.
    frecuencia_pasajeros = info_pasajeros_obj.frecuencia_viaje_con_acompanantes
    uso_poco_acompaniado = frecuencia_pasajeros in ["nunca", "ocasional"]

    # Si ambas condiciones se cumplen, activamos el flag
    if es_estilo_deportivo and uso_poco_acompaniado:
        flag_deportividad_lifestyle = True
        logging.info(f"Flags: Perfil 'Deportividad Lifestyle' detectado. Activando ajustes de carrocería para Coupés, etc.")
    # --- FIN NUEVA LÓGICA ---
    
    if preferencias_obj:
        # Condición 1: El uso NO es profesional
        uso_no_profesional = not is_yes(preferencias_obj.uso_profesional)
        
        # Condición 2: El usuario SÍ transporta carga voluminosa
        transporta_carga = is_yes(preferencias_obj.transporta_carga_voluminosa)

        # Si ambas condiciones se cumplen, activamos el flag
        if uso_no_profesional and transporta_carga:
            flag_ajuste_maletero_personal = True
            logging.info(f"Flags: Perfil 'Transportista Personal' detectado. Activando ajustes de maletero y carrocería.")
    
    return {
        "penalizar_puertas_bajas": penalizar_puertas_bajas_actual, # Propagar
       # "priorizar_ancho": priorizar_ancho_actual, # Propagar
        "flag_penalizar_low_cost_comodidad": flag_penalizar_lc_comod,
        "flag_penalizar_deportividad_comodidad": flag_penalizar_dep_comod, 
        "flag_penalizar_antiguo_por_tecnologia": flag_penalizar_ant_tec,
        "aplicar_logica_distintivo_ambiental": flag_aplicar_dist_amb,
        "penalizar_bev_reev_aventura_ocasional": flag_pen_bev_reev_avent_ocas,
        "penalizar_phev_aventura_ocasional": flag_pen_phev_avent_ocas,
        "penalizar_electrificados_aventura_extrema": flag_pen_electrif_avent_extr,
        "favorecer_carroceria_montana": flag_fav_car_montana,
        "favorecer_carroceria_comercial": flag_fav_car_comercial,
        "favorecer_carroceria_pasajeros_pro": flag_fav_car_pasajeros_pro,
        "desfavorecer_carroceria_no_aventura": flag_desfav_car_no_aventura,
        "favorecer_suv_aventura_ocasional": flag_fav_suv_aventura_ocasional,
        "favorecer_pickup_todoterreno_aventura_extrema": flag_fav_pickup_todoterreno_aventura_extrema,
        "penalizar_awd_ninguna_aventura": penalizar_awd_ninguna_aventura,
        "favorecer_awd_aventura_ocasional": favorecer_awd_aventura_ocasional,
        "favorecer_awd_aventura_extrema": favorecer_awd_aventura_extrema,
        "aplicar_logica_objetos_especiales": flag_aplicar_logica_objetos_especiales,
        "favorecer_carroceria_confort": flag_fav_carroceria_confort,
        "flag_favorecer_bev_uso_definido": flag_favorecer_bev_uso_definido,
        "flag_logica_uso_ocasional": flag_logica_uso_ocasional,
        "flag_penalizar_phev_uso_intensivo": flag_penalizar_phev_uso_intensivo,
        "flag_favorecer_electrificados_por_punto_carga": flag_favorecer_electrificados_por_punto_carga,
        "flag_logica_diesel_ciudad": flag_logica_diesel_ciudad,
        "flag_bonus_awd_nieve": flag_bonus_awd_nieve,
        "flag_bonus_awd_montana": flag_bonus_awd_montana,
        "flag_logica_reductoras_aventura": flag_logica_reductoras_aventura,
        "flag_bonus_awd_clima_adverso" : flag_bonus_awd_clima_adverso,
        "flag_bonus_seguridad_critico": flag_bonus_seguridad_critico,
        "flag_bonus_seguridad_fuerte": flag_bonus_seguridad_fuerte,
        "flag_bonus_fiab_dur_critico": flag_bonus_fiab_dur_critico,
        "flag_bonus_fiab_dur_fuerte": flag_bonus_fiab_dur_fuerte,
        "flag_bonus_costes_critico": flag_bonus_costes_critico,
        "flag_penalizar_tamano_no_compacto": flag_penalizar_tamano_no_compacto,
        "flag_bonus_singularidad_lifestyle": flag_bonus_singularidad_lifestyle,
        "flag_deportividad_lifestyle": flag_deportividad_lifestyle,
        "flag_ajuste_maletero_personal" : flag_ajuste_maletero_personal,
        "es_municipio_zbe": flag_es_zbe       
    }
    

   
def calcular_pesos_finales_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Calcula los pesos crudos y normalizados finales basados en todas las
    preferencias del usuario, filtros inferidos (para *_min_val) y flags climáticos/dinámicos.
    Actualiza state['pesos'].
    """
    print("--- Ejecutando Nodo: calcular_pesos_finales_node ---")
    logging.debug("--- Ejecutando Nodo: calcular_pesos_finales_node ---")

    preferencias_obj = state.get("preferencias_usuario")
    filtros_obj = state.get("filtros_inferidos") # Contiene estetica_min, premium_min, singular_min
    info_clima_obj = state.get("info_clima_usuario")
    info_pasajeros_obj = state.get("info_pasajeros")
    print(f"DEBUG_MIO (info_pasajeros_o     bj): {info_pasajeros_obj}")
    km_anuales_val = state.get("km_anuales_estimados")
    print(f"DEBUG_MIO_2: (km_anuales_val): {km_anuales_val}")
    # Por ahora, los extraemos aquí de info_clima_obj para pasarlos a compute_raw_weights.

    es_nieblas_val = False
    es_nieve_val = False
    es_monta_val = False
    if info_clima_obj and hasattr(info_clima_obj, 'cp_valido_encontrado') and info_clima_obj.cp_valido_encontrado:
        es_nieblas_val = getattr(info_clima_obj, 'ZONA_NIEBLAS', False) or False # Default a False si el atributo no existe
        es_nieve_val = getattr(info_clima_obj, 'ZONA_NIEVE', False) or False
        es_monta_val = getattr(info_clima_obj, 'ZONA_CLIMA_MONTA', False) or False

    pesos_calculados_normalizados = {} # Default a dict vacío en caso de error

    if not preferencias_obj or not filtros_obj:
        logging.error("ERROR (CalcPesos) ► Faltan preferencias_usuario o filtros_inferidos. No se pueden calcular pesos.")
        return {"pesos": pesos_calculados_normalizados} # Devolver pesos vacíos

    try:
        prefs_dict_para_weights = preferencias_obj.model_dump(mode='json', exclude_none=False)
        info_pasajeros_dict_para_weights = info_pasajeros_obj.model_dump(mode='json', exclude_none=False) if info_pasajeros_obj else None

        logging.debug(f"DEBUG (CalcPesos) ► Entradas para compute_raw_weights:\n"
                      f"  Preferencias: {prefs_dict_para_weights.get('apasionado_motor')}, {prefs_dict_para_weights.get('aventura')}, etc.\n"
                      f"  InfoPasajeros: {info_pasajeros_dict_para_weights}\n"
                      f"  ZonaNieblas: {es_nieblas_val}, ZonaNieve: {es_nieve_val}, ZonaMonta: {es_monta_val}")

        raw_weights = compute_raw_weights(
            preferencias=prefs_dict_para_weights, # Usar el dict que ya tenías
            info_pasajeros_dict=info_pasajeros_dict_para_weights,
            es_zona_nieblas=es_nieblas_val,
            # es_zona_nieve=es_nieve_val,
            # es_zona_clima_monta=es_monta_val,
            km_anuales_estimados=km_anuales_val
        )
        pesos_calculados_normalizados = normalize_weights(raw_weights)
        logging.debug(f"DEBUG (CalcPesos) ► Pesos finales calculados y normalizados: {pesos_calculados_normalizados}") 
    
    except Exception as e_weights:
        logging.error(f"ERROR (CalcPesos) ► Fallo calculando pesos: {e_weights}")
        traceback.print_exc()
        # pesos_calculados_normalizados se queda como {}

    return {"pesos": pesos_calculados_normalizados}

def formatear_tabla_resumen_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Formatea la tabla resumen final de criterios y la guarda en
    state['tabla_resumen_criterios']. Ya NO añade AIMessage al historial.
    """
    print("--- Ejecutando Nodo: formatear_tabla_resumen_node ---")
    logging.debug("--- Ejecutando Nodo: formatear_tabla_resumen_node ---")

    preferencias_obj = state.get("preferencias_usuario")
    filtros_actualizados_obj = state.get("filtros_inferidos") 
    economia_obj = state.get("economia")
    codigo_postal_val = state.get("codigo_postal_usuario")
    info_clima_obj = state.get("info_clima_usuario")
    info_pasajeros_obj = state.get("info_pasajeros")

    tabla_final_md = "Error al generar el resumen de criterios." # Default

    if not preferencias_obj or not filtros_actualizados_obj or not economia_obj:
        logging.error("ERROR (FormatearTabla) ► Faltan datos esenciales para formatear la tabla.")
        tabla_final_md = "Lo siento, falta información para generar el resumen completo de tus preferencias."
    else:
        try:
            prefs_dict_para_tabla = preferencias_obj.model_dump(mode='json', exclude_none=False) if preferencias_obj else {}
            filtros_dict_para_tabla = filtros_actualizados_obj.model_dump(mode='json', exclude_none=False) if filtros_actualizados_obj else {}
            econ_dict_para_tabla = economia_obj.model_dump(mode='json', exclude_none=False) if economia_obj else {}
            info_clima_dict_para_tabla = info_clima_obj.model_dump(mode='json', exclude_none=False) if info_clima_obj else {}
            info_pasajeros_dict_para_tabla = info_pasajeros_obj.model_dump(mode='json', exclude_none=False) if info_pasajeros_obj else {}
            
            tabla_final_md = formatear_preferencias_en_tabla(
                preferencias=prefs_dict_para_tabla, 
                filtros=filtros_dict_para_tabla, 
                economia=econ_dict_para_tabla,
                codigo_postal_usuario=codigo_postal_val,
                info_clima_usuario=info_clima_dict_para_tabla,
                info_pasajeros=info_pasajeros_dict_para_tabla 
            )
            logging.debug("\n--- TABLA RESUMEN GENERADA INTERNAMENTE (DEBUG) ---\n" + tabla_final_md + "\n--------------------------------------\n")
        except Exception as e_format:
            logging.error(f"ERROR (FormatearTabla) ► Fallo formateando la tabla: {e_format}")
            traceback.print_exc() 
            tabla_final_md = "Hubo un inconveniente al generar el resumen de tus preferencias."

    # Devolver solo las claves del estado que este nodo modifica
    return {
        "tabla_resumen_criterios": tabla_final_md,
        "pregunta_pendiente": None # Asegurar que se limpie
    }

  # --- Fin Etapa 4 ---
from config.settings import (MAPA_FRECUENCIA_USO, MAPA_DISTANCIA_TRAYECTO, MAPA_FRECUENCIA_VIAJES_LARGOS, MAPA_REALIZA_VIAJES_LARGOS_KM )

# --- ✅ NUEVA FUNCIÓN PARA SER USADA COMO NODO INDEPENDIENTE ---
def calcular_km_anuales_postprocessing_node(state: EstadoAnalisisPerfil) -> Dict[str, Optional[int]]:
    """
    Calcula los km_anuales_estimados basándose en las preferencias del usuario.
    Actúa como un nodo del grafo que lee el estado y devuelve el nuevo campo calculado.
    """
    print("--- Ejecutando Nodo: calcular_km_anuales_postprocessing_node ---")
    preferencias = state.get("preferencias_usuario")
    
    if not preferencias:
        logging.warning("WARN (CalcKM) ► No hay 'preferencias_usuario' en el estado. No se pueden calcular los km.")
        return {"km_anuales_estimados": None}

    # --- Parte 1: Kilometraje por uso habitual (Fórmula: 52 * a * b) ---
    frecuencia_uso_val = getattr(preferencias, 'frecuencia_uso', None)
    a = MAPA_FRECUENCIA_USO.get(frecuencia_uso_val, 0)
    print(f"a: {a}")
    
    distancia_trayecto_val = getattr(preferencias, 'distancia_trayecto', None)
    b = MAPA_DISTANCIA_TRAYECTO.get(distancia_trayecto_val, 0)
    print(f"b: {b} -> 52 * {a} * {b}")
    
    km_habituales = 52 * a * b

    # --- Parte 2: Kilometraje por viajes largos (Fórmula: n * c) ---
    realiza_viajes_largos_val = getattr(preferencias, 'realiza_viajes_largos', 'no')
    n_key = "sí" if is_yes(realiza_viajes_largos_val) else "no"
    n = MAPA_REALIZA_VIAJES_LARGOS_KM.get(n_key, 0)

    frecuencia_viajes_largos_val = getattr(preferencias, 'frecuencia_viajes_largos', None)
    c = MAPA_FRECUENCIA_VIAJES_LARGOS.get(frecuencia_viajes_largos_val, 0)

    km_viajes_largos = n * c
    
    # --- Parte 3: Cálculo Final ---
    km_totales = int(km_habituales + km_viajes_largos)

    logging.info(f"DEBUG (CalcKM) ► Cálculo: (52 * {a} * {b}) + ({n} * {c}) = {km_totales} km/año")
    
    return {"km_anuales_estimados": km_totales}




def buscar_coches_finales_node(state: EstadoAnalisisPerfil, config: RunnableConfig) -> dict:
    """
    Usa los filtros y pesos finales, busca en BQ, y presenta un mensaje combinado
    con el resumen de criterios y los resultados de los coches.
    """
    print("--- Ejecutando Nodo: buscar_coches_finales_node ---")
    logging.debug(f"DEBUG (Buscar BQ Init) ► Estado completo recibido: {state}") 
    k_coches = 5
    historial = state.get("messages", [])
    tabla_resumen_criterios_md = state.get("tabla_resumen_criterios", "No se pudo generar el resumen de criterios.")
    preferencias_obj = state.get("preferencias_usuario") # Objeto PerfilUsuario
    filtros_finales_obj = state.get("filtros_inferidos") 
    pesos_finales = state.get("pesos")
    economia_obj = state.get("economia")
    penalizar_puertas_flag = state.get("penalizar_puertas_bajas", False)
    flag_penalizar_lc_comod = state.get("flag_penalizar_low_cost_comodidad", False)
    flag_penalizar_dep_comod = state.get("flag_penalizar_deportividad_comodidad", False)
    flag_penalizar_antiguo_tec_val = state.get("flag_penalizar_antiguo_por_tecnologia", False)
    flag_aplicar_distintivo_val = state.get("aplicar_logica_distintivo_ambiental", False)
    flag_es_zbe_val = state.get("es_municipio_zbe", False)
    # Flags de aventura y penalización de mecánica
    flag_pen_bev_reev_avent_ocas = state.get("penalizar_bev_reev_aventura_ocasional", False)
    flag_pen_phev_avent_ocas= state.get("penalizar_phev_aventura_ocasional", False)
    flag_pen_electrif_avent_extr = state.get("penalizar_electrificados_aventura_extrema", False)
    flag_fav_car_montana_val = state.get("favorecer_carroceria_montana", False)
    flag_fav_car_comercial_val = state.get("favorecer_carroceria_comercial", False)
    flag_fav_car_pasajeros_pro_val = state.get("favorecer_carroceria_pasajeros_pro", False)
    flag_desfav_car_no_aventura_val = state.get("desfavorecer_carroceria_no_aventura", False)
    flag_fav_suv_aventura_ocasional = state.get("favorecer_suv_aventura_ocasional")
    flag_fav_pickup_todoterreno_aventura_extrema = state.get("favorecer_pickup_todoterreno_aventura_extrema")
    flag_aplicar_logica_objetos_especiales= state.get("aplicar_logica_objetos_especiales")
    flag_fav_carroceria_confort= state.get("favorecer_carroceria_confort")
    flag_logica_uso_ocasional = state.get("flag_logica_uso_ocasional")
    flag_favorecer_bev_uso_definido = state.get("flag_favorecer_bev_uso_definido")
    flag_penalizar_phev_uso_intensivo = state.get("flag_penalizar_phev_uso_intensivo")
    flag_favorecer_electrificados_por_punto_carga = state.get("flag_favorecer_electrificados_por_punto_carga")
    flag_logica_diesel_ciudad= state.get("flag_logica_diesel_ciudad")
    penalizar_awd_ninguna_val = state.get("penalizar_awd_ninguna_aventura", False)
    favorecer_awd_ocasional_val = state.get("favorecer_awd_aventura_ocasional", False)
    favorecer_awd_extrema_val = state.get("favorecer_awd_aventura_extrema", False)
    flag_bonus_nieve_val = state.get("flag_bonus_awd_nieve", False)
    flag_bonus_montana_val = state.get("flag_bonus_awd_montana", False)
    flag_reductoras_aventura_val = state.get("flag_logica_reductoras_aventura")
    flag_bonus_awd_clima_adverso = state.get("flag_bonus_awd_clima_adverso")
    flag_bonus_seguridad_critico = state.get("flag_bonus_seguridad_critico")
    flag_bonus_seguridad_fuerte = state.get("flag_bonus_seguridad_fuerte")
    flag_bonus_fiab_dur_critico = state.get("flag_bonus_fiab_dur_critico")
    flag_bonus_fiab_dur_fuerte = state.get("flag_bonus_fiab_dur_fuerte")
    flag_bonus_costes_critico = state.get("flag_bonus_costes_critico")
    flag_penalizar_tamano_no_compacto = state.get("flag_penalizar_tamano_no_compacto")
    flag_bonus_singularidad_lifestyle = state.get("flag_bonus_singularidad_lifestyle")
    flag_deportividad_lifestyle = state.get("flag_deportividad_lifestyle")
    flag_ajuste_maletero_personal = state.get("flag_ajuste_maletero_personal")
    km_anuales_val = state.get("km_anuales_estimados")

    # 2. Obtén el thread_id directamente del objeto 'config'
    # Esta es la forma correcta y segura de accederlo.
    configurable_config = config.get("configurable", {})
    thread_id = configurable_config.get("thread_id", "unknown_thread_in_node") # Fallback por si acaso

    logging.info(f"INFO (Buscar BQ) ► Ejecutando búsqueda para thread_id: {thread_id}")
    
    coches_encontrados_raw = [] 
    coches_encontrados = []
    sql_ejecutada = None 
    params_ejecutados = None 
    mensaje_coches = "No pude realizar la búsqueda de coches en este momento." # Default para la parte de coches

    if filtros_finales_obj and pesos_finales:
        filtros_para_bq = {}
        if hasattr(filtros_finales_obj, "model_dump"):
             filtros_para_bq.update(filtros_finales_obj.model_dump(mode='json', exclude_none=True))
        elif isinstance(filtros_finales_obj, dict): 
             filtros_para_bq.update({k: v for k, v in filtros_finales_obj.items() if v is not None})

        if economia_obj and economia_obj.modo == 2:
            filtros_para_bq['modo'] = 2
            filtros_para_bq['submodo'] = economia_obj.submodo
            if economia_obj.submodo == 1:
                 filtros_para_bq['pago_contado'] = economia_obj.pago_contado
            elif economia_obj.submodo == 2:
                 filtros_para_bq['cuota_max'] = economia_obj.cuota_max
        
        filtros_para_bq['penalizar_puertas_bajas'] = penalizar_puertas_flag
        filtros_para_bq['flag_penalizar_low_cost_comodidad'] = flag_penalizar_lc_comod
        filtros_para_bq['flag_penalizar_deportividad_comodidad'] = flag_penalizar_dep_comod
        filtros_para_bq['flag_penalizar_antiguo_por_tecnologia'] = flag_penalizar_antiguo_tec_val
        filtros_para_bq['aplicar_logica_distintivo_ambiental'] = flag_aplicar_distintivo_val
        filtros_para_bq['penalizar_bev_reev_aventura_ocasional'] = flag_pen_bev_reev_avent_ocas
        filtros_para_bq['penalizar_phev_aventura_ocasional'] = flag_pen_phev_avent_ocas
        filtros_para_bq['penalizar_electrificados_aventura_extrema'] = flag_pen_electrif_avent_extr
        filtros_para_bq['es_municipio_zbe'] = flag_es_zbe_val
        filtros_para_bq['favorecer_carroceria_montana'] = flag_fav_car_montana_val
        filtros_para_bq['favorecer_carroceria_comercial'] = flag_fav_car_comercial_val
        filtros_para_bq['favorecer_carroceria_pasajeros_pro'] = flag_fav_car_pasajeros_pro_val
        filtros_para_bq['desfavorecer_carroceria_no_aventura'] = flag_desfav_car_no_aventura_val
        filtros_para_bq['favorecer_suv_aventura_ocasional'] = flag_fav_suv_aventura_ocasional
        filtros_para_bq['favorecer_pickup_todoterreno_aventura_extrema'] = flag_fav_pickup_todoterreno_aventura_extrema
        filtros_para_bq['aplicar_logica_objetos_especiales'] = flag_aplicar_logica_objetos_especiales
        filtros_para_bq['favorecer_carroceria_confort'] = flag_fav_carroceria_confort
        filtros_para_bq['flag_logica_uso_ocasional'] = flag_logica_uso_ocasional
        filtros_para_bq['flag_favorecer_bev_uso_definido'] = flag_favorecer_bev_uso_definido
        filtros_para_bq['flag_penalizar_phev_uso_intensivo'] = flag_penalizar_phev_uso_intensivo
        filtros_para_bq['flag_favorecer_electrificados_por_punto_carga'] = flag_favorecer_electrificados_por_punto_carga
        filtros_para_bq['flag_logica_diesel_ciudad'] = flag_logica_diesel_ciudad
        filtros_para_bq['penalizar_awd_ninguna_aventura'] = penalizar_awd_ninguna_val
        filtros_para_bq['favorecer_awd_aventura_ocasional'] = favorecer_awd_ocasional_val
        filtros_para_bq['favorecer_awd_aventura_extrema'] = favorecer_awd_extrema_val
        filtros_para_bq['flag_bonus_nieve_val'] = flag_bonus_nieve_val
        filtros_para_bq['flag_bonus_montana_val'] = flag_bonus_montana_val
        filtros_para_bq['flag_logica_reductoras_aventura'] = flag_reductoras_aventura_val
        filtros_para_bq['flag_bonus_awd_clima_adverso'] = flag_bonus_awd_clima_adverso
        filtros_para_bq['flag_bonus_seguridad_critico'] = flag_bonus_seguridad_critico
        filtros_para_bq['flag_bonus_seguridad_fuerte'] = flag_bonus_seguridad_fuerte
        filtros_para_bq['flag_bonus_fiab_dur_critico'] = flag_bonus_fiab_dur_critico
        filtros_para_bq['flag_bonus_fiab_dur_fuerte'] = flag_bonus_fiab_dur_fuerte
        filtros_para_bq['flag_bonus_costes_critico'] = flag_bonus_costes_critico
        filtros_para_bq['flag_penalizar_tamano_no_compacto'] = flag_penalizar_tamano_no_compacto
        filtros_para_bq['flag_bonus_singularidad_lifestyle'] = flag_bonus_singularidad_lifestyle
        filtros_para_bq['flag_deportividad_lifestyle'] = flag_deportividad_lifestyle
        filtros_para_bq['flag_ajuste_maletero_personal'] = flag_ajuste_maletero_personal
        filtros_para_bq['km_anuales_estimados'] = km_anuales_val
        
        logging.debug(f"DEBUG (Buscar BQ) ► Llamando a buscar_coches_bq con k={k_coches}")
        logging.debug(f"DEBUG (Buscar BQ) ► Filtros para BQ: {filtros_para_bq}") 
        logging.debug(f"DEBUG (Buscar BQ) ► Pesos para BQ: {pesos_finales}") 
        
        try:
            resultados_tupla = buscar_coches_bq(
                filtros=filtros_para_bq, 
                pesos=pesos_finales, 
                k=k_coches
            )
            if isinstance(resultados_tupla, tuple) and len(resultados_tupla) == 3: #val coches encontrados (coches_encontrados_raw),(sql_ejecutada),(params_ejecutados).
                coches_encontrados_raw, sql_ejecutada, params_ejecutados = resultados_tupla
            else: 
                logging.warning("WARN (Buscar BQ) ► buscar_coches_bq no devolvió SQL/params. Logueo será parcial.")
                coches_encontrados_raw = resultados_tupla if isinstance(resultados_tupla, list) else []
            # --- SANITIZACIÓN DE NaN ---
            if coches_encontrados_raw:
                for coche_raw in coches_encontrados_raw:
                    coches_encontrados.append(sanitize_dict_for_json(coche_raw))
                logging.info(f"INFO (Buscar BQ) ► {len(coches_encontrados_raw)} coches crudos se limpian NaN para ->  {len(coches_encontrados)} coches.")
            # --- FIN SANITIZACIÓN ---
            
            if coches_encontrados:
                mensaje_coches = f"¡Listo! Basado en todo lo que hablamos, aquí tienes {len(coches_encontrados)} coche(s) que podrían interesarte:\n\n"
                
                # ##CODIGO BUCLE PARA CUANDO INTEGREMOS LOGICA EXPLICACION LLM
                # # #coches_para_df = []
                # # for i, coche_dict_completo in enumerate(coches_encontrados):
                # #     # --- LLAMAR AL NUEVO GENERADOR DE EXPLICACIONES ---
                # #     explicacion_coche = generar_explicacion_coche_mejorada(
                # #         coche_dict_completo=coche_dict_completo,
                # #         preferencias_usuario=preferencias_obj,
                # #         pesos_normalizados=pesos_finales,
                # #         flag_penalizar_lc_comod=flag_penalizar_lc_comod,
                # #         flag_penalizar_dep_comod=flag_penalizar_dep_comod,
                # #         flag_penalizar_ant_tec=flag_penalizar_antiguo_tec_val,
                # #         flag_es_zbe=flag_es_zbe_val,
                # #         flag_aplicar_dist_gen=flag_aplicar_distintivo_val,
                # #         flag_penalizar_puertas = penalizar_puertas_flag,                 
                # #     )
                # #     # --- FIN LLAMADA ---
                # #     # Añadir la explicación al string del mensaje
                # #     # (Formato más integrado con la tabla)
                # #     mensaje_coches += f"\n**{i+1}. {coche_dict_completo.get('nombre', 'Coche Desconocido')}**"
                # #     if coche_dict_completo.get('precio_compra_contado') is not None:
                # #         precio_f = f"{coche_dict_completo.get('precio_compra_contado'):,.0f}€".replace(",",".")
                # #         mensaje_coches += f" - {precio_f}"
                # #     if coche_dict_completo.get('score_total') is not None:
                # #         score_f = f"{coche_dict_completo.get('score_total'):.3f}"
                # #         mensaje_coches += f" (Score: {score_f})"
                # #     mensaje_coches += f"\n   *Por qué podría interesarte:* {explicacion_coche}\n"


                # # Si quieres una tabla resumen de los coches (además de la explicación individual)
                # # df_coches_display = pd.DataFrame(coches_para_df)
                # # columnas_deseadas_tabla = ['Nº', 'nombre', 'marca', 'precio_compra_contado', 'score_total', 'tipo_carroceria', 'tipo_mecanica']
                # # # ... (formateo de columnas del df_coches_display) ...
                # # tabla_coches_md = df_coches_display[columnas_deseadas_tabla].to_markdown(index=False)
                # # mensaje_coches += "\n" + tabla_coches_md + "\n"
                
                # mensaje_coches += "\n¿Qué te parecen estas opciones? ¿Hay alguno que te interese para ver más detalles?\n"
                # try:
                #     df_coches = pd.DataFrame(coches_encontrados)
                #     columnas_deseadas = [ # Define tus columnas deseadas
                #         'nombre', 'marca', 'precio_compra_contado', 'score_total',
                #         'tipo_carroceria', 'tipo_mecanica', 'traccion', 'reductoras', 'foto' 
                        
                #     ]
                #     columnas_a_mostrar = [col for col in columnas_deseadas if col in df_coches.columns]
                    
                #     if columnas_a_mostrar:
                #         if 'precio_compra_contado' in df_coches.columns:
                #             df_coches['precio_compra_contado'] = df_coches['precio_compra_contado'].apply(lambda x: f"{x:,.0f}€".replace(",",".") if isinstance(x, (int, float)) else "N/A")
                #         if 'score_total' in df_coches.columns:
                #              df_coches['score_total'] = df_coches['score_total'].apply(lambda x: f"{x:.3f}" if isinstance(x, float) else x)
                #         tabla_coches_md = df_coches[columnas_a_mostrar].to_markdown(index=False)
                #         mensaje_coches += tabla_coches_md
                #     else:
                #         mensaje_coches += "No se pudieron formatear los detalles de los coches."
                # except Exception as e_format_coches:
                #     logging.error(f"ERROR (Buscar BQ) ► Falló el formateo de la tabla de coches: {e_format_coches}")
                #     mensaje_coches += "Hubo un problema al mostrar los detalles. Aquí una lista simple:\n"
                #     for i, coche in enumerate(coches_encontrados):
                #         nombre = coche.get('nombre', 'N/D'); precio = coche.get('precio_compra_contado')
                #         precio_str = f"{precio:,.0f}€".replace(",",".") if isinstance(precio, (int, float)) else "N/A"
                #         mensaje_coches += f"{i+1}. {nombre} - {precio_str}\n"
                # Iteramos sobre cada coche para construir su "tarjeta" de presentación
                for i, coche in enumerate(coches_encontrados):
                    
                    # --- 1. Preparamos los datos de cada coche ---
                    nombre = coche.get('nombre', 'Coche Desconocido')
                    url_foto = coche.get('foto')
                    tipo_mecanica = coche.get('tipo_mecanica')
                    anyo_unidad = coche.get('ano_unidad')
                    traccion = coche.get('traccion')
                    
                    # Formateamos el precio y el score para mostrarlos
                    precio_str = "N/A"
                    if coche.get('precio_compra_contado') is not None:
                        try:
                            precio_str = f"{coche.get('precio_compra_contado'):,.0f}€".replace(",", ".")
                        except (ValueError, TypeError):
                            pass # Mantenemos "N/A" si el formato falla

                    score_str = "N/A"
                    if coche.get('score_total') is not None:
                        try:
                            score_str = f"{coche.get('score_total'):.2f} pts"
                        except (ValueError, TypeError):
                            pass

                    # --- 2. Generamos la explicación personalizada (lógica omitida temporalmente) ---
                    # Se omite la llamada a generar_explicacion_coche_mejorada y se usa un texto provisional.
                    explicacion_coche = "Análisis detallado de la recomendación pendiente de desarrollo."

                    # --- 3. Construimos el mensaje en Markdown para este coche ---
                    mensaje_coches += f"\n---\n"  # Separador horizontal
                    mensaje_coches += f"### {i+1}. {nombre}\n"  # Título del coche

                    # ✅ CORREGIDO: Añadido un salto de línea '\n' al final de esta línea.
                    # Esto asegura que la imagen aparezca en una nueva línea.
                    mensaje_coches += f"> {tipo_mecanica} | {anyo_unidad} | {traccion}\n"

                    # Añadimos la imagen si la URL existe
                    if url_foto and url_foto.strip():
                        mensaje_coches += f"![Foto de {nombre}]({url_foto})\n"

                    # Añadimos los detalles clave y la explicación
                    # Se usa un solo '\n' para que no haya un espacio excesivo con la explicación.
                    mensaje_coches += f"**Precio:** {precio_str} | **Puntuación:** {score_str}\n"
                    mensaje_coches += f"*{explicacion_coche}*\n"
                
                mensaje_coches += "\n\n---\n\n¿Qué te parecen estas opciones? ¿Hay alguno que te interese para ver más detalles?"
                # --- ✅ FIN DE LA NUEVA LÓGICA DE PRESENTACIÓN ---
               
                
            else:
                # ... (Tu lógica de sugerencias heurísticas para mensaje_coches) ...
                mensaje_coches = "He aplicado todos tus filtros, pero no encontré coches que coincidan exactamente. ¿Quizás quieras redefinir algún criterio?"
                print("INFO (Buscar BQ) ► No se encontraron coches. Intentando generar sugerencia.")
                
                # Usaremos esta variable para construir la sugerencia
                _sugerencia_generada = None
                
                # Heurística 1: Tipo de Mecánica
                tipos_mecanica_actuales = filtros_para_bq.get("tipo_mecanica", [])
                mecanicas_electricas_puras = {"BEV", "REEV"} # Conjunto para chequeo eficiente
                es_solo_electrico_puro = all(m in mecanicas_electricas_puras for m in tipos_mecanica_actuales)
                
                if tipos_mecanica_actuales and es_solo_electrico_puro and len(tipos_mecanica_actuales) <= 3:
                    _sugerencia_generada = (
                        "No encontré coches que sean únicamente 100% eléctricos (como BEV o REEV) "
                        "con el resto de tus criterios. ¿Te gustaría que amplíe la búsqueda para incluir también "
                        "vehículos híbridos (enchufables o no) y de gasolina?"
                    )
                
                # Heurística 2: Precio/Cuota (si no se sugirió mecánica)
                if not _sugerencia_generada: # Solo si no se hizo la sugerencia anterior
                    precio_actual = filtros_para_bq.get("precio_max_contado_recomendado") or filtros_para_bq.get("pago_contado")
                    cuota_actual = filtros_para_bq.get("cuota_max_calculada") or filtros_para_bq.get("cuota_max")

                    if precio_actual is not None:
                        nuevo_precio_sugerido = int(precio_actual * 1.20)
                        _sugerencia_generada = (
                            f"Con el presupuesto actual al contado de aproximadamente {precio_actual:,.0f}€ no he encontrado opciones que cumplan todo lo demás. "
                            f"¿Estarías dispuesto a considerar un presupuesto hasta unos {nuevo_precio_sugerido:,.0f}€?"
                        )
                    elif cuota_actual is not None:
                        nueva_cuota_sugerida = int(cuota_actual * 1.20)
                        _sugerencia_generada = (
                            f"Con la cuota mensual de aproximadamente {cuota_actual:,.0f}€ no he encontrado opciones. "
                            f"¿Podríamos considerar una cuota hasta unos {nueva_cuota_sugerida:,.0f}€/mes?"
                        )
                if _sugerencia_generada:
                    mensaje_coches = _sugerencia_generada # Usar la sugerencia específica
                
                if not _sugerencia_generada: # Si ninguna heurística aplicó
                    _sugerencia_generada = "He aplicado todos tus filtros, pero no encontré coches que coincidan exactamente en este momento. ¿Quizás quieras redefinir algún criterio general?"
                mensaje_coches = _sugerencia_generada

        except Exception as e_bq:
            logging.error(f"ERROR (Buscar BQ) ► Falló la ejecución de buscar_coches_bq: {e_bq}")
            traceback.print_exc()
            mensaje_coches = f"Lo siento, tuve un problema al buscar en la base de datos: {e_bq}"
    else:
        logging.error("ERROR (Buscar BQ) ► Faltan filtros o pesos finales en el estado para la búsqueda.")
        mensaje_coches = "Lo siento, falta información interna para realizar la búsqueda final."

    # Logueo a BigQuery (como lo tenías)
    if filtros_finales_obj and pesos_finales: 
        try:
            log_busqueda_a_bigquery(
                id_conversacion=thread_id,
                preferencias_usuario_obj=state.get("preferencias_usuario"),
                filtros_aplicados_obj=filtros_finales_obj, 
                economia_usuario_obj=economia_obj,
                pesos_aplicados_dict=pesos_finales,
                tabla_resumen_criterios_md=tabla_resumen_criterios_md, # <-- Viene del estado
                coches_recomendados_list=coches_encontrados,
                num_coches_devueltos=len(coches_encontrados),
                sql_query_ejecutada=sql_ejecutada, # <-- De la llamada a buscar_coches_bq
                sql_params_list=params_ejecutados  # <-- De la llamada a buscar_coches_bq
            )
        except Exception as e_log:
            print(f"ERROR (Buscar BQ) ► Falló el logueo a BigQuery: {e_log}")
            traceback.print_exc()
#     # --- FIN LLAMADA AL LOGGER ---
        pass # Placeholder

    # --- CONSTRUIR MENSAJE FINAL COMBINADO ---
    mensaje_final_completo = f"{mensaje_coches}" #f"{tabla_resumen_criterios_md}\n\n---\n\n{mensaje_coches}"
    
    final_ai_msg = AIMessage(content=mensaje_final_completo)
    historial_final = list(historial) 
    if not historial or historial[-1].content != final_ai_msg.content:
        historial_final.append(final_ai_msg)
    else:
        logging.debug("DEBUG (Buscar BQ) ► Mensaje final combinado duplicado, no se añade.")

    # Devolver estado final
    return {
        "messages": historial_final,
        "coches_recomendados": coches_encontrados, 
        "tabla_resumen_criterios": tabla_resumen_criterios_md, # Propagar la tabla (útil para logging)
        # Propagar otros campos del estado que no se modifican aquí pero son necesarios
        "preferencias_usuario": state.get("preferencias_usuario"),
        "info_pasajeros": state.get("info_pasajeros"),
        "filtros_inferidos": filtros_finales_obj, 
        "economia": economia_obj, 
        "pesos": pesos_finales, 
        "penalizar_puertas_bajas": penalizar_puertas_flag, 
       # "priorizar_ancho": state.get("priorizar_ancho"), 
        "flag_penalizar_low_cost_comodidad": flag_penalizar_lc_comod,
        "flag_penalizar_deportividad_comodidad": flag_penalizar_dep_comod, 
        "flag_penalizar_antiguo_por_tecnologia": flag_penalizar_antiguo_tec_val,
        "aplicar_logica_distintivo_ambiental": flag_aplicar_distintivo_val,
        "es_municipio_zbe": flag_es_zbe_val, 
        "penalizar_bev_reev_aventura_ocasional": flag_pen_bev_reev_avent_ocas,
        "penalizar_phev_aventura_ocasional": flag_pen_phev_avent_ocas,
        "penalizar_electrificados_aventura_extrema": flag_pen_electrif_avent_extr,
        "codigo_postal_usuario": state.get("codigo_postal_usuario"),
        "info_clima_usuario": state.get("info_clima_usuario"),
        "favorecer_carroceria_montana": flag_fav_car_montana_val,
        "favorecer_carroceria_comercial": flag_fav_car_comercial_val,
        "favorecer_carroceria_pasajeros_pro": flag_fav_car_pasajeros_pro_val,
        "desfavorecer_carroceria_no_aventura": flag_desfav_car_no_aventura_val,
        "favorecer_suv_aventura_ocasional" : flag_fav_suv_aventura_ocasional,
        'favorecer_pickup_todoterreno_aventura_extrema' : flag_fav_pickup_todoterreno_aventura_extrema,
        'aplicar_logica_objetos_especiales' : flag_aplicar_logica_objetos_especiales,
        'favorecer_carroceria_confort' : flag_fav_carroceria_confort,
        'flag_logica_uso_ocasional' : flag_logica_uso_ocasional,
        'flag_favorecer_bev_uso_definido' : flag_favorecer_bev_uso_definido,
        'flag_penalizar_phev_uso_intensivo': flag_penalizar_phev_uso_intensivo,
        'flag_favorecer_electrificados_por_punto_carga': flag_favorecer_electrificados_por_punto_carga,
        'flag_logica_diesel_ciudad': flag_logica_diesel_ciudad ,
        'penalizar_awd_ninguna_aventura' : penalizar_awd_ninguna_val,
        'favorecer_awd_aventura_ocasional' : favorecer_awd_ocasional_val,
        'favorecer_awd_aventura_extrema' : favorecer_awd_extrema_val,
        'flag_logica_reductoras_aventura' :flag_reductoras_aventura_val,
        'flag_bonus_awd_clima_adverso' : flag_bonus_awd_clima_adverso,
        'flag_bonus_seguridad_critico': flag_bonus_seguridad_critico,
        'flag_bonus_seguridad_fuerte' : flag_bonus_seguridad_fuerte ,
        'flag_bonus_fiab_dur_critico' : flag_bonus_fiab_dur_critico,
        'flag_bonus_fiab_dur_fuerte' : flag_bonus_fiab_dur_fuerte ,
        'flag_bonus_costes_critico' : flag_bonus_costes_critico,
        "flag_penalizar_tamano_no_compacto": flag_penalizar_tamano_no_compacto,
        "flag_bonus_singularidad_lifestyle" : flag_bonus_singularidad_lifestyle,
        "flag_deportividad_lifestyle": flag_deportividad_lifestyle,
        "flag_ajuste_maletero_personal": flag_ajuste_maletero_personal,
        "pregunta_pendiente": None # Este nodo es final para el turno
        
    }

 