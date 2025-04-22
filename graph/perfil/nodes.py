
from langchain_core.messages import HumanMessage, BaseMessage,AIMessage
from utils.formatters import formatear_preferencias_en_tabla
from utils.postprocessing import aplicar_postprocesamiento
from .state import EstadoAnalisisPerfil
from config.llm import structured_llm
from prompts.loader import perfil_structured_sys_msg
from config.llm import llm_validacion
from utils.generadores import generar_mensaje_validacion_dinamico
from utils.preprocesing import extraer_preferencias_iniciales
from utils.weights import compute_raw_weights, normalize_weights
import random

def analizar_perfil_usuario_node(state: EstadoAnalisisPerfil) -> dict:
    # ① Historial de mensajes
    historial = state.get("messages", [])
    ultimo = historial[-1].content if historial else ""
    iniciales = extraer_preferencias_iniciales(ultimo)
    # Inyectar en estado antes de llamar al LLM
    existing = state.get("preferencias_usuario") or {}
    state["preferencias_usuario"] = {**existing, **iniciales}

    # ② Llamada al LLM estructurado
    response = structured_llm.invoke([
        perfil_structured_sys_msg,
        *historial
    ])

    # ③ Reglas defensivas
    preferencias, filtros = aplicar_postprocesamiento(
        response.preferencias_usuario,
        response.filtros_inferidos
    )
    # ④ Fusionar las preferencias iniciales para que no se pierdan
    preferencias = {**preferencias, **iniciales}
    # Construir el mensaje de validación
    ai_msg = AIMessage(content=response.mensaje_validacion)

    # 5️ Devolver estado completo, agregando el mensaje al historial
    return {
        **state,
        "preferencias_usuario": preferencias,  # ya incorporadas las iniciales
        "filtros_inferidos":    filtros,
        # Si ya no necesitas este campo aparte, puedes omitirlo
        "mensaje_validacion":   response.mensaje_validacion,
        "messages":             historial + [ai_msg]
    }




#Funcion de prueba para tener conversaciones mas naturales 
def validar_preferencias_node(state: EstadoAnalisisPerfil) -> dict:
    preferencias = state.get("preferencias_usuario", {})
    if hasattr(preferencias, "model_dump"):
        preferencias = preferencias.model_dump()

    filtros = state.get("filtros_inferidos", {})
    if hasattr(filtros, "model_dump"):
        filtros = filtros.model_dump()

    campos_preferencias = [
        "solo_electricos", "aventura", "altura_mayor_190", "valora_estetica",
        "apasionado_motor", "uso_profesional", "cambio_automatico", "peso_mayor_100"
    ]
    campos_filtros = ["tipo_mecanica"]

    preferencias_completas = all(preferencias.get(k) not in [None, "", "null"] for k in campos_preferencias)
    filtros_completos       = all(filtros.get(k) not in [None, "", [], "null"] for k in campos_filtros)

    if preferencias_completas and filtros_completos:
        # ① Formatear tabla 
        tabla   = formatear_preferencias_en_tabla(preferencias, filtros)
        mensaje = AIMessage(content=tabla)

        # ② Calcular pesos suaves
        aventura_val = preferencias.get("aventura")
        # ➡️ Si es un Enum, toma .value; si es string no vacío, si no, fallback a "ninguna"
        if hasattr(aventura_val, "value"):
            aventura_lvl = aventura_val.value
        elif isinstance(aventura_val, str) and aventura_val:
            aventura_lvl = aventura_val
        else:
            aventura_lvl = "ninguna"
        raw   = compute_raw_weights(
            estetica=      filtros["estetica_min"],
            premium=       filtros["premium_min"],
            singular=      filtros["singular_min"],
            aventura_level=aventura_lvl
        )
        # ➡️ Normalizar pesos
        pesos = normalize_weights(raw)
          
    else:
        # Usa el generador dinámico de mensajes para formular la próxima pregunta
        mensaje = generar_mensaje_validacion_dinamico(
            preferencias=preferencias,
            filtros=filtros,
            mensajes=state.get("messages", []),
            llm_validacion=llm_validacion
        )

    # ③ Devolver todo el estado incluyendo pesos (si los calculamos)
    new_state = {
        **state,
        "preferencias_usuario": preferencias,
        "filtros_inferidos":    filtros,
        "messages":             state.get("messages", []) + [mensaje]
    }
    if preferencias_completas and filtros_completos:
        new_state["pesos"] = pesos

    return new_state
