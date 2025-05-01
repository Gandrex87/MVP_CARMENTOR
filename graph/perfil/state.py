from typing import TypedDict
from typing import List, Optional, Annotated, Literal
from langchain_core.messages import HumanMessage, BaseMessage,AIMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field, model_validator
from utils.enums import Transmision, TipoMecanica, NivelAventura
from typing import Literal, Optional


# 🧠 Modelos de Datos (PerfilUsuario, FiltrosInferidos, EconomiaUsuario): Estos modelos definen la información que quieres recopilar.
        
class PerfilUsuario(BaseModel):
    # Añadir default=None a todos los Optional que no lo tenían
    altura_mayor_190: Optional[str] = Field(default=None, description="¿El usuario mide más de 1.90 metros? Responde 'sí' o 'no'")
    peso_mayor_100: Optional[str] = Field(default=None, description="¿El usuario pesa más de 100 kg? Responde 'sí' o 'no'")
    uso_profesional: Optional[str] = Field(default=None, description="¿Usará el coche para trabajo? Responde 'sí' o 'no'")
    valora_estetica: Optional[str] = Field(default=None, description="¿Valora la estética del coche? Responde 'sí' o 'no'")
    solo_electricos: Optional[str] = Field(default=None, description="¿Quiere solo coches eléctricos? Responde 'sí' o 'no'")
    transmision_preferida: Optional[Transmision] = Field(default=None, description="¿Qué transmisión prefieres: automático, manual o ambos?")
    apasionado_motor : Optional[str] = Field(default=None, description="¿Eres un apasionado/a del motor y/o la movilidad? Responde 'sí' o 'no'")
    aventura: Optional[NivelAventura] = Field(default=None,description="¿Qué nivel de aventura buscas con tu vehículo: 'ninguna', 'ocasional' o 'extrema'?")
    
    # ConfigDict se mantiene igual (recuerda quitar ignored_types si no lo hiciste)
    class ConfigDict:
        use_enum_values = True

class FiltrosInferidos(BaseModel):
    batalla_min: Optional[float] = Field(default=None, description="Valor mínimo de batalla recomendado (rango: 1500.0 a 4490.0 mm). Relevante si el usuario mide más de 189 cm.")
    indice_altura_interior_min: Optional[float] = Field(default=None, description="Valor mínimo de índice de altura interior recomendado (rango: 0.90 a 3.020). Relevante si el usuario mide más de 189 cm.")
    estetica_min: Optional[float] = Field(default=None, description="Mínimo valor de estética recomendado (0.0 a 10.0)")
    tipo_mecanica: Optional[List[TipoMecanica]] = Field(default=None, description="Lista de motorizaciones recomendadas")
    premium_min: Optional[float] = Field(default=None, description="Mínimo valor de premium recomendado (0.0 a 10.0)")
    singular_min: Optional[float] = Field(default=None, description="Mínimo valor de singularidad recomendado (0.0 a 10.0)")
    tipo_carroceria: Optional[List[str]] = Field(default=None, description="Lista de tipos de carrocería recomendados por RAG (ej: ['SUV', 'COUPE'])")
    modo_adquisicion_recomendado: Optional[Literal['Contado', 'Financiado']] = Field(
        default=None,
        description="Modo de compra recomendado (Contado/Financiado) basado en análisis Modo 1."
    )
    precio_max_contado_recomendado: Optional[float] = Field(
        default=None,
        description="Precio máximo recomendado si se aconseja comprar al contado (Modo 1)."
    )
    cuota_max_calculada: Optional[float] = Field(
        default=None,
        description="Cuota mensual máxima calculada si se aconseja financiar (Modo 1)."
    )

#cuanta gana y aplicamos un % 60 /por porcentaje MODO 1 o 2 iNGRESO 
class EconomiaUsuario(BaseModel):
    modo:         Optional[Literal[1, 2]] = Field(default=None) # Añadir Field(default=None) por si acaso
    submodo:      Optional[Literal[1, 2]] = Field(default=None)
    ingresos:     Optional[float] = Field(default=None)
    ahorro:       Optional[float] = Field(default=None)
    pago_contado: Optional[float] = Field(default=None)
    cuota_max:    Optional[float] = Field(default=None)
    entrada:      Optional[float] = Field(default=None)
    anos_posesion: Optional[int] = Field(default=None, description="Número estimado de años que el usuario planea conservar el vehículo." )


# 🧠 Modelos de Salida (ResultadoEconomia, ResultadoSoloPerfil, ResultadoSoloFiltros): Estos modelos definen la salida esperada del LLM.
class ResultadoEconomia(BaseModel):
    economia: EconomiaUsuario = Field(description="Objeto que contiene TODA la información económica recopilada o actualizada.") 
    mensaje_validacion: str
    

class ResultadoSoloPerfil(BaseModel):
    """Salida esperada del LLM enfocado solo en el perfil del usuario."""
    preferencias_usuario: PerfilUsuario
    mensaje_validacion: str = Field(description="Pregunta de seguimiento CLARA y CORTA si falta información ESENCIAL para completar el PerfilUsuario, o un mensaje de confirmación si el perfil está completo.")

class ResultadoSoloFiltros(BaseModel):
    """Salida esperada del LLM enfocado solo en inferir filtros técnicos."""
    filtros_inferidos: FiltrosInferidos
    mensaje_validacion: str = Field(description="Pregunta de seguimiento CLARA y CORTA si falta información ESENCIAL para completar los FiltrosInferidos (ej: tipo_mecanica), o un mensaje de confirmación si los filtros están completos.")

    
#ES el contenedor general que acumula toda la información a lo largo de la ejecución del grafo.
class EstadoAnalisisPerfil(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]  # 👈 sumo todos los mensajes sin perder contexto
    preferencias_usuario: Optional[PerfilUsuario]
    filtros_inferidos: Optional[FiltrosInferidos]
    economia: Optional[EconomiaUsuario]          # ← nuevo canal para la rama económica
    mensaje_validacion: Optional[str]
    pesos:              Optional[dict]  # soft‑weights normalizados
    pregunta_pendiente: Optional[str] # Para guardar la pregunta entre nodos

