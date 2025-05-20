
from langchain_core.messages import HumanMessage, BaseMessage,AIMessage
from pydantic import ValidationError # Importar para manejo de errores si es necesario
from .state import (EstadoAnalisisPerfil, 
                    PerfilUsuario, ResultadoSoloPerfil , 
                    FiltrosInferidos, ResultadoSoloFiltros,
                    EconomiaUsuario,ResultadoEconomia ,
                    InfoPasajeros, ResultadoPasajeros)
from config.llm import llm_solo_perfil, llm_solo_filtros, llm_economia, llm_pasajeros
from prompts.loader import system_prompt_perfil, system_prompt_filtros_template, prompt_economia_structured_sys_msg, system_prompt_pasajeros
from utils.postprocessing import aplicar_postprocesamiento_perfil, aplicar_postprocesamiento_filtros
from utils.validation import check_perfil_usuario_completeness , check_filtros_completos, check_economia_completa, check_pasajeros_completo
from utils.formatters import formatear_preferencias_en_tabla
from utils.weights import compute_raw_weights, normalize_weights
from utils.rag_carroceria import get_recommended_carrocerias
from utils.bigquery_tools import buscar_coches_bq
from utils.conversion import is_yes 
from utils.bq_logger import log_busqueda_a_bigquery 
import traceback 
import pandas as pd

# En graph/nodes.py
# --- Etapa 1: Recopilación de Preferencias del Usuario ---

def recopilar_preferencias_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Procesa entrada humana, llama a llm_solo_perfil, actualiza preferencias_usuario,
    y guarda el contenido del mensaje devuelto en 'pregunta_pendiente'.
    """
    print("--- Ejecutando Nodo: recopilar_preferencias_node ---")
    historial = state.get("messages", [])
    preferencias_actuales = state.get("preferencias_usuario") 

    # 1. Comprobar si el último mensaje es de la IA
    if historial and isinstance(historial[-1], AIMessage):
        print("DEBUG (Perfil) ► Último mensaje es AIMessage, omitiendo llamada a llm_solo_perfil.")
        return {**state, "pregunta_pendiente": None} # Limpiar pregunta pendiente

    print("DEBUG (Perfil) ► Último mensaje es HumanMessage o historial vacío, llamando a llm_solo_perfil...")
    
    # Inicializar variables que se usarán después del try/except
    preferencias_post = preferencias_actuales # Usar el actual como fallback inicial
    contenido_msg_llm = None # Mensaje a guardar para el siguiente nodo
    
    # 2. Llamar al LLM enfocado en el perfil
    try:
        # LLM ahora devuelve ResultadoSoloPerfil (con tipo_mensaje y contenido_mensaje)
        response: ResultadoSoloPerfil = llm_solo_perfil.invoke(
            [system_prompt_perfil, *historial],
            config={"configurable": {"tags": ["llm_solo_perfil"]}} 
        )
        print(f"DEBUG (Perfil) ► Respuesta llm_solo_perfil: {response}")

        # --- CAMBIO: Extraer de la nueva estructura ---
        preferencias_nuevas = response.preferencias_usuario 
        tipo_msg_llm = response.tipo_mensaje # Puedes usarlo para logging o lógica futura si quieres
        contenido_msg_llm = response.contenido_mensaje # Este es el texto que guardaremos

        # 3. Aplicar post-procesamiento
        try:
            resultado_post_proc = aplicar_postprocesamiento_perfil(preferencias_nuevas)
            if resultado_post_proc is not None:
                preferencias_post = resultado_post_proc
            else:
                 print("WARN (Perfil) ► aplicar_postprocesamiento_perfil devolvió None.")
                 preferencias_post = preferencias_nuevas # Fallback
            print(f"DEBUG (Perfil) ► Preferencias TRAS post-procesamiento: {preferencias_post}")
        except Exception as e_post:
            print(f"ERROR (Perfil) ► Fallo en postprocesamiento de perfil: {e_post}")
            preferencias_post = preferencias_nuevas # Fallback

    # Manejo de errores de la llamada LLM
    except ValidationError as e_val:
        print(f"ERROR (Perfil) ► Error de Validación Pydantic en llm_solo_perfil: {e_val}")
        contenido_msg_llm = f"Hubo un problema al entender tus preferencias (formato inválido). ¿Podrías reformular? Detalle: {e_val}"
        # Mantener preferencias anteriores si falla validación
        preferencias_post = preferencias_actuales 
    except Exception as e:
        print(f"ERROR (Perfil) ► Fallo general al invocar llm_solo_perfil: {e}")
        print("--- TRACEBACK FALLO LLM PERFIL ---")
        traceback.print_exc() # Imprimir traceback para depurar
        print("--------------------------------")
        contenido_msg_llm = "Lo siento, tuve un problema técnico al procesar tus preferencias."
        # Mantener preferencias anteriores
        preferencias_post = preferencias_actuales 

    # 4. Actualizar el estado 'preferencias_usuario' (fusionando)
    preferencias_actualizadas = preferencias_post # Usar resultado post-proc o el fallback
    if preferencias_actuales and preferencias_post: 
        try:
            if hasattr(preferencias_post, "model_dump"):
                # Usar exclude_none=True para evitar que Nones del LLM borren datos existentes
                update_data = preferencias_post.model_dump(exclude_unset=True, exclude_none=True) 
                if update_data: # Solo actualizar si hay algo que actualizar
                     preferencias_actualizadas = preferencias_actuales.model_copy(update=update_data)
                else: # Si post-proc no devolvió nada útil, mantener el actual
                     preferencias_actualizadas = preferencias_actuales
            else:
                 preferencias_actualizadas = preferencias_post 
        except Exception as e_merge:
             print(f"ERROR (Perfil) ► Fallo al fusionar preferencias: {e_merge}")
             preferencias_actualizadas = preferencias_actuales 

    print(f"DEBUG (Perfil) ► Estado preferencias_usuario actualizado: {preferencias_actualizadas}")
    
    # 5. Guardar la pregunta/confirmación pendiente para el siguiente nodo
    pregunta_para_siguiente_nodo = None
    if contenido_msg_llm and contenido_msg_llm.strip():
        pregunta_para_siguiente_nodo = contenido_msg_llm.strip()
        print(f"DEBUG (Perfil) ► Guardando mensaje pendiente: {pregunta_para_siguiente_nodo}")
    else:
        print(f"DEBUG (Perfil) ► No hay mensaje pendiente.")
        
    # 6. Devolver estado actualizado (SIN modificar messages, CON pregunta_pendiente)
    return {
        **state,
        "preferencias_usuario": preferencias_actualizadas,
        # "messages": historial_con_nuevo_mensaje, # <-- NO se actualiza aquí
        "pregunta_pendiente": pregunta_para_siguiente_nodo # <-- Se guarda el CONTENIDO del mensaje
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
    if prefs is None: 
        return "¿Podrías contarme un poco sobre qué buscas o para qué usarás el coche?"
    # Revisa los campos en orden de prioridad deseado para preguntar
    if prefs.apasionado_motor is None: return "¿Te consideras una persona entusiasta del mundo del motor y la tecnología automotriz?"
    if prefs.valora_estetica is None: return "¿La Estética es importante para ti o crees que hay factores más importantes?"
    if prefs.coche_principal_hogar is None: return "¿El coche que estamos buscando será el vehículo principal de tu hogar?."
    if prefs.uso_profesional is None: return "¿El coche lo destinaras principalmente para uso personal o más para fines profesionales (trabajo)?"
    if is_yes(prefs.uso_profesional) and prefs.tipo_uso_profesional is None:
        return "¿Y ese uso profesional será principalmente para llevar pasajeros, transportar carga, o un uso mixto?"
    if prefs.prefiere_diseno_exclusivo is None: return "En cuanto al estilo del coche, ¿te inclinas más por un diseño exclusivo y llamativo, o por algo más discreto y convencional?"
    if prefs.altura_mayor_190 is None: return "Para recomendarte un vehículo con espacio adecuado, ¿tu altura supera los 1.90 metros?"
    if prefs.peso_mayor_100 is None: return "Para garantizar tu máxima comodidad, ¿tienes un peso superior a 100 kg?"
    if prefs.aventura is None: return "Para conocer tu espíritu aventurero, dime que prefieres:\n 🛣️ Solo asfalto (ninguna)\n 🌲 Salidas off‑road de vez en cuando (ocasional)\n 🏔️ Aventurero extremo en terrenos difíciles (extrema)"
    if prefs.transporta_carga_voluminosa is None:
        return "¿Transportas con frecuencia equipaje o carga voluminosa? (Responde 'sí' o 'no')"
    if is_yes(prefs.transporta_carga_voluminosa) and prefs.necesita_espacio_objetos_especiales is None:
        return "¿Y ese transporte de carga incluye objetos de dimensiones especiales como bicicletas, tablas de surf, cochecitos para bebé, sillas de ruedas, instrumentos musicales, etc?"
    # --- FIN NUEVAS PREGUNTAS DE CARGA ---
    if prefs.solo_electricos is None: return "¿Estás interesado exclusivamente en vehículos con motorización eléctrica?"
    if prefs.transmision_preferida is None: return "En cuanto a la transmisión, ¿qué opción se ajusta mejor a tus preferencias?\n 1) Automático\n 2) Manual\n 3) Ambos, puedo considerar ambas opciones"
     # --- NUEVAS PREGUNTAS DE RATING (0-10) ---
    if prefs.rating_fiabilidad_durabilidad is None: return "En una escala de 0 (nada importante) a 10 (extremadamente importante), ¿qué tan importante es para ti la Fiabilidad y Durabilidad del coche?"
    if prefs.rating_seguridad is None:return "Pensando en la Seguridad, ¿qué puntuación le darías en importancia (0-10)?"
    if prefs.rating_comodidad is None:return "Y en cuanto a la comodidad y confort del vehiculo que tan importante es que se maximice? (0-10)"
    if prefs.rating_impacto_ambiental is None: return "Considerando el Bajo Impacto Medioambiental, ¿qué importancia tiene esto para tu elección (0-10)?"
    #if prefs.rating_costes_uso is None: return "Respecto a los Costes de Uso y Mantenimiento Reducidos, ¿cómo lo puntuarías en importancia (0-10)?"
    if prefs.rating_tecnologia_conectividad is None: return "Finalmente, para la Tecnología y Conectividad del coche, ¿qué tan relevante es para ti (0-10)?"
    if prefs.prioriza_baja_depreciacion is None: return "¿Es importante para ti que la depreciación del coche sea lo más baja posible? 'sí' o 'no'"
    # --- FIN NUEVAS PREGUNTAS DE RATING ---
    
    return "¿Podrías darme algún detalle más sobre tus preferencias?" # Fallback muy genérico

def preguntar_preferencias_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Añade la pregunta de seguimiento correcta al historial.
    Verifica si el perfil está realmente completo ANTES de añadir un mensaje 
    de confirmación/transición. Si no lo está, asegura que se añada una pregunta real.
    """
    print("--- Ejecutando Nodo: preguntar_preferencias_node ---")
    mensaje_pendiente = state.get("pregunta_pendiente") 
    preferencias = state.get("preferencias_usuario")
    historial_actual = state.get("messages", [])
    historial_nuevo = list(historial_actual) 
    
    mensaje_a_enviar = None 

    # 1. Comprobar si el perfil está REALMENTE completo AHORA
    perfil_esta_completo = check_perfil_usuario_completeness(preferencias)

    if not perfil_esta_completo:
        print("DEBUG (Preguntar Perfil) ► Perfil aún INCOMPLETO según checker.")
        pregunta_generada_fallback = None 

        # Generar la pregunta específica AHORA por si la necesitamos
        try:
             pregunta_generada_fallback = _obtener_siguiente_pregunta_perfil(preferencias)
             print(f"DEBUG (Preguntar Perfil) ► Pregunta fallback generada: {pregunta_generada_fallback}")
        except Exception as e_fallback:
             print(f"ERROR (Preguntar Perfil) ► Error generando pregunta fallback: {e_fallback}")
             pregunta_generada_fallback = "¿Podrías darme más detalles sobre tus preferencias?" 

        # ¿Tenemos un mensaje pendiente del LLM?
        if mensaje_pendiente and mensaje_pendiente.strip():
            # Comprobar si el mensaje pendiente PARECE una confirmación
            es_confirmacion = (
                mensaje_pendiente.startswith("¡Perfecto!") or 
                mensaje_pendiente.startswith("¡Genial!") or 
                mensaje_pendiente.startswith("¡Estupendo!") or 
                mensaje_pendiente.startswith("Ok,") or 
                "¿Pasamos a" in mensaje_pendiente
            )

            if es_confirmacion:
                # IGNORAR la confirmación errónea y USAR el fallback
                print(f"WARN (Preguntar Perfil) ► Mensaje pendiente ('{mensaje_pendiente}') parece confirmación, pero perfil incompleto. IGNORANDO y usando fallback.")
                mensaje_a_enviar = pregunta_generada_fallback
            else:
                # El mensaje pendiente parece una pregunta válida, la usamos.
                 print(f"DEBUG (Preguntar Perfil) ► Usando mensaje pendiente (pregunta LLM): {mensaje_pendiente}")
                 mensaje_a_enviar = mensaje_pendiente
        else:
            # No había mensaje pendiente válido, usamos la fallback generada.
            print("WARN (Preguntar Perfil) ► Nodo ejecutado para preguntar, pero no había mensaje pendiente válido. Generando pregunta fallback.")
            mensaje_a_enviar = pregunta_generada_fallback
            
    else: # El perfil SÍ está completo
        print("DEBUG (Preguntar Perfil) ► Perfil COMPLETO según checker.")
        # Usamos el mensaje pendiente (que debería ser de confirmación)
        if mensaje_pendiente and mensaje_pendiente.strip():
             print(f"DEBUG (Preguntar Perfil) ► Usando mensaje de confirmación pendiente: {mensaje_pendiente}")
             mensaje_a_enviar = mensaje_pendiente
        else:
             print("WARN (Preguntar Perfil) ► Perfil completo pero no había mensaje pendiente. Usando confirmación genérica.")
             mensaje_a_enviar = "¡Entendido! Ya tenemos tu perfil completo." # Mensaje simple

    # Añadir el mensaje decidido al historial
    if mensaje_a_enviar and mensaje_a_enviar.strip():
        ai_msg = AIMessage(content=mensaje_a_enviar)
        if not historial_actual or historial_actual[-1].content != ai_msg.content:
            historial_nuevo.append(ai_msg)
            print(f"DEBUG (Preguntar Perfil) ► Mensaje final añadido: {mensaje_a_enviar}") 
        else:
             print("DEBUG (Preguntar Perfil) ► Mensaje final duplicado, no se añade.")
    else:
         print("ERROR (Preguntar Perfil) ► No se determinó ningún mensaje a enviar.")
         ai_msg = AIMessage(content="No estoy seguro de qué preguntar ahora. ¿Puedes darme más detalles?")
         historial_nuevo.append(ai_msg)

    # Devolver estado
    return {**state, "messages": historial_nuevo, "pregunta_pendiente": None}


# --- NUEVA ETAPA: PASAJEROS ---

def recopilar_info_pasajeros_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Procesa entrada humana, llama a llm_pasajeros, actualiza info_pasajeros,
    y guarda el contenido del mensaje devuelto en 'pregunta_pendiente'.
    Es el nodo principal del bucle de pasajeros.
    """
    print("--- Ejecutando Nodo: recopilar_info_pasajeros_node ---")
    historial = state.get("messages", [])
    pasajeros_actuales = state.get("info_pasajeros") # Puede ser None o InfoPasajeros

    # Guarda AIMessage (igual que en perfil)
    if historial and isinstance(historial[-1], AIMessage):
        print("DEBUG (Pasajeros) ► Último mensaje es AIMessage, omitiendo llamada a llm_pasajeros.")
        return {**state, "pregunta_pendiente": None} 

    print("DEBUG (Pasajeros) ► Último mensaje es HumanMessage o inicio de etapa, llamando a llm_pasajeros...")
    
    pasajeros_actualizados = pasajeros_actuales # Usar como fallback
    contenido_msg_llm = None

    try:
        # Llama al LLM específico de pasajeros
        response: ResultadoPasajeros = llm_pasajeros.invoke(
            [system_prompt_pasajeros, *historial],
            config={"configurable": {"tags": ["llm_pasajeros"]}} 
        )
        print(f"DEBUG (Pasajeros) ► Respuesta llm_pasajeros: {response}")

        pasajeros_nuevos = response.info_pasajeros 
        tipo_msg_llm = response.tipo_mensaje 
        contenido_msg_llm = response.contenido_mensaje
        
        print(f"DEBUG (Pasajeros) ► Tipo='{tipo_msg_llm}', Contenido='{contenido_msg_llm}'")
        print(f"DEBUG (Pasajeros) ► Info Pasajeros LLM: {pasajeros_nuevos}")

        # Actualizar el estado 'info_pasajeros' (fusión simple)
        if pasajeros_actuales and pasajeros_nuevos:
            try:
                update_data = pasajeros_nuevos.model_dump(exclude_unset=True, exclude_none=True)
                if update_data:
                    pasajeros_actualizados = pasajeros_actuales.model_copy(update=update_data)
                # else: No hacer nada si no hay datos nuevos
            except Exception as e_merge:
                print(f"ERROR (Pasajeros) ► Fallo al fusionar info_pasajeros: {e_merge}")
                pasajeros_actualizados = pasajeros_actuales # Mantener anterior
        elif pasajeros_nuevos:
             pasajeros_actualizados = pasajeros_nuevos # Usar el nuevo si no había antes
        # Si ambos son None o pasajeros_nuevos es None, pasajeros_actualizados mantiene su valor inicial

    except ValidationError as e_val:
        print(f"ERROR (Pasajeros) ► Error de Validación Pydantic en llm_pasajeros: {e_val}")
        contenido_msg_llm = f"Hubo un problema al entender la información sobre pasajeros: {e_val}. ¿Podrías repetirlo?"
    except Exception as e:
        print(f"ERROR (Pasajeros) ► Fallo general al invocar llm_pasajeros: {e}")
        traceback.print_exc()
        contenido_msg_llm = "Lo siento, tuve un problema técnico procesando la información de pasajeros."

    print(f"DEBUG (Pasajeros) ► Estado info_pasajeros actualizado: {pasajeros_actualizados}")
    
    # Guardar la pregunta/confirmación pendiente
    pregunta_para_siguiente_nodo = None
    if contenido_msg_llm and contenido_msg_llm.strip():
        pregunta_para_siguiente_nodo = contenido_msg_llm.strip()
        print(f"DEBUG (Pasajeros) ► Guardando mensaje pendiente: {pregunta_para_siguiente_nodo}")
    else:
        print(f"DEBUG (Pasajeros) ► No hay mensaje pendiente.")
        
    return {
        **state,
        "info_pasajeros": pasajeros_actualizados, # Guardar info actualizada
        "pregunta_pendiente": pregunta_para_siguiente_nodo 
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
    """Genera una pregunta fallback específica para pasajeros si falta algo."""
    if info is None or info.frecuencia is None:
        return "Cuéntame, ¿quiénes suelen viajar contigo en el coche habitualmente? ¿Llevas pasajeros a menudo?"
    elif info.frecuencia != "nunca":
        if info.num_ninos_silla is None and info.num_otros_pasajeros is None:
            return "¿Cuántas personas suelen ser en total (adultos/niños)? ¿Algún niño necesita sillita?"
        elif info.num_ninos_silla is None:
            # Intenta ser un poco más específico si ya sabe Z
            z_val = info.num_otros_pasajeros
            if z_val is not None:
                 return f"Entendido, con {z_val}. ¿Hay también niños que necesiten sillita de seguridad?"
            else: # Si Z también fuera None (raro aquí), preguntar genérico
                 return "¿Necesitas espacio para alguna sillita infantil?"
        elif info.num_otros_pasajeros is None:
             x_val = info.num_ninos_silla
             if x_val is not None:
                  return f"Entendido, {x_val} niño(s) con sillita. ¿Suelen ir más pasajeros (adultos u otros niños sin silla)?"
             else: # Raro
                  return "¿Suelen viajar otros adultos o niños mayores además de los que usan sillita?"
    return "¿Algo más sobre los pasajeros que deba saber?" # Fallback muy genérico

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
    Calcula: plazas_min (siempre), penalizar_puertas_bajas, priorizar_ancho.
    """
    print("--- Ejecutando Nodo: aplicar_filtros_pasajeros_node ---")
    info_pasajeros_obj = state.get("info_pasajeros") # <-- Renombrado para claridad
    filtros_actuales = state.get("filtros_inferidos") or FiltrosInferidos() 

    # Valores por defecto para los flags
    penalizar_p = False 
    priorizar_a = False 
    
    # Valores para X y Z (default 0)
    X = 0
    Z = 0
    frecuencia = None

    if info_pasajeros_obj: # Verificar que info_pasajeros_obj exista
        frecuencia = info_pasajeros_obj.frecuencia
        X = info_pasajeros_obj.num_ninos_silla or 0
        Z = info_pasajeros_obj.num_otros_pasajeros or 0
        print(f"DEBUG (Aplicar Filtros Pasajeros) ► Info recibida: freq='{frecuencia}', X={X}, Z={Z}")
    else:
        print("ERROR (Aplicar Filtros Pasajeros) ► No hay información de pasajeros en el estado. Se usarán defaults para plazas.")
        # frecuencia seguirá siendo None, X y Z son 0

    # --- Calcular plazas_min SIEMPRE ---
    # Si frecuencia es 'nunca' o None, X y Z son 0, entonces plazas_calc = 1.
    plazas_calc = X + Z + 1 
    print(f"DEBUG (Aplicar Filtros Pasajeros) ► Calculado plazas_min = {plazas_calc}")

    # --- Aplicar reglas para flags que SÍ dependen de la frecuencia ---
    if frecuencia and frecuencia != "nunca":
        # Regla Priorizar Ancho (si Z>=2 para ocasional o frecuente)
        if Z >= 2:
            priorizar_a = True
            print("DEBUG (Aplicar Filtros Pasajeros) ► Indicador priorizar_ancho = True")
            
        # Regla Penalizar Puertas Bajas (solo si frecuente y X>=1)
        if frecuencia == "frecuente" and X >= 1:
            penalizar_p = True
            print("DEBUG (Aplicar Filtros Pasajeros) ► Indicador penalizar_puertas_bajas = True")
    else:
        print("DEBUG (Aplicar Filtros Pasajeros) ► Frecuencia es 'nunca' o None. Flags de priorizar_ancho y penalizar_puertas se mantienen en su default (False).")


    # Actualizar el objeto filtros_inferidos con plazas_min
    update_filtros_dict = {"plazas_min": plazas_calc}
    filtros_actualizados = filtros_actuales.model_copy(update=update_filtros_dict)
    print(f"DEBUG (Aplicar Filtros Pasajeros) ► Filtros actualizados (con plazas_min): {filtros_actualizados}")

    # Devolver el estado completo actualizado
    # Asegúrate que tu return en finalizar_y_presentar_node y los TypedDict sean explícitos para estas claves
    return {
        # **state, # Considera devolver solo lo que cambia o el estado explícito
        "preferencias_usuario": state.get("preferencias_usuario"),
        "info_pasajeros": info_pasajeros_obj, # El objeto original
        "filtros_inferidos": filtros_actualizados, # Con plazas_min actualizado
        "economia": state.get("economia"),          
        "pesos": state.get("pesos"), 
        "pregunta_pendiente": state.get("pregunta_pendiente"), 
        "coches_recomendados": state.get("coches_recomendados"), 
        "tabla_resumen_criterios": state.get("tabla_resumen_criterios"),
        "penalizar_puertas_bajas": penalizar_p,  # Guardar flag actualizado
        "priorizar_ancho": priorizar_a,          # Guardar flag actualizado
        "flag_penalizar_low_cost_comodidad": state.get("flag_penalizar_low_cost_comodidad"), # Mantener estos
        "flag_penalizar_deportividad_comodidad": state.get("flag_penalizar_deportividad_comodidad")
    }

# --- Fin Nueva Etapa Pasajeros ---
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
        #print(f"DEBUG (Filtros) ► Guardando pregunta pendiente: {pregunta_para_siguiente_nodo}")
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

# Tu código para finalizar_y_presentar_node

def finalizar_y_presentar_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Realiza los cálculos finales (Modo 1 econ, RAG carrocerías, pesos, flags de penalización) 
    y formatea la tabla resumen final una vez toda la información está completa.
    """
    print("--- Ejecutando Nodo: finalizar_y_presentar_node ---")
    historial = state.get("messages", [])
    preferencias_obj = state.get("preferencias_usuario") # Este es el objeto PerfilUsuario
    filtros_obj = state.get("filtros_inferidos")       # Objeto FiltrosInferidos
    economia_obj = state.get("economia")           # Objeto EconomiaUsuario
    info_pasajeros_obj = state.get("info_pasajeros") # Objeto InfoPasajeros
    priorizar_ancho_flag = state.get("priorizar_ancho", False)
    pesos_calculados = None # Inicializar
    tabla_final_md = "Error al generar el resumen." # Default

    # Verificar pre-condiciones
    if not preferencias_obj or not filtros_obj or not economia_obj: # info_pasajeros es opcional para este check
         print("ERROR (Finalizar) ► Faltan datos esenciales (perfil/filtros/economia) para finalizar.")
         ai_msg = AIMessage(content="Lo siento, parece que falta información para generar el resumen final.")
         # Devolver un estado mínimo para no romper el grafo
         return {
             "messages": historial + [ai_msg],
             "preferencias_usuario": preferencias_obj, "info_pasajeros": info_pasajeros_obj,
             "filtros_inferidos": filtros_obj, "economia": economia_obj, "pesos": None,
             "tabla_resumen_criterios": None, "coches_recomendados": None,
             "penalizar_puertas_bajas": state.get("penalizar_puertas_bajas"),
             "priorizar_ancho": priorizar_ancho_flag,
             "flag_penalizar_low_cost_comodidad": False, # Default
             "flag_penalizar_deportividad_comodidad": False ,# Default
             "flag_penalizar_antiguo_por_tecnologia": False,
             "aplicar_logica_distintivo_ambiental": False # <-- Default para el nuevo flag
         }
    # Trabajar con una copia de filtros para las modificaciones
    filtros_actualizados = filtros_obj.model_copy(deep=True)   
         
 # --- LÓGICA MODO 1 ECON (como la tenías) ---
    print("DEBUG (Finalizar) ► Verificando si aplica lógica Modo 1...")
    if economia_obj.modo == 1:
        # ... (tu lógica existente para calcular modo_adq_rec, etc. y actualizar filtros_actualizados) ...
        # Ejemplo resumido:
        print("DEBUG (Finalizar) ► Modo 1 detectado. Calculando recomendación...")
        try:
            ingresos = economia_obj.ingresos; ahorro = economia_obj.ahorro; anos_posesion = economia_obj.anos_posesion
            if ingresos is not None and ahorro is not None and anos_posesion is not None:
                 t = min(anos_posesion, 8); ahorro_utilizable = ahorro * 0.75
                 potencial_ahorro_plazo = ingresos * 0.1 * t
                 if potencial_ahorro_plazo <= ahorro_utilizable:
                     modo_adq_rec, precio_max_rec, cuota_max_calc = "Contado", potencial_ahorro_plazo, None
                 else:
                     modo_adq_rec, precio_max_rec, cuota_max_calc = "Financiado", None, (ingresos * 0.1) / 12
                 update_dict = {"modo_adquisicion_recomendado": modo_adq_rec, "precio_max_contado_recomendado": precio_max_rec, "cuota_max_calculada": cuota_max_calc}
                 filtros_actualizados = filtros_actualizados.model_copy(update=update_dict) 
                 print(f"DEBUG (Finalizar) ► Filtros actualizados con recomendación Modo 1: {filtros_actualizados}")
        except Exception as e_calc:
            print(f"ERROR (Finalizar) ► Fallo durante cálculo de recomendación Modo 1: {e_calc}")
    else:
         print("DEBUG (Finalizar) ► Modo no es 1, omitiendo cálculo de recomendación.")
    # --- FIN LÓGICA MODO 1 ---
    
    # Convertir a dicts ANTES de pasarlos a funciones que los esperan así
    prefs_dict_para_funciones = preferencias_obj.model_dump(mode='json', exclude_none=False)
    filtros_dict_para_rag = filtros_actualizados.model_dump(mode='json', exclude_none=False)
    info_pasajeros_dict_para_rag = info_pasajeros_obj.model_dump(mode='json') if info_pasajeros_obj else None

    # 1. Llamada RAG
    if not filtros_actualizados.tipo_carroceria: 
        print("DEBUG (Finalizar) ► Llamando a RAG...")
        try:
            tipos_carroceria_rec = get_recommended_carrocerias(
                prefs_dict_para_funciones, 
                filtros_dict_para_rag, 
                info_pasajeros_dict_para_rag, 
                k=4
            ) 
            print(f"DEBUG (Finalizar) ► RAG recomendó: {tipos_carroceria_rec}")
            filtros_actualizados.tipo_carroceria = tipos_carroceria_rec 
        except Exception as e_rag:
            print(f"ERROR (Finalizar) ► Fallo en RAG: {e_rag}")
            filtros_actualizados.tipo_carroceria = ["Error RAG"] 
    
    # --- LÓGICA PARA FLAGS DE PENALIZACIÓN POR COMODIDAD (USANDO OBJETO Pydantic) ---
    UMBRAL_COMODIDAD_PARA_PENALIZAR = 7 
    flag_penalizar_low_cost_comodidad = False
    flag_penalizar_deportividad_comodidad = False

    # Usamos el objeto preferencias_obj directamente aquí
    if preferencias_obj and preferencias_obj.rating_comodidad is not None:
        if preferencias_obj.rating_comodidad >= UMBRAL_COMODIDAD_PARA_PENALIZAR:
            flag_penalizar_low_cost_comodidad = True
            flag_penalizar_deportividad_comodidad = True
            print(f"DEBUG (Finalizar) ► Rating Comodidad ({preferencias_obj.rating_comodidad}) >= {UMBRAL_COMODIDAD_PARA_PENALIZAR}. Activando flags de penalización.")
    
    # --- NUEVA LÓGICA PARA FLAG DE PENALIZACIÓN POR ANTIGÜEDAD Y TECNOLOGÍA ---
    UMBRAL_TECNOLOGIA_PARA_PENALIZAR_ANTIGUEDAD = 7 # Ejemplo, puedes ajustarlo

    flag_penalizar_antiguo_tec = False 
    if preferencias_obj and preferencias_obj.rating_tecnologia_conectividad is not None:
        if preferencias_obj.rating_tecnologia_conectividad >= UMBRAL_TECNOLOGIA_PARA_PENALIZAR_ANTIGUEDAD:
            flag_penalizar_antiguo_tec = True
            print(f"DEBUG (Finalizar) ► Rating Tecnología ({preferencias_obj.rating_tecnologia_conectividad}) >= {UMBRAL_TECNOLOGIA_PARA_PENALIZAR_ANTIGUEDAD}. Activando flag de penalización por antigüedad.")
            
    # --- NUEVA LÓGICA PARA FLAG DE DISTINTIVO AMBIENTAL ---
    UMBRAL_IMPACTO_AMBIENTAL_PARA_LOGICA = 8 # ¡AJUSTA ESTE UMBRAL!
    flag_aplicar_logica_distintivo = False # Default
    
    if preferencias_obj and preferencias_obj.rating_impacto_ambiental is not None:
        if preferencias_obj.rating_impacto_ambiental >= UMBRAL_IMPACTO_AMBIENTAL_PARA_LOGICA:
            flag_aplicar_logica_distintivo = True
            print(f"DEBUG (Finalizar) ► Rating Impacto Ambiental ({preferencias_obj.rating_impacto_ambiental}) >= {UMBRAL_IMPACTO_AMBIENTAL_PARA_LOGICA}. Activando lógica de distintivo ambiental.")
    # --- FIN NUEVA LÓGICA FLAG DISTINTIVO ---
    # ---
    # 2. Cálculo de Pesos
    print("DEBUG (Finalizar) ► Calculando pesos...")
    try:
        estetica_min_val = filtros_actualizados.estetica_min
        premium_min_val = filtros_actualizados.premium_min
        singular_min_val = filtros_actualizados.singular_min

        raw_weights = compute_raw_weights(
            preferencias=prefs_dict_para_funciones, # compute_raw_weights espera un dict
            estetica_min_val=estetica_min_val,
            premium_min_val=premium_min_val,
            singular_min_val=singular_min_val,
            priorizar_ancho=priorizar_ancho_flag
        )
        pesos_calculados = normalize_weights(raw_weights)
        print(f"DEBUG (Finalizar) ► Pesos calculados: {pesos_calculados}") 
    except Exception as e_weights:
        print(f"ERROR (Finalizar) ► Fallo calculando pesos: {e_weights}")
        traceback.print_exc()
        pesos_calculados = {} # Default a dict vacío en error para evitar None más adelante
    
    # 3. Formateo de la Tabla
    print("DEBUG (Finalizar) ► Formateando tabla final...")
    try:
        # Pasamos los OBJETOS Pydantic originales (o actualizados)
        tabla_final_md = formatear_preferencias_en_tabla(
            preferencias=preferencias_obj, 
            filtros=filtros_actualizados, 
            economia=economia_obj
            # info_pasajeros también podría pasarse si el formateador lo usa
        )
        print("\n--- TABLA RESUMEN GENERADA (DEBUG) ---")
        print(tabla_final_md)
        print("--------------------------------------\n")
    except Exception as e_format:
        print(f"ERROR (Finalizar) ► Fallo formateando la tabla: {e_format}")
        tabla_final_md = "Error al generar el resumen de criterios."

    # 4. Crear y añadir mensaje final
    final_ai_msg = AIMessage(content=tabla_final_md)
    historial_final = list(historial)
    if not historial or historial[-1].content != final_ai_msg.content:
        historial_final.append(final_ai_msg)

    return {
        **state, # Propaga el estado original
        "filtros_inferidos": filtros_actualizados, # Sobrescribe con el actualizado
        "pesos": pesos_calculados,                 # Añade/Sobrescribe
        "messages": historial_final,               # Sobrescribe
        "tabla_resumen_criterios": tabla_final_md, # Añade/Sobrescribe
        "coches_recomendados": None,               # Añade/Sobrescribe
        "priorizar_ancho": priorizar_ancho_flag,   # Sobrescribe con el valor local
        "flag_penalizar_low_cost_comodidad": flag_penalizar_low_cost_comodidad, # Añade/Sobrescribe
        "flag_penalizar_deportividad_comodidad": flag_penalizar_deportividad_comodidad, # Añade/Sobrescribe
        "flag_penalizar_antiguo_por_tecnologia": flag_penalizar_antiguo_tec,
        "aplicar_logica_distintivo_ambiental": flag_aplicar_logica_distintivo,
        "pregunta_pendiente": None                 # Sobrescribe
    }
  # --- Fin Etapa 4 ---


# --- NUEVO NODO BÚSQUEDA FINAL Etapa 5 ---
def buscar_coches_finales_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Usa los filtros y pesos finales del estado para buscar coches en BQ,
    presenta los resultados y loguea la búsqueda.
    """
    print("--- Ejecutando Nodo: buscar_coches_finales_node ---")
    print(f"DEBUG (Buscar BQ Init) ► Estado completo recibido: {state}") # Imprime todo el estado
    historial = state.get("messages", [])
    filtros_finales_obj = state.get("filtros_inferidos") # Es el objeto FiltrosInferidos
    pesos_finales = state.get("pesos")
    economia_obj = state.get("economia") # Es el objeto EconomiaUsuario
    penalizar_puertas_flag = state.get("penalizar_puertas_bajas", False)
    tabla_resumen_criterios = state.get("tabla_resumen_criterios") # Tabla MD de criterios
    flag_penalizar_lc_comod = state.get("flag_penalizar_low_cost_comodidad", False)
    flag_penalizar_dep_comod = state.get("flag_penalizar_deportividad_comodidad", False)
    flag_penalizar_antiguo_tec_val = state.get("flag_penalizar_antiguo_por_tecnologia", False)
    flag_aplicar_distintivo_val = state.get("aplicar_logica_distintivo_ambiental", False)


    thread_id = "unknown_thread"
    if state.get("config") and isinstance(state["config"], dict) and \
       state["config"].get("configurable") and isinstance(state["config"]["configurable"], dict):
        thread_id = state["config"]["configurable"].get("thread_id", "unknown_thread")
    
    coches_encontrados = []
    sql_ejecutada = None 
    params_ejecutados = None 
    mensaje_final = "No pude realizar la búsqueda en este momento." # Default

    if filtros_finales_obj and pesos_finales:
        filtros_para_bq = {}
        if hasattr(filtros_finales_obj, "model_dump"):
             filtros_para_bq.update(filtros_finales_obj.model_dump(mode='json', exclude_none=True))
        elif isinstance(filtros_finales_obj, dict): # Fallback si ya es dict
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
        
        k_coches = 7 
        print(f"DEBUG (Buscar BQ) ► Llamando a buscar_coches_bq con k={k_coches}")
        print(f"DEBUG (Buscar BQ) ► Filtros para BQ: {filtros_para_bq}") 
        print(f"DEBUG (Buscar BQ) ► Pesos para BQ: {pesos_finales}") 
        
        try:
            # --- MODIFICAR LLAMADA PARA OBTENER SQL/PARAMS ---
            resultados_tupla = buscar_coches_bq(
                filtros=filtros_para_bq, 
                pesos=pesos_finales, 
                k=k_coches
            )
            # Desempaquetar la tupla
            if isinstance(resultados_tupla, tuple) and len(resultados_tupla) == 3:
                coches_encontrados, sql_ejecutada, params_ejecutados = resultados_tupla
            else: # Si buscar_coches_bq no fue actualizada y solo devuelve la lista
                print("WARN (Buscar BQ) ► buscar_coches_bq no devolvió SQL/params. Logueo será parcial.")
                coches_encontrados = resultados_tupla if isinstance(resultados_tupla, list) else []
            # --- FIN MODIFICACIÓN ---

            if coches_encontrados:
                mensaje_final = f"¡Listo! Basado en todo lo que hablamos, aquí tienes {len(coches_encontrados)} coche(s) que podrían interesarte:\n\n"
                try:
                    df_coches = pd.DataFrame(coches_encontrados)
                    columnas_deseadas = ['nombre', 'marca', 'precio_compra_contado', 'score_total', 'tipo_carroceria', 'tipo_mecanica', 'plazas', 'puertas', 'traccion', 'reductoras', 'estetica', 'premium', 'singular', 'ancho', 'altura_libre_suelo', 'batalla', 'indice_altura_interior', 'cambio_automatico']
                    columnas_a_mostrar = [col for col in columnas_deseadas if col in df_coches.columns]
                    
                    if columnas_a_mostrar:
                        if 'precio_compra_contado' in df_coches.columns:
                            df_coches['precio_compra_contado'] = df_coches['precio_compra_contado'].apply(lambda x: f"{x:,.0f}€".replace(",",".") if isinstance(x, (int, float)) else "N/A")
                        if 'score_total' in df_coches.columns:
                             df_coches['score_total'] = df_coches['score_total'].apply(lambda x: f"{x:.3f}" if isinstance(x, float) else x)
                        tabla_coches_md = df_coches[columnas_a_mostrar].to_markdown(index=False)
                        mensaje_final += tabla_coches_md
                    else:
                        mensaje_final += "No se pudieron formatear los detalles de los coches."
                except Exception as e_format_coches:
                    print(f"ERROR (Buscar BQ) ► Falló el formateo de la tabla de coches: {e_format_coches}")
                    mensaje_final += "Hubo un problema al mostrar los detalles. Aquí una lista simple:\n"
                    for i, coche in enumerate(coches_encontrados):
                        nombre = coche.get('nombre', 'N/D'); precio = coche.get('precio_compra_contado')
                        precio_str = f"{precio:,.0f}€".replace(",",".") if isinstance(precio, (int, float)) else "N/A"
                        mensaje_final += f"{i+1}. {nombre} - {precio_str}\n"
                mensaje_final += "\n\n¿Qué te parecen estas opciones? ¿Hay alguno que te interese para ver más detalles o hacemos otra búsqueda?"
            else:
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
                    mensaje_final = _sugerencia_generada # Usar la sugerencia específica
                
                if not _sugerencia_generada: # Si ninguna heurística aplicó
                    _sugerencia_generada = "He aplicado todos tus filtros, pero no encontré coches que coincidan exactamente en este momento. ¿Quizás quieras redefinir algún criterio general?"
                mensaje_final = _sugerencia_generada
                
        except Exception as e_bq:
            print(f"ERROR (Buscar BQ) ► Falló la ejecución de buscar_coches_bq: {e_bq}")
            traceback.print_exc()
            mensaje_final = f"Lo siento, tuve un problema al buscar en la base de datos de coches: {e_bq}"
    else:
        print("ERROR (Buscar BQ) ► Faltan filtros o pesos finales en el estado.")
        mensaje_final = "Lo siento, falta información interna para realizar la búsqueda final."

    # --- LLAMADA AL LOGGER ANTES DE AÑADIR MENSAJE FINAL AL HISTORIAL ---
    # Solo loguear si la búsqueda se intentó (filtros y pesos estaban presentes)
    if filtros_finales_obj and pesos_finales:
        try:
            log_busqueda_a_bigquery(
                id_conversacion=thread_id,
                preferencias_usuario_obj=state.get("preferencias_usuario"),
                filtros_aplicados_obj=filtros_finales_obj, 
                economia_usuario_obj=economia_obj,
                pesos_aplicados_dict=pesos_finales,
                tabla_resumen_criterios_md=tabla_resumen_criterios, # <-- Viene del estado
                coches_recomendados_list=coches_encontrados,
                num_coches_devueltos=len(coches_encontrados),
                sql_query_ejecutada=sql_ejecutada, # <-- De la llamada a buscar_coches_bq
                sql_params_list=params_ejecutados  # <-- De la llamada a buscar_coches_bq
            )
        except Exception as e_log:
            print(f"ERROR (Buscar BQ) ► Falló el logueo a BigQuery: {e_log}")
            traceback.print_exc()
    # --- FIN LLAMADA AL LOGGER ---
    final_ai_msg = AIMessage(content=mensaje_final)
    historial_final = list(historial)
    if not historial or historial[-1].content != final_ai_msg.content:
        historial_final.append(final_ai_msg)
    else:
        print("DEBUG (Buscar BQ) ► Mensaje final duplicado, no se añade.")

    return {
        "coches_recomendados": coches_encontrados, 
        "messages": historial_final,
        # Aseguramos que los campos que deben limpiarse/actualizarse lo hagan
        "pregunta_pendiente": None, # Este nodo es final, no deja preguntas
        "filtros_inferidos": filtros_finales_obj, # Ya estaban actualizados
        "pesos": pesos_finales, # Ya estaban actualizados
        "economia": economia_obj, # No se modifica aquí
        "info_pasajeros": state.get("info_pasajeros"), # No se modifica aquí
        "preferencias_usuario": state.get("preferencias_usuario"), # No se modifica aquí
        "flag_penalizar_low_cost_comodidad": flag_penalizar_lc_comod,
        "flag_penalizar_deportividad_comodidad": flag_penalizar_dep_comod, 
        "flag_penalizar_antiguo_por_tecnologia": flag_penalizar_antiguo_tec_val,
        "aplicar_logica_distintivo_ambiental": flag_aplicar_distintivo_val,
        "tabla_resumen_criterios": tabla_resumen_criterios # Persiste si se necesita
    }