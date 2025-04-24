from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import Runnable
from typing import List
from config.llm import prompt_validacion
from utils.conversion import get_enum_names

def generar_mensaje_validacion_dinamico(
    preferencias: dict,
    filtros: dict,
    mensajes: List,
    llm_validacion: Runnable
) -> AIMessage:
    """
    Genera un mensaje conversacional natural con 1 o máximo 2 preguntas basadas en las preferencias y filtros faltantes.
    """

    campos_preferencias = [
        "solo_electricos","uso_profesional","aventura", "cambio_automatico","valora_estetica","altura_mayor_190", "peso_mayor_100", 
        "apasionado_motor"
    ]
    campos_filtros = ["tipo_mecanica"]

    preferencias_faltantes = [k for k in campos_preferencias if preferencias.get(k) in [None, "", "null"]]
    filtros_faltantes = [k for k in campos_filtros if filtros.get(k) in [None, "", [], "null"]]

    # # Convertir Enums a texto plano
    # if "tipo_carroceria" in filtros and isinstance(filtros["tipo_carroceria"], list):
    #     filtros["tipo_carroceria"] = get_enum_names(filtros["tipo_carroceria"])
    if "tipo_mecanica" in filtros and isinstance(filtros["tipo_mecanica"], list):
        filtros["tipo_mecanica"] = get_enum_names(filtros["tipo_mecanica"])

    # Crear la entrada para el modelo
    mensajes_llm = [
        SystemMessage(content=prompt_validacion),
        *mensajes,  # historial
        AIMessage(content=(
            f"Preferencias conocidas: {preferencias}\n"
            f"Filtros inferidos: {filtros}\n"
            f"Preferencias faltantes: {preferencias_faltantes}\n"
            f"Filtros faltantes: {filtros_faltantes}"
        ))
    ]

    # Generar respuesta
    return llm_validacion.invoke(mensajes_llm)


