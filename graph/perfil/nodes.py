
from langchain_core.messages import HumanMessage, BaseMessage,AIMessage
from utils.formatters import formatear_preferencias_en_tabla
from utils.postprocessing import es_fuera_de_dominio , aplicar_postprocesamiento
from .state import EstadoAnalisisPerfil
from config.llm import structured_llm
from prompts.loader import perfil_structured_sys_msg
from config.llm import llm_validacion
from utils.generadores import generar_mensaje_validacion_dinamico
import random


def analizar_perfil_usuario_node(state: EstadoAnalisisPerfil) -> dict:
    historial = state.get("messages", [])

    # Aquí podrías usarlo para registrar entradas fuera de dominio si lo deseas:
    # if es_fuera_de_dominio(historial[-1].content.lower()):
    #     print("⚠️ Pregunta fuera de dominio detectada:", historial[-1].content)

    # Ejecutar el modelo estructurado con todo el historial y el system message
    response = structured_llm.invoke([
        perfil_structured_sys_msg,
        *historial
    ])

    # Aplicar reglas defensivas post-LLM
    preferencias, filtros = aplicar_postprocesamiento(
        response.preferencias_usuario, response.filtros_inferidos
    )

    return {
        **state,
        "preferencias_usuario": preferencias,
        "filtros_inferidos": filtros,
        "mensaje_validacion": response.mensaje_validacion
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
        "solo_electricos", "uso_profesional", "altura_mayor_190",
        "peso_mayor_100", "valora_estetica", "cambio_automatico", "apasionado_motor"
    ]
    campos_filtros = ["tipo_carroceria", "tipo_mecanica", "premium_min", "singular_min"]

    preferencias_completas = all(preferencias.get(k) not in [None, "", "null"] for k in campos_preferencias)
    filtros_completos = all(filtros.get(k) not in [None, "", [], "null"] for k in campos_filtros)

    if preferencias_completas and filtros_completos:
        tabla = formatear_preferencias_en_tabla(preferencias, filtros)
        mensaje = AIMessage(content=tabla)
    else:
        # Usa el generador dinámico de mensajes para formular la próxima pregunta
        mensaje = generar_mensaje_validacion_dinamico(
            preferencias=preferencias,
            filtros=filtros,
            mensajes=state.get("messages", []),
            llm_validacion=llm_validacion
    )

    return {"messages": [mensaje]}



#Valida que el usuario ha respondido todas las preguntas necesarias para hacer una recomendación
# y si no, le pregunta lo que falta.
#Opcion funcional al 14 de Abril.
# def validar_preferencias_node(state: EstadoAnalisisPerfil) -> dict:
#     preferencias = state.get("preferencias_usuario", {})
#     if hasattr(preferencias, "model_dump"):
#         preferencias = preferencias.model_dump()

#     filtros = state.get("filtros_inferidos", {})
#     if hasattr(filtros, "model_dump"):
#         filtros = filtros.model_dump()

#     campos_preferencias = [
#         "solo_electricos", "uso_profesional", "altura_mayor_190",
#         "peso_mayor_100", "valora_estetica", "cambio_automatico", "apasionado_motor"
#     ]
#     campos_filtros = ["tipo_carroceria", "tipo_mecanica", "premium_min", "singular_min"]

#     preferencias_completas = all(preferencias.get(k) not in [None, "", "null"] for k in campos_preferencias)
#     filtros_completos = all(filtros.get(k) not in [None, "", [], "null"] for k in campos_filtros)

#     if preferencias_completas and filtros_completos:
#         tabla = formatear_preferencias_en_tabla(preferencias, filtros)
#         mensaje = AIMessage(content=tabla)
#     else:
#         texto = ""

#         intros = [
#             "",
#             "",
#             "Un detalle más para ayudarte:",
#             "Gracias, me falta saber:",
#             "continuemos afinando la recomendación:",
#             "Perfecto. Para afinar la recomendación",
#             "Antes de continuar, una pregunta rápida:",
#             "Para darte una mejor sugerencia:",
#             "necesito saber algo más:",
#             ""
#         ]

#         campos_prioritarios = [
#             ("solo_electricos", "¿Quieres un coche totalmente eléctrico o estás abierto a otras opciones?"),
#             ("uso_profesional", "¿Lo usarás principalmente para trabajar o para uso personal?"),
#             ("valora_estetica", "¿Qué tan importante es que el coche se vea bien (estética)?"),
#             ("cambio_automatico", "¿Prefieres un coche automático o manual?"),
#             ("altura_mayor_190", "¿Podrías decirme si mides más de 1.90 m?"),
#             ("peso_mayor_100", "¿Sabes si pesas más de 100 kg?"),
#             ("apasionado_motor", "¿Eres un apasionado/a del motor y/o la movilidad?"),
#             ("tipo_carroceria", "¿Qué tipo de coche te interesa más? Puedes pensar en algo:\n"
#              "• Compacto o urbano (como una berlina o coupé)\n"
#              "• Familiar y amplio (como un SUV, monovolumen o furgoneta)\n"
#              "• Aventura o trabajo (como una pickup, comercial o autocaravana)\n"
#              "• Descubierto y con estilo (como un descapotable)\n")
#         ]

#         preguntas_faltantes = [pregunta for campo, pregunta in campos_prioritarios if preferencias.get(campo) in [None, "", "null"] or (campo == "tipo_carroceria" and not filtros.get("tipo_carroceria"))]

#         if preguntas_faltantes:
#             texto += random.choice(intros) + "\n"
#             texto += f"{preguntas_faltantes[0]}\n" # podriamos poner un maximo de 2 preguntas, guiones o dar algun formato a cada mensaje

#         mensaje = AIMessage(content=texto.strip())

#     return {"messages": [mensaje]}
