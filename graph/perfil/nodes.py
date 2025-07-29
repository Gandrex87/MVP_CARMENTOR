from utils.explanation_generator import generar_explicacion_coche_mejorada # <-- NUEVO IMPORT
from langchain_core.messages import AIMessage , SystemMessage, HumanMessage
from pydantic import ValidationError # Importar para manejo de errores si es necesario
from .state import (EstadoAnalisisPerfil, 
                    PerfilUsuario, 
                    FiltrosInferidos,
                    EconomiaUsuario,
                    InfoPasajeros, CodigoPostalExtraido,
                    InfoClimaUsuario, NivelAventura , FrecuenciaUso, DistanciaTrayecto, FrecuenciaViajesLargos
)
from config.llm import llm_solo_perfil, llm_economia, llm_pasajeros, llm_cp_extractor
from prompts.loader import system_prompt_perfil, prompt_economia_structured_sys_msg, system_prompt_pasajeros, system_prompt_cp
from utils.postprocessing import aplicar_postprocesamiento_perfil, aplicar_postprocesamiento_filtros
from utils.validation import check_perfil_usuario_completeness , check_pasajeros_completo, es_cp_valido
from utils.formatters import formatear_preferencias_en_tabla
from utils.weights import compute_raw_weights, normalize_weights
from utils.bigquery_tools import buscar_coches_bq
from utils.bq_data_lookups import obtener_datos_climaticos_por_cp # IMPORT para la función de búsqueda de clima ---
from utils.conversion import is_yes 
from utils.bq_logger import log_busqueda_a_bigquery
from utils.sanitize_dict_for_json import sanitize_dict_for_json
from utils.question_bank import QUESTION_BANK , PREGUNTAS_CP_INICIAL , PREGUNTAS_CP_REINTENTO ,PREGUNTA_BIENVENIDA
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

# --- INICIO: NODOS PARA ETAPA DE CÓDIGO POSTAL ---
# Su única responsabilidad es generar el saludo y la primera pregunta.


def saludo_y_pregunta_inicial_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Genera el mensaje de bienvenida y la primera pregunta sobre el CP.
    Se ejecuta una sola vez al inicio de la conversación.
    """
    print("--- Ejecutando Nodo: saludo_y_pregunta_inicial_node ---")
    
    # Elegimos uno de los saludos al azar de nuestra lista de constantes.
    welcome_message = random.choice(PREGUNTA_BIENVENIDA)
    
    first_question = (
        "Para empezar, ¿puedes decirme tu código postal? Así podré tener en cuenta "
        "clima, normativas locales, tipo de vías o la disponibilidad de "
        "recarga eléctrica si contemplas un vehículo electrificado."
    )
    
    # Devolvemos dos mensajes para que el frontend pueda mostrarlos por separado
    return {"messages": [AIMessage(content=welcome_message), AIMessage(content=first_question)]}

def preguntar_cp_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Genera la pregunta correcta para el código postal.
    Si es la primera vez, hace la pregunta inicial.
    Si ya hubo un intento fallido, pide que se reintente.
    """
    logging.info("--- Ejecutando Nodo (Refactorizado): preguntar_cp_node ---")
    
    # Comprobamos el contador de intentos, no el valor del CP extraído.
    intentos = state.get("intentos_cp", 0)

    if intentos > 0:
        # Si ya hubo al menos un intento fallido, elegimos una pregunta de reintento al azar.
        pregunta = random.choice(PREGUNTAS_CP_REINTENTO)
    else:
        # Si no hay ningún intento previo, elegimos una pregunta inicial al azar.
        pregunta = random.choice(PREGUNTAS_CP_INICIAL)

    # Añadimos el mensaje al historial
    historial_actual = state.get("messages", [])
    historial_nuevo = list(historial_actual)
    
    if not historial_actual or historial_actual[-1].content != pregunta:
        logging.info(f"DEBUG (Preguntar CP) ► Añadiendo pregunta: {pregunta}")
        historial_nuevo.append(AIMessage(content=pregunta))
    else:
        logging.warning("DEBUG (Preguntar CP) ► Mensaje duplicado, no se añade.")

    return {"messages": historial_nuevo}




def recopilar_cp_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Invoca al LLM con la única tarea de extraer el texto que podría ser
    un código postal del mensaje del usuario.
    """
    logging.info("--- Ejecutando Nodo (Refactorizado): recopilar_cp_node ---")
    
    historial = state.get("messages", [])

    if not historial or isinstance(historial[-1], AIMessage):
        logging.debug("DEBUG (CP) ► No hay nuevo mensaje de usuario para procesar.")
        return {}

    try:
        # Construimos la lista de mensajes manualmente para un control total.
        mensajes_para_llm = [SystemMessage(content=system_prompt_cp), *historial]
        
        # Invocamos al LLM estructurado.
        response: CodigoPostalExtraido = llm_cp_extractor.invoke(
            mensajes_para_llm,
            config={"configurable": {"tags": ["llm_cp_extractor"]}}
        )
        # La única salida de este nodo es el CP extraído, que guardamos en el estado para que el siguiente paso (la arista condicional) lo valide.
        # Ya no necesitamos 'tipo_mensaje' ni 'contenido_mensaje'.
        cp_extraido = response.codigo_postal
        logging.info(f"DEBUG (CP) ► CP extraído por LLM: '{cp_extraido}'")
        
        return {
            "codigo_postal_extraido_temporal": cp_extraido
        }

    except (ValidationError, Exception) as e:
        logging.error(f"ERROR (CP) ► Fallo en la extracción del CP: {e}", exc_info=True)
        # En caso de error, devolvemos un valor nulo para que la validación falle
        # y se pueda volver a preguntar.
        return {"codigo_postal_extraido_temporal": None}



def validar_y_decidir_cp_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Valida el CP extraído y decide el siguiente paso.
    Si el CP es válido, avanza.
    Si es inválido, comprueba el número de intentos. Si es el primer
    intento, repregunta. Si es el segundo, avanza sin CP.
    """
    logging.info("--- Ejecutando Nodo (Refactorizado): validar_y_decidir_cp_node ---")
    
    cp_extraido = state.get("codigo_postal_extraido_temporal")
    intentos = state.get("intentos_cp", 0)

    if es_cp_valido(cp_extraido):
        logging.info(f"DEBUG (CP Val) ► CP '{cp_extraido}' es válido. Avanzando.")
        # Guardamos el CP final y preparamos la decisión para avanzar.
        return {
            "codigo_postal_usuario": cp_extraido,
            "_decision_cp_validation": "avanzar_a_clima"
        }
    else:
        # El CP extraído no es válido.
        if intentos >= 1:
            # Este fue el segundo intento (o más). Dejamos de preguntar.
            logging.warning("WARN (CP Val) ► Segundo intento fallido. Avanzando sin CP.")
            return {
                "codigo_postal_usuario": None, # Aseguramos que no hay CP
                "_decision_cp_validation": "avanzar_a_clima"
            }
        else:
            # Este fue el primer intento fallido. Incrementamos el contador y repreguntamos.
            logging.info("INFO (CP Val) ► Primer intento fallido. Repreguntando.")
            return {
                "intentos_cp": intentos + 1,
                "_decision_cp_validation": "repreguntar_cp"
            }


def buscar_info_clima_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Si hay un código postal válido, busca la información climática en BQ.
    Actualiza state['info_clima_usuario'].
    """
    print("--- Ejecutando Nodo: buscar_info_clima_node ---")
    cp_usuario = state.get("codigo_postal_usuario")
    info_clima_calculada = None

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
#     Procesa la entrada del usuario, llama al LLM para extraer nueva información,
#     y FUSIONA esa nueva información con el perfil existente.
#     --- VERSIÓN FINAL COMPLETAMENTE REFACTORIZADA ---
#     """
#     logging.info("--- Ejecutando Nodo (Final): recopilar_preferencias_node ---")
    
#     historial = state.get("messages", [])
#     preferencias_actuales_obj = state.get("preferencias_usuario") or PerfilUsuario()

#     # Si el último mensaje es de la IA, no hay nueva entrada de usuario que procesar.
#     if not historial or isinstance(historial[-1], AIMessage):
#         logging.debug("(Perfil) ► No hay nuevo mensaje de usuario para procesar.")
#         return {} # No hay cambios en el estado

#     logging.debug("(Perfil) ► Llamando a llm_solo_perfil...")
    
#     perfil_final_a_guardar = preferencias_actuales_obj # Por defecto, mantenemos el perfil actual

#     try:
#         # La variable 'response' ahora es de tipo PerfilUsuario directamente.
#         response: PerfilUsuario = llm_solo_perfil.invoke(
#             [SystemMessage(content=system_prompt_perfil), *historial],
#             config={"configurable": {"tags": ["llm_solo_perfil"]}} 
#         )
        
#         # 'response' es ahora el objeto PerfilUsuario que necesitamos.
#         preferencias_del_llm = response
        
#         # --- Lógica de Fusión Inteligente ---
#         if preferencias_del_llm:
#             nuevos_datos = preferencias_del_llm.model_dump(exclude_unset=True)
            
#             if nuevos_datos:
#                 logging.info(f"DEBUG (Perfil) ► Fusionando nuevos datos del LLM: {nuevos_datos}")
#                 perfil_consolidado = preferencias_actuales_obj.model_copy(update=nuevos_datos)
#             else:
#                 logging.info("DEBUG (Perfil) ► El LLM no extrajo nuevos datos.")
#                 perfil_consolidado = preferencias_actuales_obj
            
#             # Asumiendo que tienes una función de post-procesamiento
#             perfil_final_a_guardar = aplicar_postprocesamiento_perfil(perfil_consolidado)
#         else:
#             logging.warning("WARN (Perfil) ► El LLM no devolvió un objeto de preferencias.")
#             perfil_final_a_guardar = preferencias_actuales_obj

#     except ValidationError as e_val:
#         logging.error(f"ERROR (Perfil) ► Error de Validación Pydantic en llm_solo_perfil: {e_val.errors()}")
#         # En caso de error de formato, no actualizamos el perfil para no corromperlo.
#         perfil_final_a_guardar = preferencias_actuales_obj 

#     except Exception as e_general:
#         logging.error(f"ERROR (Perfil) ► Fallo general al invocar llm_solo_perfil o en post-procesamiento: {e_general}", exc_info=True)
#         perfil_final_a_guardar = preferencias_actuales_obj

#     # Este nodo solo actualiza el perfil. No devuelve mensajes.
#     return {
#         "preferencias_usuario": perfil_final_a_guardar,
#     }

def recopilar_preferencias_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Procesa la entrada del usuario, llama al LLM para extraer nueva información,
    y FUSIONA esa nueva información con el perfil existente.
    --- VERSIÓN CORREGIDA PARA EVITAR ALUCINACIONES ---
    """
    logging.info("--- Ejecutando Nodo (Final): recopilar_preferencias_node ---")
    
    historial = state.get("messages", [])
    preferencias_actuales_obj = state.get("preferencias_usuario") or PerfilUsuario()

    # Si el último mensaje no es del usuario, no hay nueva entrada que procesar.
    if not historial or not isinstance(historial[-1], HumanMessage):
        logging.debug("(Perfil) ► No hay nuevo mensaje de usuario para procesar.")
        return {} 

    logging.debug("(Perfil) ► Llamando a llm_solo_perfil con contexto limitado...")
    
    # --- ✅ CAMBIO CLAVE: ACORTAR EL CONTEXTO ---
    # En lugar de pasar todo el historial, pasamos solo la última pregunta del agente
    # y la última respuesta del usuario. Esto enfoca al LLM en la tarea inmediata.
    contexto_relevante = historial[-2:]

    perfil_final_a_guardar = preferencias_actuales_obj 

    try:
        response: PerfilUsuario = llm_solo_perfil.invoke(
            # Usamos el contexto acotado en lugar de todo el historial
            [SystemMessage(content=system_prompt_perfil), *contexto_relevante], 
            config={"configurable": {"tags": ["llm_solo_perfil"]}} 
        )
        
        preferencias_del_llm = response
        
        if preferencias_del_llm:
            nuevos_datos = preferencias_del_llm.model_dump(exclude_unset=True)
            
            if nuevos_datos:
                logging.info(f"DEBUG (Perfil) ► Fusionando nuevos datos del LLM: {nuevos_datos}")
                perfil_consolidado = preferencias_actuales_obj.model_copy(update=nuevos_datos)
            else:
                logging.info("DEBUG (Perfil) ► El LLM no extrajo nuevos datos.")
                perfil_consolidado = preferencias_actuales_obj
            
            perfil_final_a_guardar = aplicar_postprocesamiento_perfil(perfil_consolidado)
        else:
            logging.warning("WARN (Perfil) ► El LLM no devolvió un objeto de preferencias.")
            perfil_final_a_guardar = preferencias_actuales_obj

    except Exception as e:
        logging.error(f"ERROR (Perfil) ► Fallo en la invocación del LLM o fusión: {e}", exc_info=True)
        perfil_final_a_guardar = preferencias_actuales_obj

    return {
        "preferencias_usuario": perfil_final_a_guardar,
    }

def _obtener_siguiente_pregunta_perfil(prefs: Optional[PerfilUsuario]) -> str:
    """
    Genera una pregunta específica y variada basada en el primer campo 
    obligatorio que falta en el perfil del usuario, siguiendo un orden secuencial estricto.
    """
    if prefs is None: 
        return "¿Podrías contarme un poco sobre qué buscas o para qué usarás el coche?"

    # --- La función ahora es una secuencia de comprobaciones "planas" ---
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
    # Cada pregunta ahora es una comprobación independiente en el flujo.
    if prefs.tiene_garage is None:
        return random.choice(QUESTION_BANK["tiene_garage"])
    
    # Estas preguntas solo se evalúan si la anterior ya tiene respuesta.
    if is_yes(prefs.tiene_garage) and prefs.espacio_sobra_garage is None:
        return random.choice(QUESTION_BANK["espacio_sobra_garage"])
    
    if is_yes(prefs.tiene_garage) and not is_yes(prefs.espacio_sobra_garage) and not prefs.problema_dimension_garage:
        return random.choice(QUESTION_BANK["problema_dimension_garage"])
        
    if not is_yes(prefs.tiene_garage) and prefs.problemas_aparcar_calle is None:
        return random.choice(QUESTION_BANK["problemas_aparcar_calle"])

    if prefs.tiene_punto_carga_propio is None: return random.choice(QUESTION_BANK["tiene_punto_carga_propio"])
    if prefs.solo_electricos is None: return random.choice(QUESTION_BANK["solo_electricos"])
    
    # Pregunta de transmisión solo si no quiere exclusivamente eléctricos
    if not is_yes(prefs.solo_electricos) and prefs.transmision_preferida is None:
        return random.choice(QUESTION_BANK["transmision_preferida"])
    if prefs.prioriza_baja_depreciacion is None: return random.choice(QUESTION_BANK["prioriza_baja_depreciacion"])     
    # Ratings en el orden correcto
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



def generar_mensaje_transicion_perfil(state: EstadoAnalisisPerfil) -> dict:
    """
    Este nodo se activa una sola vez, cuando el perfil se ha completado.
    Su única responsabilidad es generar un mensaje amigable de transición
    antes de pasar a la siguiente etapa (pasajeros).
    """
    print("--- Ejecutando Nodo: generar_mensaje_transicion_perfil ---")
    
    # Puedes crear varias versiones del mensaje para que el agente suene más dinámico
    mensajes_posibles = [
        "¡Estupendo! Ya tengo una idea muy clara de tus gustos y preferencias. Ahora, para asegurarnos de que el coche se adapte perfectamente a quienes viajarán contigo, hablemos un poco sobre los pasajeros.",
        "¡Perfecto! Hemos completado la primera etapa para definir tu coche ideal. Lo siguiente es pensar en el espacio y la comodidad de las personas que te acompañarán.",
        "¡Genial! Con toda esta información sobre tus preferencias, ya podemos empezar a acotar la búsqueda. El siguiente paso es conocer cuántas personas usarán el coche y sus necesidades."
    ]
    
    # Elegimos uno de los mensajes al azar
    import random
    mensaje_transicion = random.choice(mensajes_posibles)
    
    # Añadimos el mensaje al historial
    historial_actual = state.get("messages", [])
    historial_nuevo = list(historial_actual)
    historial_nuevo.append(AIMessage(content=mensaje_transicion))
    
    print(f"INFO: Añadido mensaje de transición: '{mensaje_transicion}'")
    
    return {"messages": historial_nuevo}



# --- NUEVA ETAPA: PASAJEROS ---
def recopilar_info_pasajeros_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Invoca al LLM con la única tarea de extraer datos del mensaje del usuario
    y rellenar el objeto InfoPasajeros.
    --- VERSIÓN CORREGIDA PARA EVITAR KeyError ---
    """
    logging.info("--- Ejecutando Nodo (Corregido): recopilar_info_pasajeros_node ---")
    
    historial = state.get("messages", [])
    info_pasajeros_actual = state.get("info_pasajeros") or InfoPasajeros()

    if not historial or isinstance(historial[-1], AIMessage):
        logging.debug("DEBUG (Pasajeros) ► No hay nuevo mensaje de usuario para procesar.")
        return {}

    try:
        # --- LÓGICA DE INVOCACIÓN CORREGIDA ---
        # Construimos la lista de mensajes manualmente para evitar el formateo del prompt de sistema.
        mensajes_para_llm = [SystemMessage(content=system_prompt_pasajeros), *historial]
        
        # Invocamos al LLM estructurado con la lista de mensajes y la configuración de tags.
        info_pasajeros_extraida = llm_pasajeros.invoke(
            mensajes_para_llm,
            config={"configurable": {"tags": ["llm_pasajeros"]}}
        )
        
        # --- Lógica de Fusión Inteligente (sin cambios) ---
        nuevos_datos = info_pasajeros_extraida.model_dump(exclude_unset=True)
        
        if nuevos_datos:
            logging.info(f"DEBUG (Pasajeros) ► Fusionando nuevos datos del LLM: {nuevos_datos}")
            info_pasajeros_final = info_pasajeros_actual.model_copy(update=nuevos_datos)
        else:
            logging.info("DEBUG (Pasajeros) ► El LLM no extrajo nuevos datos.")
            info_pasajeros_final = info_pasajeros_actual

    except ValidationError as e_val:
        logging.error(f"ERROR (Pasajeros) ► Error de Validación Pydantic: {e_val.errors()}")
        info_pasajeros_final = info_pasajeros_actual
    except Exception as e_general:
        logging.error(f"ERROR (Pasajeros) ► Fallo general: {e_general}", exc_info=True)
        info_pasajeros_final = info_pasajeros_actual

    return {
        "info_pasajeros": info_pasajeros_final
    }


# def validar_info_pasajeros_node(state: EstadoAnalisisPerfil) -> dict:
#     """Nodo simple que comprueba si la información de pasajeros está completa."""
#     print("--- Ejecutando Nodo: validar_info_pasajeros_node ---")
#     info_pasajeros = state.get("info_pasajeros")
#     # Llama a la función de utilidad (que crearemos en el siguiente paso)
#     if check_pasajeros_completo(info_pasajeros):
#         print("DEBUG (Pasajeros) ► Validación: Info Pasajeros considerada COMPLETA.")
#     else:
#         print("DEBUG (Pasajeros) ► Validación: Info Pasajeros considerada INCOMPLETA.")
#     # No modifica el estado, solo valida para la condición
#     return {**state}



def _obtener_siguiente_pregunta_pasajeros(info: Optional[InfoPasajeros]) -> str:
    """
    Genera la siguiente pregunta de forma determinista basándose en el
    primer campo que falta en el objeto InfoPasajeros.
    """
    if not info or info.suele_llevar_acompanantes is None:
        return "¿Vas a llevar acompañantes en el coche?\n\n* ✅ Sí\n* ❌ No"

    # Si el usuario SÍ lleva acompañantes, continuamos con las sub-preguntas.
    if info.suele_llevar_acompanantes is True:
        if info.frecuencia_viaje_con_acompanantes is None:
            return "Entendido. Y, ¿con qué frecuencia sueles llevar a estos acompañantes? Por ejemplo, ¿de manera ocasional o frecuentemente?"
        

        # Si no sabemos el número de sillas, lo preguntamos.
        if info.num_ninos_silla is None:
            frecuencia_texto = info.frecuencia_viaje_con_acompanantes
            return (f"De acuerdo, los llevas de forma {frecuencia_texto}. "
                    "¿Cuántos de esos acompañantes necesitan una silla infantil? (Puedes responder con un número como 0, 1, 2...)"
                    )

        # Si no sabemos el número de otros pasajeros, lo preguntamos.
        if info.num_otros_pasajeros is None:
            return ("Y además de los que usan silla, ¿cuántos otros pasajeros sueles llevar? "
                    "(adultos, adolescentes, etc. Responde con un número por favor).")

    # Si se llega aquí, significa que la etapa está completa.
    # Esta función no debería ser llamada en ese caso, pero devolvemos
    # un mensaje de confirmación como fallback.
    logging.warning("WARN (_obtener_siguiente_pregunta_pasajeros) ► Se pidió una pregunta, pero la información de pasajeros parece completa.")
    return "¡Perfecto! Tengo toda la información que necesito sobre los pasajeros."


def preguntar_info_pasajeros_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Este nodo ahora es muy simple: obtiene la pregunta correcta de nuestra
    lógica determinista y la añade al historial.
    """
    logging.info("--- Ejecutando Nodo (Refactorizado): preguntar_info_pasajeros_node ---")
    
    info_pasajeros = state.get("info_pasajeros")
    historial_actual = state.get("messages", [])
    
    # Obtenemos la pregunta correcta desde nuestra función lógica.
    pregunta = _obtener_siguiente_pregunta_pasajeros(info_pasajeros)
    
    # Añadimos el mensaje al historial, evitando duplicados.
    if not historial_actual or historial_actual[-1].content != pregunta:
        logging.info(f"DEBUG (Preguntar Pasajeros) ► Añadiendo pregunta: {pregunta}")
        historial_nuevo = list(historial_actual)
        historial_nuevo.append(AIMessage(content=pregunta))
        return {"messages": historial_nuevo}
    
    logging.warning("DEBUG (Preguntar Pasajeros) ► Mensaje duplicado, no se añade.")
    return {} # No hay cambios


def generar_mensaje_transicion_pasajeros(state: EstadoAnalisisPerfil) -> dict:
    """
    Este nodo se activa una sola vez, cuando la info de pasajeros se ha completado.
    Su única responsabilidad es generar un mensaje amigable de transición
    antes de pasar a la siguiente etapa (economía).
    """
    print("--- Ejecutando Nodo: generar_mensaje_transicion_pasajeros ---")
    
    # Creamos varias versiones del mensaje para que el agente suene más dinámico
    mensajes_posibles = [
        "¡Perfecto! Ya tengo claro quiénes te acompañarán habitualmente. Para asegurarnos de encontrar un coche que se ajuste a tu presupuesto, vamos a hablar ahora de la parte económica.",
        "¡Estupendo! Información de pasajeros registrada. El siguiente paso es definir el presupuesto para poder filtrar las mejores opciones para ti.",
        "¡Genial! Con esto terminamos la sección de pasajeros. Ahora, si te parece, continuamos con el apartado económico para acotar la búsqueda."
    ]
    
    # Elegimos uno de los mensajes al azar
    mensaje_transicion = random.choice(mensajes_posibles)
    
    # Añadimos el mensaje al historial
    historial_actual = state.get("messages", [])
    historial_nuevo = list(historial_actual)
    historial_nuevo.append(AIMessage(content=mensaje_transicion))
    
    print(f"INFO: Añadido mensaje de transición de pasajeros: '{mensaje_transicion}'")
    
    return {"messages": historial_nuevo}

def aplicar_filtros_pasajeros_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Calcula filtros/indicadores basados en la información de pasajeros completa
    y los actualiza en el estado.
    --- VERSIÓN CORREGIDA PARA USAR EL MODELO InfoPasajeros REFACTORIZADO ---
    """
    logging.info("--- Ejecutando Nodo: aplicar_filtros_pasajeros_node ---")
    
    info_pasajeros_obj = state.get("info_pasajeros")
    filtros_actuales_obj = state.get("filtros_inferidos") or FiltrosInferidos() 

    penalizar_p = False 
    X = 0
    Z = 0
    frecuencia = None

    if info_pasajeros_obj:
        # ▼▼▼ LÍNEA CORREGIDA ▼▼▼
        # Ya no intentamos acceder al campo 'frecuencia' que fue eliminado.
        # Usamos directamente el campo correcto.
        frecuencia = info_pasajeros_obj.frecuencia_viaje_con_acompanantes
        
        X = info_pasajeros_obj.num_ninos_silla or 0
        Z = info_pasajeros_obj.num_otros_pasajeros or 0
        logging.debug(f"DEBUG (Aplicar Filtros Pasajeros) ► Info recibida: freq='{frecuencia}', X={X}, Z={Z}")
    else:
        logging.error("ERROR (Aplicar Filtros Pasajeros) ► No hay información de pasajeros en el estado.")
        frecuencia = "nunca"

    plazas_calc = X + Z + 1 
    logging.debug(f"DEBUG (Aplicar Filtros Pasajeros) ► Calculado plazas_min = {plazas_calc}")

    if frecuencia and frecuencia == "frecuente":
        if X >= 1:
            penalizar_p = True
            logging.debug("DEBUG (Aplicar Filtros Pasajeros) ► Indicador penalizar_puertas_bajas = True")
    
    update_filtros_dict = {"plazas_min": plazas_calc}
    filtros_actualizados = filtros_actuales_obj.model_copy(update=update_filtros_dict)
    
    return {
        "filtros_inferidos": filtros_actualizados,
        "penalizar_puertas_bajas": penalizar_p,
    }


# --- Fin Nueva Etapa Pasajeros ---
# --- Fin Etapa 1 ---

# --- Etapa 2: Inferencia y Validación de Filtros Técnicos ---
def construir_filtros_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Construye y refina los filtros de búsqueda de forma determinista
    llamando a la función de post-procesamiento. No utiliza LLM.
    --- VERSIÓN CORREGIDA PARA EVITAR LA SOBRESCRITURA DE DATOS ---
    """
    print("--- Ejecutando Nodo: construir_filtros_node ---")
    
    preferencias_obj = state.get("preferencias_usuario")
    info_clima_obj = state.get("info_clima_usuario")

    # ▼▼▼ LÍNEA CORREGIDA 1 ▼▼▼
    # Obtenemos el objeto de filtros del estado actual. Este objeto ya contiene
    # los datos económicos calculados en el nodo anterior.
    filtros_desde_estado = state.get("filtros_inferidos") or FiltrosInferidos()

    if not preferencias_obj:
        print("ERROR (Filtros) ► Nodo ejecutado pero 'preferencias_usuario' no existe. No se pueden construir filtros.")
        return {"filtros_inferidos": filtros_desde_estado}

    print("DEBUG (Filtros) ► Preferencias e info_clima disponibles. Construyendo filtros...")

    try:
        # ▼▼▼ LÍNEA CORREGIDA 2 ▼▼▼
        # Pasamos el objeto de filtros que hemos recuperado del estado (que ya tiene
        # los datos económicos) a la función de post-procesamiento.
        filtros_finales = aplicar_postprocesamiento_filtros(
            filtros=filtros_desde_estado,
            preferencias=preferencias_obj,
            info_clima=info_clima_obj 
        )
        print(f"DEBUG (Filtros) ► Filtros finales construidos: {filtros_finales}")

    except Exception as e_post:
        print(f"ERROR (Filtros) ► Fallo construyendo los filtros: {e_post}")
        traceback.print_exc()
        filtros_finales = filtros_desde_estado
        
    return {
        "filtros_inferidos": filtros_finales
    }

# --- Fin Etapa 2 ---


# --- Etapa 3: Inferencia y Validación de Recopilación de Economía ---

# --- Lógica de Preguntas (El "Cerebro") ---

def _obtener_siguiente_pregunta_economia(econ: Optional[EconomiaUsuario]) -> str:
    """
    Genera la siguiente pregunta económica de forma determinista basándose
    en el primer campo que falta.
    --- VERSIÓN FINAL CORREGIDA CON PREGUNTAS DE SEGUIMIENTO ---
    """
    if not econ or econ.presupuesto_definido is None:
        return (
            "Para definir tu presupuesto, ¿qué prefieres?\n\n"
            "* 1️⃣ Prefiero que me aconsejes con criterios de inteligencia financiera.\n"
            "* 2️⃣ Prefiero indicar yo mismo cuánto y cómo gastar."
        )

    if econ.presupuesto_definido is False: # Rama "Asesoramiento"
        if econ.ingresos is None:
            return "¿Cuáles son tus ingresos netos anuales aproximados? Este dato es clave para darte una recomendación financiera sólida."
        if econ.ahorro is None:
            return "Gracias. Ahora, ¿de cuántos ahorros dispones para la compra del vehículo?"
    
    elif econ.presupuesto_definido is True: # Rama "Usuario Define"
        if econ.tipo_presupuesto is None:
            
            # ▼▼▼ PREGUNTA REFORMULADA Y ÚNICA ▼▼▼
            return (
                "Perfecto. Al indicar tú el presupuesto, ¿qué modalidad prefieres?\n\n"
                "* 1️⃣ Un pago único al contado.\n"
                "* 2️⃣ Una cuota mensual de financiación."
            )
        
        # 2. Si eligió "contado", pero no ha dado la cifra, se le pregunta.
        if econ.tipo_presupuesto == "contado" and econ.pago_contado is None:
            return "¿Cuál es tu presupuesto? Puedes indicarme un pago máximo al contado."

        # 3. Si eligió "financiado", pero no ha dado la cifra, se le pregunta.
        if econ.tipo_presupuesto == "financiado" and econ.cuota_max is None:
            return "Indícame la cuota máxima que estás dispuesto a pagar por el coche."

    # Si se llega aquí, la etapa está completa. Devolvemos una confirmación.
    return "¡Entendido! Ya tengo toda la información económica que necesito."



def preguntar_economia_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Obtiene la pregunta correcta de nuestra lógica determinista y la
    añade al historial.
    """
    logging.info("--- Ejecuting Nodo (Refactorizado): preguntar_economia_node ---")
    
    economia = state.get("economia")
    historial_actual = state.get("messages", [])
    
    pregunta = _obtener_siguiente_pregunta_economia(economia)
    
    historial_nuevo = list(historial_actual)
    if not historial_actual or historial_actual[-1].content != pregunta:
        logging.info(f"DEBUG (Preguntar Economía) ► Añadiendo pregunta: {pregunta}")
        historial_nuevo.append(AIMessage(content=pregunta))
    else:
        logging.warning("DEBUG (Preguntar Economía) ► Mensaje duplicado, no se añade.")

    return {"messages": historial_nuevo}


def recopilar_economia_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Primero intenta manejar respuestas numéricas simples de forma determinista.
    Si la respuesta es compleja, delega la extracción al LLM.
    --- VERSIÓN FINAL REFORZADA Y DETERMINISTA ---
    """
    logging.info("--- Ejecutando Nodo (Reforzado): recopilar_economia_node ---")

    historial = state.get("messages", [])
    economia_actual = state.get("economia") or EconomiaUsuario()

    if not historial or not isinstance(historial[-1], HumanMessage):
        return {}

    # Extraemos la última pregunta y respuesta para analizarlas
    last_ai_message = historial[-2].content if len(historial) > 1 else ""
    last_human_message = historial[-1].content.strip().lower()

    # --- ✅ MANEJO DETERMINISTA DE RESPUESTAS NUMÉRICAS ---
    # Interceptamos respuestas simples ("1", "2", etc.) antes de llamar al LLM.
    
    update_data = None
    
    # Caso 1: El usuario elige entre "Asesoramiento" o "Presupuesto Propio"
    # Caso 1: Busca la frase clave de la primera pregunta.
    if "para definir tu presupuesto" in last_ai_message.lower():
        if last_human_message in ["1", "la 1", "1️⃣"]:
            update_data = {"presupuesto_definido": False}
        elif last_human_message in ["2", "la 2", "2️⃣"]:
            update_data = {"presupuesto_definido": True}

    # Caso 2: Busca la frase clave de la segunda pregunta (la reformulada).
    elif "¿qué modalidad prefieres?" in last_ai_message.lower():
        if last_human_message in ["1", "la 1", "1️⃣"]:
            update_data = {"tipo_presupuesto": "contado"}
        elif last_human_message in ["2", "la 2", "2️⃣"]:
            update_data = {"tipo_presupuesto": "financiado"}


    # Si hemos encontrado una correspondencia determinista, la aplicamos y terminamos.
    if update_data:
        logging.info(f"DEBUG (Economía) ► Aplicando actualización determinista: {update_data}")
        economia_final = economia_actual.model_copy(update=update_data)
        return {"economia": economia_final}
    
    # --- SI LA RESPUESTA NO ERA SIMPLE, PROCEDEMOS CON EL LLM ---
    logging.debug("DEBUG (Economía) ► La respuesta no es simple, delegando al LLM...")
    
    # Usamos el contexto limitado que ya habiamos implementado
    contexto_relevante = historial[-2:]
    
    try:
        mensajes_para_llm = [SystemMessage(content=prompt_economia_structured_sys_msg), *contexto_relevante]
        response: EconomiaUsuario = llm_economia.invoke(
            mensajes_para_llm, config={"configurable": {"tags": ["llm_economia"]}}
        )
        
        # ... (el resto de la lógica de fusión y normalización que ya teníamos)
        if response and response.tipo_presupuesto:
            response.tipo_presupuesto = response.tipo_presupuesto.lower()
            
        nuevos_datos = response.model_dump(exclude_unset=True)
        if nuevos_datos:
            logging.info(f"DEBUG (Economía) ► Fusionando nuevos datos del LLM: {nuevos_datos}")
            economia_final = economia_actual.model_copy(update=nuevos_datos)
        else:
            economia_final = economia_actual
            
        return {"economia": economia_final}

    except Exception as e:
        logging.error(f"ERROR (Economía) ► Fallo en la extracción de datos económicos: {e}", exc_info=True)
        return {}


# --- Fin Etapa 3 ---


# --- Etapa 4: nodo economia ---

def calcular_recomendacion_economia_modo1_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Calcula la recomendación económica para el Modo 1, con logging detallado
    para una depuración completa del proceso de decisión.
    --- VERSIÓN CORREGIDA PARA USAR EL MODELO EconomiaUsuario REFACTORIZADO ---
    """
    logging.info("--- Ejecutando Nodo: calcular_recomendacion_economia_modo1_node ---")
    
    economia_obj = state.get("economia")
    filtros_obj = state.get("filtros_inferidos")

    if filtros_obj is None:
        filtros_obj = FiltrosInferidos()
        
    filtros_actualizados = filtros_obj.model_copy(deep=True)
    
    # ▼▼▼ LÓGICA CORREGIDA ▼▼▼
    # En lugar de comprobar 'modo == 1', ahora comprobamos si 'presupuesto_definido' es False.
    if economia_obj and economia_obj.presupuesto_definido is False:
        logging.info("DEBUG (CalcEconModo1) ► Modo 'Asesoramiento' detectado. Iniciando cálculo...")
        try:
            ingresos = economia_obj.ingresos
            ahorro = economia_obj.ahorro
            #anos_posesion_usuario = economia_obj.anos_posesion
            #if ingresos is not None and ahorro is not None and anos_posesion_usuario is not None:
            if ingresos is not None and ahorro is not None:
                t = 8 
                
                # --- ✅ INICIO DE LOGS DE DEP DEBUGGING ---
                logging.info("--------------------------------------------------")
                logging.info(" INSPECCIÓN DE CÁLCULO ECONÓMICO (MODO ASESORAMIENTO) ")
                logging.info(f"  - Inputs: Ingresos={ingresos}€, Ahorro={ahorro}€, Plazo (fijo)={t} años")

                ahorro_utilizable = ahorro * 0.75
                logging.info(f"  - Ahorro Utilizable (75%): {ahorro_utilizable:,.2f}€")

                gasto_potencial_total = ingresos * 0.095 * t
                logging.info(f"  - Gasto Potencial Total (a {t} años): {gasto_potencial_total:,.2f}€")
                
                capacidad_ahorro_mensual_coche = (ingresos * 0.095) / 12 
                logging.info(f"  - Capacidad Ahorro Mensual (Cuota Máx. teórica): {capacidad_ahorro_mensual_coche:,.2f}€/mes")

                # Condición para decidir "Contado"
                decision_contado = gasto_potencial_total <= ahorro_utilizable
                logging.info(f"  - Condición Contado: ¿{gasto_potencial_total:,.2f}€ <= {ahorro_utilizable:,.2f}€? -> {decision_contado}")
                logging.info("--------------------------------------------------")
                # --- FIN DE LOGS DE DEP DEBUGGING ---

                # Lógica de decisión
                if decision_contado:
                    modo_adq_rec = "Contado"
                    precio_max_rec = gasto_potencial_total
                    cuota_max_calc = None
                else:
                    modo_adq_rec = "Financiado"
                    precio_max_rec = None
                    cuota_max_calc = capacidad_ahorro_mensual_coche
                
                logging.info(f"✅ RECOMENDACIÓN FINAL: Modo={modo_adq_rec}, Precio Máx.={precio_max_rec}, Cuota Máx.={cuota_max_calc}")

                update_dict = {
                    "modo_adquisicion_recomendado": modo_adq_rec,
                    "precio_max_contado_recomendado": precio_max_rec,
                    "cuota_max_calculada": cuota_max_calc
                }
                filtros_actualizados = filtros_actualizados.model_copy(update=update_dict) 
            else:
                 logging.warning("WARN (CalcEconModo1) ► Faltan datos (ingresos, ahorro o años) para cálculo.")
        except Exception as e_calc:
            logging.error(f"ERROR (CalcEconModo1) ► Fallo durante el cálculo: {e_calc}", exc_info=True)
    else:
         logging.info("DEBUG (CalcEconModo1) ► Modo 'Usuario Define' o sin datos de economía, omitiendo cálculo.")

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
    flag_coche_ciudad_perfil = False
    flag_coche_ciudad_2_perfil = False
    flag_es_conductor_urbano = False
     
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
            "flag_ajuste_maletero_personal" : flag_ajuste_maletero_personal,
            "flag_coche_ciudad_perfil" :  flag_coche_ciudad_perfil,
            "flag_coche_ciudad_2_perfil" : flag_coche_ciudad_2_perfil,
            "flag_es_conductor_urbano": flag_es_conductor_urbano
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
     # --- LÓGICA PARA EL FLAG DE PENALIZACIÓN (EL "CUÁNDO") ---
    # Se activa si el usuario no suele llevar pasajeros o lo hace ocasionalmente.
    if getattr(info_pasajeros_obj, 'suele_llevar_acompanantes', True) is False:
        flag_penalizar_tamano_no_compacto = True
    elif getattr(info_pasajeros_obj, 'frecuencia_viaje_con_acompanantes', 'frecuente') == "ocasional":
        flag_penalizar_tamano_no_compacto = True
    if flag_penalizar_tamano_no_compacto:
        logging.info("Flags: Se activará la penalización por tamaño para coches grandes.")
    # --- LÓGICA PARA EL FLAG DE CONTEXTO (EL "CÓMO") ---
    # Se activa si el usuario se identifica como conductor urbano.
    if is_yes(getattr(preferencias_obj, 'circula_principalmente_ciudad', 'no')):
        flag_es_conductor_urbano = True
        logging.info(f"Flags: Perfil 'Conductor Urbano' detectado.")

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
    # Condición 1: El usuario valora un diseño exclusivo
    quiere_diseno_exclusivo = is_yes(getattr(preferencias_obj, 'prefiere_diseno_exclusivo', 'no'))
    # Condición 2: El uso con acompañantes es bajo o nulo
    uso_poco_acompaniado = False # Inicializamos como Falso por seguridad
    # Obtenemos los datos de pasajeros de forma segura
    suele_llevar_pasajeros = getattr(info_pasajeros_obj, 'suele_llevar_acompanantes', False)
    frecuencia_viajes = getattr(info_pasajeros_obj, 'frecuencia_viaje_con_acompanantes', None)
    num_otros_pasajeros = getattr(info_pasajeros_obj, 'num_otros_pasajeros', 0)
    # Evaluamos la condición de pasajeros de forma explícita
    if not suele_llevar_pasajeros:
        # Si nunca lleva pasajeros (equivale a frecuencia "nunca"), la condición se cumple.
        uso_poco_acompaniado = True
    elif frecuencia_viajes == "ocasional":
        # Si es ocasional, aplicamos la sub-condición del número de pasajeros.
        if num_otros_pasajeros <= 3:
            uso_poco_acompaniado = True
            logging.info(f"Flags: Frecuencia 'ocasional' con Z={num_otros_pasajeros} <= 3. Condición de pasajeros cumplida.")
        else:
            logging.info(f"Flags: Frecuencia 'ocasional' pero con Z={num_otros_pasajeros} > 3. Condición NO cumplida.")
    
    # Si ambas condiciones principales se cumplen, activamos el flag
    if quiere_diseno_exclusivo and uso_poco_acompaniado:
        flag_bonus_singularidad_lifestyle = True
        razon_pasajeros = "nunca" if not suele_llevar_pasajeros else "ocasional"
        logging.info(f"Flags: Perfil 'Singularidad Lifestyle' detectado (Diseño Exclusivo, Pasajeros: {razon_pasajeros}). Activando bonus.")
        
            
    # --- ✅ NUEVA LÓGICA PARA flag_deportividad_lifestyle ---
     # Condición 1: El estilo de conducción debe ser DEPORTIVO
    es_estilo_deportivo = getattr(preferencias_obj, 'estilo_conduccion', None) == EstiloConduccion.DEPORTIVO.value
    # Condición 2: El uso con acompañantes debe ser bajo o moderado
    uso_poco_acompaniado = False # Inicializamos como Falso por seguridad
    # Obtenemos los datos de pasajeros de forma segura
    suele_llevar_pasajeros = getattr(info_pasajeros_obj, 'suele_llevar_acompanantes', False)
    frecuencia_viajes = getattr(info_pasajeros_obj, 'frecuencia_viaje_con_acompanantes', None)
    num_otros_pasajeros = getattr(info_pasajeros_obj, 'num_otros_pasajeros', 0)
    # Evaluamos la condición de pasajeros de forma más explícita
    if not suele_llevar_pasajeros:
        # Si nunca lleva pasajeros (equivale a frecuencia "nunca"), la condición se cumple.
        uso_poco_acompaniado = True
    elif frecuencia_viajes == "ocasional":
        # Si es ocasional, aplicamos la sub-condición del número de pasajeros.
        if num_otros_pasajeros <= 3:
            uso_poco_acompaniado = True
            logging.info(f"Flags: Frecuencia 'ocasional' con Z={num_otros_pasajeros} <= 3. Condición de pasajeros cumplida.")
        else:
            logging.info(f"Flags: Frecuencia 'ocasional' pero con Z={num_otros_pasajeros} > 3. Condición NO cumplida.")
    # Si la frecuencia es 'frecuente', uso_poco_acompaniado se mantiene en False, que es el comportamiento correcto.

    # Si ambas condiciones principales se cumplen, activamos el flag
    if es_estilo_deportivo and uso_poco_acompaniado:
        flag_deportividad_lifestyle = True
        # Construimos un log más detallado para entender por qué se activó
        razon_pasajeros = "nunca" if not suele_llevar_pasajeros else f"ocasional con Z={num_otros_pasajeros}"
        logging.info(f"Flags: Perfil 'Deportividad Lifestyle' detectado (Estilo: Deportivo, Pasajeros: {razon_pasajeros}). Activando ajustes.")
    # --- FIN DE LA NUEVA LÓGICA ---
    
    if preferencias_obj:
        # Condición 1: El uso NO es profesional
        uso_no_profesional = not is_yes(preferencias_obj.uso_profesional) 
        # Condición 2: El usuario SÍ transporta carga voluminosa
        transporta_carga = is_yes(preferencias_obj.transporta_carga_voluminosa)
        # Si ambas condiciones se cumplen, activamos el flag
        if uso_no_profesional and transporta_carga:
            flag_ajuste_maletero_personal = True
            logging.info(f"Flags: Perfil 'Transportista Personal' detectado. Activando ajustes de maletero y carrocería.")
    
    # --- ✅ NUEVA LÓGICA PARA FLAG DE "COCHE DE CIUDAD" ---
    # Desglosamos las 6 condiciones para mayor claridad
    cond_1 = getattr(info_pasajeros_obj, 'suele_llevar_acompanantes', False) is True
    cond_2 = getattr(info_pasajeros_obj, 'frecuencia_viaje_con_acompanantes', None) in ["ocasional", "frecuente"]
    cond_3 = is_yes(getattr(preferencias_obj, 'circula_principalmente_ciudad', 'no'))
    cond_4 = not is_yes(getattr(preferencias_obj, 'transporta_carga_voluminosa', 'si'))
    distancia = getattr(preferencias_obj, 'distancia_trayecto', None)
    cond_5 = distancia in [DistanciaTrayecto.MENOS_10_KM.value, DistanciaTrayecto.ENTRE_10_Y_50_KM.value]
    cond_6 = not is_yes(getattr(preferencias_obj, 'realiza_viajes_largos', 'si'))

    # Si TODAS las condiciones se cumplen, activamos el flag
    if all([cond_1, cond_2, cond_3, cond_4, cond_5, cond_6]):
        flag_coche_ciudad_perfil = True
        logging.info(f"Flags: Perfil 'Coche de Ciudad' detectado. Activando bonus para coches compactos y ligeros.")
    # --- FIN NUEVA LÓGICA ---
    
    # --- ✅ NUEVA LÓGICA PARA FLAG DE "COCHE DE CIUDAD 2" ---
    # Desglosamos las 6 condiciones para mayor claridad

    # Condición 1: No lleva pasajeros o los lleva ocasionalmente
    cond_1 = (getattr(info_pasajeros_obj, 'suele_llevar_acompanantes', True) is False) or \
             (getattr(info_pasajeros_obj, 'frecuencia_viaje_con_acompanantes', None) == "ocasional")
    # Condición 2: Circula principalmente por ciudad
    cond_2 = is_yes(getattr(preferencias_obj, 'circula_principalmente_ciudad', 'no'))
    # Condición 3: No necesita un maletero amplio
    cond_3 = not is_yes(getattr(preferencias_obj, 'transporta_carga_voluminosa', 'si'))
    # Condición 4: Sus trayectos habituales son cortos
    distancia = getattr(preferencias_obj, 'distancia_trayecto', None)
    cond_4 = distancia in [DistanciaTrayecto.MENOS_10_KM.value, DistanciaTrayecto.ENTRE_10_Y_50_KM.value]
    # Condición 5: Sí realiza viajes largo
    cond_5 = is_yes(getattr(preferencias_obj, 'realiza_viajes_largos', 'no'))
    # Condición 6: Pero esos viajes largos son solo ocasionales
    frecuencia_vl = getattr(preferencias_obj, 'frecuencia_viajes_largos', None)
    cond_6 = frecuencia_vl == FrecuenciaViajesLargos.OCASIONALMENTE.value

    # Si TODAS las condiciones se cumplen, activamos el flag
    if all([cond_1, cond_2, cond_3, cond_4, cond_5, cond_6]):
        flag_coche_ciudad_2_perfil = True
        logging.info(f"Flags: Perfil 'Coche de Ciudad 2' detectado. Activando bonus para coches compactos y ligeros.")
    # --- FIN NUEVA LÓGICA ---

    
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
        "flag_coche_ciudad_perfil" :  flag_coche_ciudad_perfil,
        "flag_coche_ciudad_2_perfil": flag_coche_ciudad_2_perfil,
        "flag_es_conductor_urbano": flag_es_conductor_urbano,
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
    logging.info("--- Ejecutando Nodo: buscar_coches_finales_node ---") 
    k_coches =  7
    # Obtenemos el offset actual del estado, si no existe, empezamos en 0.
    offset = state.get("offset_busqueda", 0)
    historial = state.get("messages", [])
    tabla_resumen_criterios_md = state.get("tabla_resumen_criterios", "No se pudo generar el resumen de criterios.")
    #preferencias_obj = state.get("preferencias_usuario") # Objeto PerfilUsuario
    filtros_finales_obj = state.get("filtros_inferidos") 
    pesos_finales = state.get("pesos")
    economia_obj = state.get("economia")
    penalizar_puertas_flag = state.get("penalizar_puertas_bajas", False)
    flag_penalizar_lc_comod = state.get("flag_penalizar_low_cost_comodidad", False)
    flag_penalizar_dep_comod = state.get("flag_penalizar_deportividad_comodidad", False)
    flag_penalizar_antiguo_tec_val = state.get("flag_penalizar_antiguo_por_tecnologia", False)
    flag_aplicar_distintivo_val = state.get("aplicar_logica_distintivo_ambiental", False)
    flag_es_zbe_val = state.get("es_municipio_zbe", False)
    flag_desfav_car_no_aventura_val = state.get("desfavorecer_carroceria_no_aventura", False)
    flag_aplicar_logica_objetos_especiales= state.get("aplicar_logica_objetos_especiales")
    flag_pen_bev_reev_avent_ocas = state.get("penalizar_bev_reev_aventura_ocasional", False)
    flag_pen_phev_avent_ocas= state.get("penalizar_phev_aventura_ocasional", False)
    flag_pen_electrif_avent_extr = state.get("penalizar_electrificados_aventura_extrema", False)
    flag_fav_car_montana_val = state.get("favorecer_carroceria_montana", False)
    flag_fav_car_comercial_val = state.get("favorecer_carroceria_comercial", False)
    flag_fav_car_pasajeros_pro_val = state.get("favorecer_carroceria_pasajeros_pro", False)
    flag_fav_suv_aventura_ocasional = state.get("favorecer_suv_aventura_ocasional")
    flag_fav_pickup_todoterreno_aventura_extrema = state.get("favorecer_pickup_todoterreno_aventura_extrema")
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
    flag_coche_ciudad_perfil = state.get("flag_coche_ciudad_perfil")
    flag_coche_ciudad_2_perfil = state.get("flag_coche_ciudad_2_perfil")
    flag_es_conductor_urbano = state.get("flag_es_conductor_urbano")
    km_anuales_val = state.get("km_anuales_estimados")
    configurable_config = config.get("configurable", {})
    thread_id = configurable_config.get("thread_id", "unknown_thread_in_node") #

    logging.info(f"INFO (Buscar BQ) ► Ejecutando búsqueda para thread_id: {thread_id}")
    
    final_ai_msg = None
    coches_encontrados_raw = [] 
    coches_encontrados = []
    sql_ejecutada = None 
    params_ejecutados = None 
    
    #mensaje_coches = "No pude realizar la búsqueda de coches en este momento." # Default para la parte de coches
    # --- 2. BÚSQUEDA EN BIGQUERY ---
    if filtros_finales_obj and pesos_finales:
        try:
            # --- 2.1. PREPARACIÓN DE FILTROS PARA BQ ---
            filtros_para_bq = filtros_finales_obj.model_dump(mode='json', exclude_none=True)

            # Comprobamos si el usuario definió su propio presupuesto o si pidió asesoramiento.
            if economia_obj and economia_obj.presupuesto_definido is True:
                logging.info("DEBUG (Buscar BQ) ► Modo 'Usuario Define' detectado. Añadiendo presupuesto del usuario a los filtros BQ.")
                
                # Usamos los valores que el usuario introdujo, infiriendo el tipo por el campo presente.
                if economia_obj.pago_contado is not None:
                    # Si el usuario ha definido un pago al contado, usamos ese.
                    filtros_para_bq['pago_contado'] = economia_obj.pago_contado
                elif economia_obj.cuota_max is not None:
                    # Si el usuario ha definido una cuota máxima, usamos esa.
                    filtros_para_bq['cuota_max'] = economia_obj.cuota_max
            
            else:
                # Si el usuario eligió el modo "Asesoramiento" (presupuesto_definido is False),
                # usamos los valores que calculamos en el nodo anterior y que están guardados en los filtros.
                logging.info("DEBUG (Buscar BQ) ► Modo 'Asesoramiento' detectado. Añadiendo presupuesto calculado a los filtros BQ.")
                
                if filtros_finales_obj:
                    if filtros_finales_obj.modo_adquisicion_recomendado == 'Contado':
                        filtros_para_bq['pago_contado'] = filtros_finales_obj.precio_max_contado_recomendado
                    elif filtros_finales_obj.modo_adquisicion_recomendado == 'Financiado':
                        filtros_para_bq['cuota_max'] = filtros_finales_obj.cuota_max_calculada
            
            # Añadimos todos los flags al diccionario de filtros
            for flag_name in state.keys():
                if flag_name.startswith('flag_') or flag_name.startswith('penalizar_') or flag_name.startswith('favorecer_'):
                    filtros_para_bq[flag_name] = state.get(flag_name)
            
            filtros_para_bq['km_anuales_estimados'] = km_anuales_val
            filtros_para_bq['penalizar_puertas_bajas'] = penalizar_puertas_flag
            filtros_para_bq['aplicar_logica_distintivo_ambiental'] = flag_aplicar_distintivo_val
            filtros_para_bq['es_municipio_zbe'] = flag_es_zbe_val
            filtros_para_bq['desfavorecer_carroceria_no_aventura'] = flag_desfav_car_no_aventura_val
            filtros_para_bq['aplicar_logica_objetos_especiales'] = flag_aplicar_logica_objetos_especiales

            logging.debug(f"DEBUG (Buscar BQ) ► Filtros para BQ: {filtros_para_bq}") 
            logging.debug(f"DEBUG (Buscar BQ) ► Pesos para BQ: {pesos_finales}") 
            

            resultados_tupla = buscar_coches_bq(
                filtros=filtros_para_bq, 
                pesos=pesos_finales, 
                k=k_coches
            )
            logging.debug(f"DEBUG (Buscar BQ) ► Llamando a buscar_coches_bq con k={k_coches}")
            # Desempaquetamos el resultado de la búsqueda
            coches_encontrados_raw, sql_ejecutada, params_ejecutados = resultados_tupla
            
            # Sanitizamos los datos para evitar errores de JSON
            if coches_encontrados_raw:
                for coche_raw in coches_encontrados_raw:
                    coches_encontrados.append(sanitize_dict_for_json(coche_raw))
                logging.info(f"INFO (Buscar BQ) ► {len(coches_encontrados)} coches sanitizados y listos.")

        except Exception as e_bq:
            logging.error(f"ERROR (Buscar BQ) ► Falló la ejecución de buscar_coches_bq: {e_bq}", exc_info=True)
            final_ai_msg = AIMessage(content=f"Lo siento, tuve un problema al buscar en la base de datos: {e_bq}")
    else:
        logging.error("ERROR (Buscar BQ) ► Faltan filtros o pesos finales en el estado para la búsqueda.")
        final_ai_msg = AIMessage(content="Lo siento, falta información interna para realizar la búsqueda final.")
    
    # --- 3. CONSTRUCCIÓN DEL MENSAJE FINAL (LÓGICA CORREGIDA) ---
    if final_ai_msg is None: # Si no hubo un error previo en la búsqueda
        if coches_encontrados:
            # --- CASO A: Se encontraron coches ---
            try:
                structured_response = {
                    "type": "car_recommendation",
                    "introText": f"¡Listo! Basado en todo lo que hablamos, aquí tienes {len(coches_encontrados)} coche(s) que podrían interesarte:",
                    "cars": []
                }
                
                for i, coche in enumerate(coches_encontrados):
                    # Preparamos los datos de cada coche
                    nombre = coche.get('nombre', 'Coche Desconocido')
                    precio_str = "N/A"
                    if coche.get('precio_compra_contado') is not None:
                        try:
                            precio_str = f"{coche.get('precio_compra_contado'):,.0f}€".replace(",", ".")
                        except (ValueError, TypeError): pass

                    score_str = "N/A"
                    if coche.get('score_total') is not None:
                        try:
                            score_str = f"{coche.get('score_total'):.2f} pts"
                        except (ValueError, TypeError): pass

                    specs = [spec for spec in [coche.get('tipo_mecanica', ''), str(coche.get('ano_unidad', '')), coche.get('traccion', '')] if spec]

                    car_object = {
                        "name": f"{i+1}. {nombre}",
                        "specs": specs,
                        "imageUrl": coche.get('foto'),
                        "price": precio_str,
                        "score": score_str,
                        "analysis": "Análisis detallado de la recomendación pendiente de desarrollo."
                    }
                    structured_response["cars"].append(car_object)

                final_ai_msg = AIMessage(
                    content=structured_response["introText"],
                    additional_kwargs={"payload": structured_response}
                )
            except Exception as e:
                logging.error(f"ERROR (Buscar BQ) ► Fallo al construir la respuesta estructurada: {e}", exc_info=True)
                final_ai_msg = AIMessage(content="Lo siento, tuve un problema al formatear los resultados.")

        else:
            # --- CASO B: No se encontraron coches ---
            _sugerencia_generada = None
            # (Tu lógica de heurísticas para generar _sugerencia_generada se mantiene igual)
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
            # ✅ LÓGICA DE MENSAJE CORREGIDA
            mensaje_final_texto = _sugerencia_generada or "He aplicado todos tus filtros, pero no encontré coches que coincidan exactamente. ¿Quizás quieras redefinir algún criterio general?"
            final_ai_msg = AIMessage(content=mensaje_final_texto)    
                
    # --- 4. ACTUALIZACIÓN DEL HISTORIAL Y RETORNO ---
    historial_final = list(historial)
    if final_ai_msg:
        historial_final.append(final_ai_msg)     
        
    # --- 5. LOGGING A BIGQUERY (sin cambios) ---       
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
        "flag_coche_ciudad_perfil" : flag_coche_ciudad_perfil,
        "flag_coche_ciudad_2_perfil" : flag_coche_ciudad_2_perfil,
        "flag_es_conductor_urbano": flag_es_conductor_urbano,
        "flag_ajuste_maletero_personal": flag_ajuste_maletero_personal,
        "flag_bonus_nieve_val": flag_bonus_nieve_val,
        "flag_bonus_montana_val": flag_bonus_montana_val,
        "pregunta_pendiente": None # Este nodo es final para el turno
        
    }

 