
from langchain_core.messages import HumanMessage, BaseMessage,AIMessage
from pydantic import ValidationError # Importar para manejo de errores si es necesario
from .state import EstadoAnalisisPerfil, ResultadoSoloPerfil , ResultadoSoloFiltros,EconomiaUsuario, ResultadoEconomia,PerfilUsuario
from config.llm import llm_solo_perfil, llm_solo_filtros, llm_economia
from prompts.loader import system_prompt_perfil, system_prompt_filtros_template, prompt_economia_structured_sys_msg
from utils.postprocessing import aplicar_postprocesamiento_perfil, aplicar_postprocesamiento_filtros
from utils.validation import check_perfil_usuario_completeness , check_filtros_completos, check_economia_completa
from utils.formatters import formatear_preferencias_en_tabla
from utils.weights import compute_raw_weights, normalize_weights
from utils.rag_carroceria import get_recommended_carrocerias
from utils.bigquery_tools import buscar_coches_bq 


# En graph/nodes.py
# nodes.py (Empezando refactorización)


# --- Etapa 1: Recopilación de Preferencias del Usuario ---
def recopilar_preferencias_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Procesa la entrada del usuario, llama a llm_solo_perfil para extraer/actualizar
    preferencias_usuario y añade el mensaje de validación/confirmación.
    """
    print("--- Ejecutando Nodo: recopilar_preferencias_node ---")
    historial = state.get("messages", [])
    # Obtener el objeto PerfilUsuario actual del estado (puede ser None si es la primera vez)
    preferencias_actuales = state.get("preferencias_usuario") 

    # 1. Comprobar si el último mensaje es de la IA (para evitar procesar preguntas de la IA)
    if historial and isinstance(historial[-1], AIMessage):
        # Si el último mensaje es de la IA, este nodo no debe llamar al LLM.
        # Simplemente devolvemos el estado esperando la respuesta humana.
        print("DEBUG (Perfil) ► Último mensaje es AIMessage, omitiendo llamada a llm_solo_perfil.")
        return {**state} 

    print("DEBUG (Perfil) ► Último mensaje es HumanMessage o historial vacío, llamando a llm_solo_perfil...")
    
    # 2. Llamar al LLM enfocado en el perfil
    try:
        # Asegúrate que system_prompt_perfil esté definido y cargado correctamente.
        # Debe instruir al LLM para que rellene ResultadoSoloPerfil.
        response: ResultadoSoloPerfil = llm_solo_perfil.invoke(
            [system_prompt_perfil, *historial],
            config={"configurable": {"tags": ["llm_solo_perfil"]}} # Tag para LangSmith/debugging
        )
        print(f"DEBUG (Perfil) ► Respuesta llm_solo_perfil: {response}")

        # Extraer los datos parseados por Pydantic
        preferencias_nuevas = response.preferencias_usuario
        mensaje_validacion = response.mensaje_validacion

    except ValidationError as e_val:
        # Error si el LLM devuelve un JSON que no coincide con ResultadoSoloPerfil
        print(f"ERROR (Perfil) ► Error de Validación Pydantic en llm_solo_perfil: {e_val}")
        ai_msg = AIMessage(content=f"Hubo un problema al entender tus preferencias. ¿Podrías reformular? (Detalle: {e_val})")
        return {**state, "messages": historial + [ai_msg]}
    except Exception as e:
        # Otros errores (ej. API de OpenAI)
        print(f"ERROR (Perfil) ► Fallo al invocar llm_solo_perfil: {e}")
        ai_msg = AIMessage(content=f"Lo siento, tuve un problema técnico al procesar tus preferencias.")
        return {**state, "messages": historial + [ai_msg]}

    # 3. (Opcional) Aplicar post-procesamiento específico del perfil
    #    Si tienes reglas que refinan SÓLO PerfilUsuario, aplícalas aquí.
    try:
        # Ejemplo: preferencias_post = aplicar_postprocesamiento_perfil(preferencias_nuevas)
        #preferencias_post = preferencias_nuevas # Por ahora, usamos la salida directa del LLM
        preferencias_post = aplicar_postprocesamiento_perfil(preferencias_nuevas)

        print(f"DEBUG (Perfil) ► Preferencias tras post-procesamiento (si aplica): {preferencias_post}")
    except Exception as e_post:
        print(f"ERROR (Perfil) ► Fallo en postprocesamiento de perfil: {e_post}")
        preferencias_post = preferencias_nuevas # Fallback

    # 4. Actualizar el estado 'preferencias_usuario'   
    if preferencias_actuales:
         # Si ya existía un perfil, lo actualizamos
         update_data = preferencias_post.model_dump(exclude_unset=True) # Obtener solo campos presentes en la respuesta
         preferencias_actualizadas = preferencias_actuales.model_copy(update=update_data)
    else:
         # Si no existía, usamos el nuevo directamente
         preferencias_actualizadas = preferencias_post
    
    print(f"DEBUG (Perfil) ► Estado preferencias_usuario actualizado: {preferencias_actualizadas}")

    # 5. Añadir mensaje de validación/confirmación del LLM al historial
    #    Este mensaje puede ser una pregunta si falta algo, o una confirmación.
    #ai_msg = AIMessage(content=mensaje_validacion)
    pregunta_para_siguiente_nodo = None
    if mensaje_validacion and mensaje_validacion.strip():
        pregunta_para_siguiente_nodo = mensaje_validacion.strip()
        print(f"DEBUG (Perfil) ► Guardando pregunta pendiente: {pregunta_para_siguiente_nodo}")
    else:
        print(f"DEBUG (Perfil) ► No hay pregunta de validación pendiente.")
        
    # Devolver estado actualizado CON la pregunta pendiente
    return {
        **state,
        "preferencias_usuario": preferencias_actualizadas,
        # 'messages' NO se modifica aquí con la respuesta de la IA
        "pregunta_pendiente": pregunta_para_siguiente_nodo 
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

from typing import Literal, Optional
def _obtener_siguiente_pregunta_perfil(prefs: Optional[PerfilUsuario]) -> str:
    """Genera una pregunta específica basada en el primer campo obligatorio que falta."""
    if prefs is None: # Si no hay perfil, pedir algo básico
        return "¿Podrías contarme un poco sobre qué buscas o para qué usarás el coche?"

    # Revisa los campos en orden de prioridad deseado para preguntar
    if prefs.altura_mayor_190 is None: return "¿Mides más de 1.90 m?"
    if prefs.peso_mayor_100 is None: return "¿Pesas más de 100 kg?"
    if prefs.uso_profesional is None: return "¿Uso personal o profesional?"
    if prefs.valora_estetica is None: return "¿Valoras la estética de un coche o no es relevante para ti?"
    if prefs.solo_electricos is None: return "¿Quieres solo coches eléctricos?"
    if prefs.transmision_preferida is None: return "¿Qué tipo de transmisión prefieres?\n  1) Automático\n  2) Manual\n  3) Ambos"
    if prefs.apasionado_motor is None: return "¿Eres un apasionado del motor?"
    if prefs.aventura is None: return "Hablando de aventura, ¿con cuál de estas afirmaciones te identificas más?\n  1) No pisas nada que no sea asfalto (ninguna)\n  2) Salidas fuera de asfalto ocasionales (ocasional)\n  3) Circular en condiciones duras con total garantía (extrema)" # Usar template aventura
    
    # Si llegamos aquí, algo raro pasa (check_... debería haber dado True)
    return "¿Podrías darme algún detalle más sobre tus preferencias?"


# --- NUEVO NODO PARA PREGUNTAR (ETAPA 1) ---
def preguntar_preferencias_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Añade la pregunta de seguimiento correcta al historial.
    Verifica si el perfil está realmente completo antes de añadir un mensaje 
    de confirmación/transición. Si no lo está, asegura que se añada una pregunta real.
    """
    print("--- Ejecutando Nodo: preguntar_preferencias_node ---")
    pregunta_guardada = state.get("pregunta_pendiente")
    preferencias = state.get("preferencias_usuario")
    historial_actual = state.get("messages", [])
    
    mensaje_a_enviar = None # El mensaje que finalmente añadiremos

    # 1. Comprobar si el perfil está REALMENTE completo AHORA
    perfil_esta_completo = check_perfil_usuario_completeness(preferencias)

    if not perfil_esta_completo:
        print("DEBUG (Preguntar Perfil) ► Perfil aún INCOMPLETO según checker.")
        # El perfil NO está completo, DEBEMOS hacer una pregunta.
        # ¿Tenemos una pregunta guardada?
        if pregunta_guardada and pregunta_guardada.strip():
            # ¿La pregunta guardada PARECE una confirmación por error?
            # (Podemos usar heurísticas simples como startswith)
            if pregunta_guardada.startswith("¡Perfecto!") or \
               pregunta_guardada.startswith("¡Genial!") or \
               pregunta_guardada.startswith("Ok, he definido") or \
               "¿Pasamos a" in pregunta_guardada:
                print(f"WARN (Preguntar Perfil) ► Pregunta guardada ('{pregunta_guardada}') parece confirmación, pero perfil incompleto. IGNORANDO y generando pregunta específica.")
                # Ignoramos la pregunta guardada y generamos una nueva basada en lo que falta
                mensaje_a_enviar = _obtener_siguiente_pregunta_perfil(preferencias)
            else:
                # La pregunta guardada parece una pregunta real, la usamos.
                 print(f"DEBUG (Preguntar Perfil) ► Usando pregunta guardada: {pregunta_guardada}")
                 mensaje_a_enviar = pregunta_guardada
        else:
            # No había pregunta guardada, generamos una nueva.
            print("DEBUG (Preguntar Perfil) ► No había pregunta guardada, generando pregunta específica.")
            mensaje_a_enviar = _obtener_siguiente_pregunta_perfil(preferencias)
            
    else: # El perfil SÍ está completo
        print("DEBUG (Preguntar Perfil) ► Perfil COMPLETO según checker.")
        # Usamos el mensaje guardado (que debería ser de confirmación/transición)
        if pregunta_guardada and pregunta_guardada.strip():
             print(f"DEBUG (Preguntar Perfil) ► Usando mensaje de confirmación guardado: {pregunta_guardada}")
             mensaje_a_enviar = pregunta_guardada
        else:
             # Si por alguna razón no había mensaje, ponemos uno por defecto
             print("WARN (Preguntar Perfil) ► Perfil completo pero no había mensaje pendiente. Usando confirmación genérica.")
             mensaje_a_enviar = "¡Entendido! Ya tenemos tu perfil. ¿Continuamos?"

    # Añadir el mensaje decidido al historial (evitando duplicados)
    historial_nuevo = historial_actual
    if mensaje_a_enviar and mensaje_a_enviar.strip():
        ai_msg = AIMessage(content=mensaje_a_enviar)
        if not historial_actual or historial_actual[-1].content != ai_msg.content:
            historial_nuevo = historial_actual + [ai_msg]
            print(f"DEBUG (Preguntar Perfil) ► Mensaje final añadido: {mensaje_a_enviar}")
        else:
             print("DEBUG (Preguntar Perfil) ► Mensaje final duplicado, no se añade.")
    else:
         print("WARN (Preguntar Perfil) ► No se determinó ningún mensaje a enviar.")


    # Devolver estado: historial actualizado y pregunta_pendiente reseteada
    return {
        **state,
        "messages": historial_nuevo,
        "pregunta_pendiente": None # Siempre limpiar la pregunta pendiente
    }

# --- Fin Etapa 1 ---

# --- Etapa 2: Inferencia y Validación de Filtros Técnicos ---
def preguntar_filtros_node(state: EstadoAnalisisPerfil) -> dict:
     """Toma la pregunta de filtros pendiente y la añade al historial."""
     print("--- Ejecutando Nodo: preguntar_filtros_node ---")
     pregunta = state.get("pregunta_pendiente")
     historial_actual = state.get("messages", [])
     historial_nuevo = historial_actual 
     mensaje_a_enviar = None
     if pregunta and pregunta.strip():
         mensaje_a_enviar = pregunta
         # Podrías añadir lógica fallback si la pregunta está vacía
     else:
         mensaje_a_enviar = "¿Podrías darme más detalles sobre los filtros técnicos?" # Fallback muy genérico

     # Añadir mensaje
     if mensaje_a_enviar:
         ai_msg = AIMessage(content=mensaje_a_enviar)
         if not historial_actual or historial_actual[-1].content != ai_msg.content:
             historial_nuevo = historial_actual + [ai_msg]
             print(f"DEBUG (Preguntar Filtros) ► Mensaje final añadido: {mensaje_a_enviar}")
         else:
              print("DEBUG (Preguntar Filtros) ► Mensaje final duplicado.")

     return {**state, "messages": historial_nuevo, "pregunta_pendiente": None}
 
def inferir_filtros_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Infiere filtros técnicos, aplica post-procesamiento, actualiza el estado 
    'filtros_inferidos' y guarda la pregunta/confirmación en 'pregunta_pendiente'.
    """
    print("--- Ejecutando Nodo: inferir_filtros_node ---")
    historial = state.get("messages", []) # Necesitamos el historial para el LLM
    preferencias = state.get("preferencias_usuario") 
    filtros_actuales = state.get("filtros_inferidos") 

    if not preferencias: 
        print("ERROR (Filtros) ► Nodo 'inferir_filtros_node' sin preferencias.")
        return {**state} 

    print("DEBUG (Filtros) ► Preferencias de usuario disponibles. Procediendo...")

    # Inicializar variables por si falla el try
    filtros_post = filtros_actuales 
    mensaje_validacion = None

    # 2. Preparar prompt (como lo tenías)
    try:
        preferencias_dict = preferencias.model_dump(mode='json')
        prompt_filtros = system_prompt_filtros_template.format(
            preferencias_contexto=str(preferencias_dict) 
        )
        print(f"DEBUG (Filtros) ► Prompt para llm_solo_filtros (parcial): {prompt_filtros[:500]}...") 
    except Exception as e_prompt:
        # ... (manejo de error de prompt como lo tenías) ...
        # Guardar el error como pregunta pendiente podría ser una opción
        mensaje_validacion = f"Error interno preparando la consulta de filtros: {e_prompt}"
        # Salimos temprano si falla el prompt
        return {**state, "filtros_inferidos": filtros_actuales, "pregunta_pendiente": mensaje_validacion}

    # 3. Llamar al LLM (como lo tenías)
    try:
        response: ResultadoSoloFiltros = llm_solo_filtros.invoke(
            [prompt_filtros, *historial], 
            config={"configurable": {"tags": ["llm_solo_filtros"]}}
        )
        print(f"DEBUG (Filtros) ► Respuesta llm_solo_filtros: {response}")
        filtros_nuevos = response.filtros_inferidos
        mensaje_validacion = response.mensaje_validacion # Guardar para usarlo después

        # 4. Aplicar post-procesamiento (como lo tenías)
        try:
            # Pasar filtros_nuevos (del LLM) y preferencias (del estado)
            resultado_post_proc = aplicar_postprocesamiento_filtros(filtros_nuevos, preferencias)
            if resultado_post_proc is not None:
                filtros_post = resultado_post_proc
            else:
                 print("WARN (Filtros) ► aplicar_postprocesamiento_filtros devolvió None.")
                 filtros_post = filtros_nuevos # Fallback
            print(f"DEBUG (Filtros) ► Filtros TRAS post-procesamiento: {filtros_post}")
        except Exception as e_post:
            print(f"ERROR (Filtros) ► Fallo en postprocesamiento de filtros: {e_post}")
            filtros_post = filtros_nuevos # Fallback

    # Manejar errores de la llamada LLM y post-procesamiento
    except ValidationError as e_val:
        print(f"ERROR (Filtros) ► Error de Validación Pydantic en llm_solo_filtros: {e_val}")
        mensaje_validacion = f"Hubo un problema al procesar los filtros técnicos. (Detalle: {e_val})"
        filtros_post = filtros_actuales # Mantener filtros anteriores si falla validación LLM
    except Exception as e:
        print(f"ERROR (Filtros) ► Fallo al invocar llm_solo_filtros: {e}")
        mensaje_validacion = "Lo siento, tuve un problema técnico al determinar los filtros."
        filtros_post = filtros_actuales # Mantener filtros anteriores

    # 5. Actualizar el estado 'filtros_inferidos' (como lo tenías)
    if filtros_actuales:
         # Usar el resultado del post-procesamiento (o el fallback)
         update_data = filtros_post.model_dump(exclude_unset=True)
         filtros_actualizados = filtros_actuales.model_copy(update=update_data)
    else:
         filtros_actualizados = filtros_post     
    print(f"DEBUG (Filtros) ► Estado filtros_inferidos actualizado: {filtros_actualizados}")

    # --- CAMBIOS AQUÍ ---
    # 6. Definir 'pregunta_para_siguiente_nodo' basado en 'mensaje_validacion'
    pregunta_para_siguiente_nodo = None
    if mensaje_validacion and mensaje_validacion.strip():
        pregunta_para_siguiente_nodo = mensaje_validacion.strip()
        print(f"DEBUG (Filtros) ► Guardando pregunta pendiente: {pregunta_para_siguiente_nodo}")
    else:
        print(f"DEBUG (Filtros) ► No hay pregunta de validación pendiente.")
        
    # 7. Devolver estado actualizado: SIN modificar 'messages', CON 'pregunta_pendiente'
    return {
        **state,
        "filtros_inferidos": filtros_actualizados,
        # "messages": historial_con_nuevo_mensaje, # <-- ELIMINADO / COMENTADO
        "pregunta_pendiente": pregunta_para_siguiente_nodo # <-- AÑADIDO y definido correctamente
    }


def validar_filtros_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Comprueba si los FiltrosInferidos en el estado están completos 
    (según los criterios definidos en la función de utilidad `check_filtros_completos`).
    """
    print("--- Ejecutando Nodo: validar_filtros_node ---")
    filtros = state.get("filtros_inferidos")
    
    # Usar una función de utilidad para verificar la completitud SOLO de los filtros
    # ¡Asegúrate de que esta función exista en utils.validation!
    if check_filtros_completos(filtros):
        print("DEBUG (Filtros) ► Validación: FiltrosInferidos considerados COMPLETOS.")
    else:
        print("DEBUG (Filtros) ► Validación: FiltrosInferidos considerados INCOMPLETOS.")
        
    # Este nodo solo valida. No modifica el estado. 
    # La condición del grafo que siga a este nodo decidirá si volver a inferir/preguntar
    # o si avanzar a la etapa de economía.
    return {**state}





# --- Etapa 3: Inferencia y Validación de Recopilación de Economía ---


# --- NUEVO NODO PARA PREGUNTAR (ETAPA 3) ---
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




# nodes.py (Continuación... añadiendo Etapa 4)

# --- Importaciones Adicionales Necesarias ---
# Asegúrate de importar estas funciones de tus utilidades
from utils.rag_carroceria import get_recommended_carrocerias
from utils.weights import compute_raw_weights, normalize_weights
from utils.formatters import formatear_preferencias_en_tabla
# También los modelos/enums si los necesitas directamente
from graph.perfil.state import EstadoAnalisisPerfil, PerfilUsuario, FiltrosInferidos, EconomiaUsuario
from utils.enums import NivelAventura # Ejemplo, si necesitas el Enum


import traceback 
# --- Etapa 4: Finalización y Presentación ---

# Tu código para finalizar_y_presentar_node

def finalizar_y_presentar_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Realiza los cálculos finales (RAG carrocerías, pesos) y formatea 
    la tabla resumen final una vez toda la información está completa.
    """
    print("--- Ejecutando Nodo: finalizar_y_presentar_node ---")
    historial = state.get("messages", [])
    preferencias = state.get("preferencias_usuario")
    filtros = state.get("filtros_inferidos")
    economia = state.get("economia")
    pesos_calculados = None 

    # Verificar pre-condiciones
    if not preferencias or not filtros or not economia:
         print("ERROR (Finalizar) ► Faltan datos esenciales...")
         ai_msg = AIMessage(content="Lo siento, parece que falta información...")
         return {**state, "messages": historial + [ai_msg]}
         
    # Convertir a dict para acceso/paso a funciones (si es necesario)
    prefs_dict = preferencias.model_dump(mode='json')
    # filtros_dict = filtros.model_dump(mode='json') # OJO: Usaremos filtros_actualizados más adelante
    econ_dict = economia.model_dump(mode='json')
    
    # --- INICIO NUEVA LÓGICA MODO 1 ---
    # Crear la copia aquí, ANTES del if/else, para que siempre exista
    filtros_actualizados = filtros.model_copy(deep=True) # <--- Inicialización Clave
    
    print("DEBUG (Finalizar) ► Verificando si aplica lógica Modo 1...")
    if economia.modo == 1:
        print("DEBUG (Finalizar) ► Modo 1 detectado. Calculando recomendación...")
        try:
            ingresos = economia.ingresos
            ahorro = economia.ahorro
            anos_posesion = economia.anos_posesion
            
            if ingresos is not None and ahorro is not None and anos_posesion is not None:
                 # ... (Cálculos de t, umbrales, modo_adq_rec, etc.) ...
                 t = min(anos_posesion, 8)
                 ahorro_utilizable = ahorro * 0.75
                 potencial_ahorro_plazo = ingresos * 0.1 * t
                 # ... (if/else para modo_adq_rec, precio_max_rec, cuota_max_calc) ...
                 if potencial_ahorro_plazo <= ahorro_utilizable:
                     modo_adq_rec, precio_max_rec, cuota_max_calc = "Contado", potencial_ahorro_plazo, None
                 else:
                     modo_adq_rec, precio_max_rec, cuota_max_calc = "Financiado", None, (ingresos * 0.1) / 12
                     
                 update_dict = {
                     "modo_adquisicion_recomendado": modo_adq_rec,
                     "precio_max_contado_recomendado": precio_max_rec,
                     "cuota_max_calculada": cuota_max_calc
                 }
                 # Actualizar la COPIA que creamos antes
                 filtros_actualizados = filtros_actualizados.model_copy(update=update_dict) 
                 print(f"DEBUG (Finalizar) ► Filtros actualizados con recomendación Modo 1: {filtros_actualizados}")
            else:
                 print("WARN (Finalizar) ► Faltan datos para cálculo Modo 1...")
        except Exception as e_calc:
            print(f"ERROR (Finalizar) ► Fallo durante cálculo de recomendación Modo 1: {e_calc}")
            # En caso de error, filtros_actualizados mantiene la copia inicial sin los cálculos de Modo 1
            
    else:
         print("DEBUG (Finalizar) ► Modo no es 1, omitiendo cálculo de recomendación.")
    # --- FIN NUEVA LÓGICA MODO 1 ---
    
    # Convertir a dict los filtros actualizados si RAG los necesita así
    filtros_dict_actualizado = filtros_actualizados.model_dump(mode='json')

    # 1. Llamada RAG (usando filtros_actualizados o su dict)
    # if not filtros_actualizados.tipo_carroceria: 
    #     print("DEBUG (Finalizar) ► Llamando a RAG...")
    try:
            # Pasar prefs_dict y el dict de filtros actualizado
            tipos_carroceria_rec = get_recommended_carrocerias(prefs_dict, filtros_dict_actualizado, k=3) 
            print(f"DEBUG (Finalizar) ► RAG recomendó: {tipos_carroceria_rec}")
            # Actualizar el objeto filtros_actualizados
            filtros_actualizados.tipo_carroceria = tipos_carroceria_rec 
    except Exception as e_rag:
            # ... (manejo error RAG) ...
            filtros_actualizados.tipo_carroceria = ["Error RAG"] 
    # ...

    # 2. Cálculo de Pesos (usando filtros_actualizados y preferencias)
    print("DEBUG (Finalizar) ► Calculando pesos...")
    pesos_calculados = None 
    try:
        # Extraer valores de filtros_actualizados y preferencias
        estetica_val = filtros_actualizados.estetica_min if filtros_actualizados.estetica_min is not None else 1.0
        # ... (obtener premium_val, singular_val) ...
        premium_val = filtros_actualizados.premium_min if filtros_actualizados.premium_min is not None else 1.0
        singular_val = filtros_actualizados.singular_min if filtros_actualizados.singular_min is not None else 1.0
        aventura_val = preferencias.aventura 
        raw = compute_raw_weights(
            preferencias=preferencias, # <--- Pasar preferencias
            estetica=estetica_val,
            premium=premium_val,
            singular=singular_val
            # aventura_level ya no se pasa, se obtiene de preferencias dentro de la función
        )
        pesos_calculados = normalize_weights(raw)
        print(f"DEBUG (Finalizar) ► Pesos calculados: {pesos_calculados}") 
    except Exception as e_weights:
        print(f"ERROR (Finalizar) ► Fallo calculando pesos: {e_weights}")
        # --- AÑADIR ESTO PARA VER EL ERROR COMPLETO ---
        print("--- TRACEBACK ERROR PESOS ---")
        traceback.print_exc()
        print("-----------------------------")

    # 3. Formateo de la Tabla (usando filtros_actualizados)
    print("DEBUG (Finalizar) ► Formateando tabla final...")
    tabla_final_md = "Error al generar el resumen." 
    try:
        # Pasar los objetos Pydantic (la función formateadora maneja la conversión a dict si es necesario)
        tabla_final_md = formatear_preferencias_en_tabla(
            preferencias=preferencias, 
            filtros=filtros_actualizados, # <-- Pasar el objeto actualizado
            economia=economia
        )
    except Exception as e_format:
        # ... (manejo error formato) ...
        pass

    # 4. Crear y añadir mensaje final (como antes)
    final_ai_msg = AIMessage(content=tabla_final_md)
    # ... (lógica para añadir a historial_final) ...
    if historial and historial[-1].content == final_ai_msg.content:
        historial_final = historial
    else:
        historial_final = historial + [final_ai_msg]


    # 5. Devolver el estado final completo
    return {
    **state,
    "filtros_inferidos": filtros_actualizados, 
    "pesos": pesos_calculados, 
    "messages": historial_final,
    "coches_recomendados": None # Inicializar/resetear por si acaso
}

# --- Fin Etapa 4 ---


# --- NUEVO NODO BÚSQUEDA FINAL ---
def buscar_coches_finales_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Usa los filtros y pesos finales del estado para buscar coches en BQ
    y presenta los resultados.
    """
    print("--- Ejecutando Nodo: buscar_coches_finales_node ---")
    historial = state.get("messages", [])
    filtros_finales = state.get("filtros_inferidos")
    pesos_finales = state.get("pesos")
    economia = state.get("economia") # Necesario para construir dict de filtros BQ

    coches_encontrados = [] # Valor por defecto
    mensaje_final = "No pude realizar la búsqueda en este momento." # Msg error default

    if filtros_finales and pesos_finales:
        # Preparar el diccionario de filtros para la función BQ
        # (Incluyendo campos económicos relevantes si modo es 2)
        filtros_para_bq = {}
        filtros_para_bq.update(filtros_finales.model_dump(mode='json', exclude_none=True))
        if economia and economia.modo == 2:
            filtros_para_bq['modo'] = 2
            filtros_para_bq['submodo'] = economia.submodo
            if economia.submodo == 1:
                 filtros_para_bq['pago_contado'] = economia.pago_contado
            elif economia.submodo == 2:
                 filtros_para_bq['cuota_max'] = economia.cuota_max

        # DEFINIR cuántos resultados pedir (ej: 5 o 7)
        k_coches = 5 

        print(f"DEBUG (Buscar BQ) ► Llamando a buscar_coches_bq con k={k_coches}")
        try:
            coches_encontrados = buscar_coches_bq(
                filtros=filtros_para_bq, 
                pesos=pesos_finales, 
                k=k_coches
            )

            # Formatear la respuesta para el usuario
            if coches_encontrados:
                mensaje_final = f"¡Listo! Basado en todo lo que hablamos, aquí tienes {len(coches_encontrados)} coche(s) que podrían interesarte:\n\n"
                # Formato simple: Nombre (Marca) - Precio - Score
                for i, coche in enumerate(coches_encontrados):
                    nombre = coche.get('nombre', 'Nombre Desconocido')
                    marca = coche.get('marca', '')
                    precio = coche.get('precio_compra_contado')
                    score = coche.get('score_total', 0.0)
                    precio_str = f"{precio:,.0f}€".replace(",",".") if isinstance(precio, (int, float)) else "Precio N/A"
                    mensaje_final += f"{i+1}. **{nombre}** ({marca}) - {precio_str} (Score: {score:.2f})\n"
                mensaje_final += "\n¿Qué te parecen estas opciones?"
            else:
                mensaje_final = "He aplicado todos tus filtros, pero no encontré coches que coincidan exactamente en este momento. ¿Quizás quieras ajustar algún criterio?"

        except Exception as e_bq:
            print(f"ERROR (Buscar BQ) ► Falló la ejecución de buscar_coches_bq: {e_bq}")
            mensaje_final = f"Lo siento, tuve un problema al buscar en la base de datos de coches: {e_bq}"
    else:
        print("ERROR (Buscar BQ) ► Faltan filtros o pesos finales en el estado.")
        mensaje_final = "Lo siento, falta información interna para realizar la búsqueda final."

    # Crear y añadir el mensaje con los resultados o el error
    final_ai_msg = AIMessage(content=mensaje_final)
    # Evitar duplicados
    if historial and historial[-1].content == final_ai_msg.content:
        historial_final = historial
    else:
        historial_final = historial + [final_ai_msg]

    # Devolver estado final con coches y mensaje
    return {
        **state,
        "coches_recomendados": coches_encontrados, 
        "messages": historial_final
    }