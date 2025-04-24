from typing import TypedDict
from typing import List, Optional, Annotated, Literal
from langchain_core.messages import HumanMessage, BaseMessage,AIMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from utils.enums import TipoCarroceria, TipoMecanica, NivelAventura


# Este archivo define la estructura del estado para:
# Guardar el historial de mensajes.
# Almacenar lo que el agente ha inferido del usuario (preferencias_usuario, filtros_inferidos...).
# Hacer persistente y rastreable la conversación y los pasos.

class EstadoAnalisisPerfil(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]  # 👈 sumo todos los mensajes sin perder contexto
    preferencias_usuario: Optional[dict]
    filtros_inferidos: Optional[dict]
    mensaje_validacion: Optional[str]
    pesos:              Optional[dict]  # soft‑weights normalizados


# 🧠 Respuestas binarios como texto plano: "sí", "no"
class PerfilUsuario(BaseModel):
    altura_mayor_190: Optional[str] = Field(description="¿El usuario mide más de 1.90 metros? Responde 'sí' o 'no'")
    peso_mayor_100: Optional[str] = Field(description="¿El usuario pesa más de 100 kg? Responde 'sí' o 'no'")
    uso_profesional: Optional[str] = Field(description="¿Usará el coche para trabajo? Responde 'sí' o 'no'")
    valora_estetica: Optional[str] = Field(description="¿Valora la estética del coche? Responde 'sí' o 'no'")
    solo_electricos: Optional[str] = Field(description="¿Quiere solo coches eléctricos? Responde 'sí' o 'no'")
    cambio_automatico: Optional[str] = Field(description="¿Quieres solo vehículos con cambio automático? Responde 'sí' o 'no'")
    apasionado_motor : Optional[str] = Field(description="¿Eres un apasionado/a del motor y/o la movilidad? Responde 'sí' o 'no'")
    aventura: Optional[NivelAventura] = Field(default=None,description="¿Qué nivel de aventura buscas con tu vehículo: 'ninguna', 'ocasional' o 'extrema'?")

    class Config:
        use_enum_values = True
        ignored_types = (NivelAventura,)


class FiltrosInferidos(BaseModel):
    batalla_min: Optional[int] = Field(
        description="Valor mínimo de batalla recomendado (rango: 1500 a 4490 mm). Relevante si el usuario mide más de 189 cm."
    )
    indice_altura_interior_min: Optional[int] = Field(
        description="Valor mínimo de índice de altura interior recomendado (rango: 1439 a 9200). Relevante si el usuario mide más de 189 cm."
    )
    # tipo_carroceria: Optional[List[TipoCarroceria]] = Field(
    #     description="Lista de carrocerías recomendadas, por ejemplo ['COMERCIAL']"
    # )
    estetica_min: Optional[float] = Field(
        description="Mínimo valor de estética recomendado (0.0 a 10.0)"
    )
    tipo_mecanica: Optional[List[TipoMecanica]] = Field(
        description="Lista de motorizaciones recomendadas"
    )
    premium_min: Optional[float] = Field(
        description="Mínimo valor de premium recomendado (0.0 a 10.0)"        
    )
    singular_min: Optional[float] = Field(
        description="Mínimo valor de singularidad recomendado (0.0 a 10.0)"
    )


class ResultadoPerfil(BaseModel):
    preferencias_usuario: PerfilUsuario
    filtros_inferidos: FiltrosInferidos
    mensaje_validacion: str



###PEDNIENTE HACER PRUEBAS CON ESTA REFACTORIZACION MEJORAS PARA USAR API REST
# class PerfilUsuario(BaseModel):
#     """
#     Preferencias personales extraídas del usuario.
#     Las respuestas son texto plano: "sí", "no" o "null" (como string).
#     """
#     altura_mayor_190: Optional[Literal["sí", "no", "null"]] = Field(description="¿El usuario mide más de 1.90 metros?")
#     peso_mayor_100: Optional[Literal["sí", "no", "null"]] = Field(description="¿El usuario pesa más de 100 kg?")
#     uso_profesional: Optional[Literal["sí", "no", "null"]] = Field(description="¿Usará el coche para trabajo?")
#     valora_estetica: Optional[Literal["sí", "no", "null"]] = Field(description="¿Valora la estética del coche?")
#     solo_electricos: Optional[Literal["sí", "no", "null"]] = Field(description="¿Quiere solo coches eléctricos?")
#     cambio_automatico: Optional[Literal["sí", "no", "null"]] = Field(description="¿Quiere solo vehículos con cambio automático?")
#     apasionado_motor: Optional[Literal["sí", "no", "null"]] = Field(description="¿Eres un apasionado/a del motor y/o la movilidad?")


# class FiltrosInferidos(BaseModel):
#     """
#     Filtros técnicos que ayudan a hacer match con la base de coches.
#     Estos son inferidos a partir de las preferencias.
#     """
#     batalla_min: Optional[int] = Field(
#         description="Valor mínimo de batalla recomendado (1500 - 4490 mm). Relevante si el usuario mide más de 189 cm."
#     )
#     indice_altura_interior_min: Optional[int] = Field(
#         description="Índice mínimo de altura interior recomendado (1439 - 9200). Relevante si el usuario mide más de 189 cm."
#     )
#     tipo_carroceria: Optional[List[TipoCarroceria]] = Field(
#         description="Lista de carrocerías recomendadas, por ejemplo ['SUV', 'MONOVOLUMEN']"
#     )
#     estetica_min: Optional[float] = Field(
#         description="Mínimo valor de estética recomendado (0.0 a 10.0)"
#     )
#     tipo_mecanica: Optional[List[TipoMecanica]] = Field(
#         description="Lista de motorizaciones recomendadas"
#     )
#     premium_min: Optional[float] = Field(
#         description="Mínimo valor de premium recomendado (0.0 a 10.0)"
#     )
#     singular_min: Optional[float] = Field(
#         description="Mínimo valor de singularidad recomendado (0.0 a 10.0)"
#     )


# class ResultadoPerfil(BaseModel):
#     """
#     Salida estructurada del LLM tras analizar el mensaje del usuario.
#     Incluye preferencias clave, filtros técnicos y un mensaje de validación.
#     """
#     preferencias_usuario: PerfilUsuario
#     filtros_inferidos: FiltrosInferidos
#     mensaje_validacion: str


# class EstadoAnalisisPerfil(TypedDict):
#     """
#     Estado compartido que fluye entre nodos en el grafo de LangGraph.
#     Guarda historial de mensajes, las preferencias del usuario y filtros inferidos.
#     """
#     messages: Annotated[List[BaseMessage], add_messages]
#     preferencias_usuario: Optional[dict]
#     filtros_inferidos: Optional[dict]
#     mensaje_validacion: Optional[str]


