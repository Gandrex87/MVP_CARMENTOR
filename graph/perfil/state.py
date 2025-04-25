from typing import TypedDict
from typing import List, Optional, Annotated, Literal
from langchain_core.messages import HumanMessage, BaseMessage,AIMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from utils.enums import Transmision, TipoMecanica, NivelAventura


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
    transmision_preferida: Optional[Transmision] = Field(default=None, description="¿Qué transmisión prefieres: automático, manual o ambos?")
    apasionado_motor : Optional[str] = Field(description="¿Eres un apasionado/a del motor y/o la movilidad? Responde 'sí' o 'no'")
    aventura: Optional[NivelAventura] = Field(default=None,description="¿Qué nivel de aventura buscas con tu vehículo: 'ninguna', 'ocasional' o 'extrema'?")

    class Config:
        use_enum_values = True
        ignored_types = (NivelAventura, Transmision)


class FiltrosInferidos(BaseModel):
    batalla_min: Optional[int] = Field(
        description="Valor mínimo de batalla recomendado (rango: 1500 a 4490 mm). Relevante si el usuario mide más de 189 cm."
    )
    indice_altura_interior_min: Optional[int] = Field(
        description="Valor mínimo de índice de altura interior recomendado (rango: 0.90 a 3.020). Relevante si el usuario mide más de 189 cm."
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

