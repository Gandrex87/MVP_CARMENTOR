# # main.py

import uuid
import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Importaciones del Agente LangGraph (Ajusta las rutas según tu proyecto) ---
try:
    from graph.perfil.builder import build_sequential_agent_graph
    from graph.perfil.memory import get_memory  # Por si necesitas el checkpointer más adelante

    logger.info("Construyendo el grafo del agente CarBlau...")
    car_mentor_graph = build_sequential_agent_graph()
    logger.info("¡Grafo del agente CarBlau construido exitosamente!")

except ImportError as e:
    logger.error(
        f"Error al importar componentes del agente LangGraph: {e}. "
        "Asegúrate de que las rutas sean correctas."
    )
    car_mentor_graph = None

except Exception as e_graph:
    logger.error(f"Error al construir el grafo del agente LangGraph: {e_graph}")
    car_mentor_graph = None


# --- Modelos Pydantic para las Solicitudes y Respuestas de la API ---

class Message(BaseModel):
    type: str = Field(..., description="Tipo de mensaje: 'ai' o 'user'.")
    content: str = Field(..., description="Contenido textual del mensaje.")


class StartConversationRequest(BaseModel):
    initial_message: Optional[str] = Field(
        None,
        description="Mensaje inicial opcional del usuario para empezar la conversación."
    )


class StartConversationResponse(BaseModel):
    thread_id: str = Field(description="Identificador único para la nueva conversación.")
    agent_messages: List[Message] = Field(description="Lista de los primeros mensajes del agente.")


class UserMessageRequest(BaseModel):
    content: str = Field(..., description="Contenido del mensaje del usuario.")


class AgentMessageResponse(BaseModel):
    thread_id: str = Field(description="Identificador de la conversación.")
    agent_messages: List[Message] = Field(description="Lista de los mensajes de respuesta del agente.")


# --- Instancia de FastAPI ---

app = FastAPI(
    title="CarBlau Agent API",
    description="API para interactuar con el agente CarBlau y obtener recomendaciones de coches.",
    version="0.1.0"
)

# (Opcional) Si necesitas CORS CORS (Cross-Origin Resource Sharing) es un mecanismo de seguridad que los navegadores implementan para controlar qué orígenes (dominios) están autorizados a hacer peticiones a tu servidor:
# from fastapi.middleware.cors import CORSMiddleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


@app.get("/", tags=["root"])
async def read_root():
    """
    Endpoint raíz que devuelve un mensaje de bienvenida.
    """
    logger.info("Solicitud recibida en el endpoint raíz ('/').")
    return {"message": "¡Bienvenido a la API del Agente CarBlau!"}


@app.post(
    "/conversation/start",
    response_model=StartConversationResponse,
    tags=["conversation"]
)
async def start_conversation(request_data: StartConversationRequest = None):
    """
    Inicia una nueva conversación con el agente CarBlau.
    Devuelve un ID de hilo (thread_id) y el primer mensaje del agente.
    """
    if not car_mentor_graph:
        logger.error("Intento de iniciar conversación, pero el grafo no está disponible.")
        raise HTTPException(
            status_code=503,
            detail="El servicio del agente no está disponible en este momento."
        )

    # Generar un ID único para la conversación
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    logger.info(f"Iniciando nueva conversación con thread_id: {thread_id}")

    # Construir lista inicial de mensajes (puede estar vacía)
    initial_messages: List[BaseMessage] = []
    if request_data and request_data.initial_message:
        logger.info(
            f"Mensaje inicial del usuario para thread_id {thread_id}: "
            f"{request_data.initial_message}"
        )
        initial_messages.append(HumanMessage(content=request_data.initial_message))

    try:
        # Llamada asíncrona al grafo
        output = await car_mentor_graph.ainvoke(
            {"messages": initial_messages},
            config=config
        )

        agent_response_messages: List[Message] = []
        if output and "messages" in output:
            # Solo devolvemos los AIMessage generados en este primer turno
            start_index = len(initial_messages)
            for msg in output["messages"][start_index:]:
                if isinstance(msg, AIMessage):
                    agent_response_messages.append(
                        Message(type="CarBlau_AI", content=msg.content)
                    )

        if not agent_response_messages:
            # Si el agente no generó respuesta en este punto, devolvemos un fallback
            logger.warning(f"El agente no generó mensajes iniciales para thread_id: {thread_id}")
            agent_response_messages.append(
                Message(type="CarBlau_AI", content="Lo siento, ha ocurrido un error al generar la respuesta inicial.")
            )

        logger.info(
            f"Conversación iniciada para thread_id: {thread_id}. Mensajes del agente: "
            f"{len(agent_response_messages)}"
        )
        return StartConversationResponse(
            thread_id=thread_id,
            agent_messages=agent_response_messages
        )

    except Exception as e:
        logger.error(
            f"Error al invocar el grafo para iniciar conversación (thread_id: {thread_id}): {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al procesar la solicitud: {str(e)}"
        )


@app.post(
    "/conversation/{thread_id}/message",
    response_model=AgentMessageResponse,
    tags=["conversation"]
)
async def send_message(
    message_request: UserMessageRequest,
    thread_id: str = Path(..., description="El ID del hilo de la conversación existente.")
):
    """
    Envía un mensaje de usuario a una conversación existente y obtiene la respuesta del agente.
    """
    if not car_mentor_graph:
        logger.error(
            f"Intento de enviar mensaje a thread_id {thread_id}, "
            "pero el grafo no está disponible."
        )
        raise HTTPException(
            status_code=503,
            detail="El servicio del agente no está disponible en este momento."
        )

    # El Body (message_request) ya fue validado por FastAPI: si falta `content`, se devuelve 422.
    if not message_request.content.strip():
        logger.warning(
            f"Solicitud a /conversation/{thread_id}/message con contenido vacío."
        )
        raise HTTPException(
            status_code=400,
            detail="El contenido del mensaje no puede estar vacío."
        )

    config = {"configurable": {"thread_id": thread_id}}
    logger.info(
        f"Continuando conversación con thread_id: {thread_id}. "
        f"Mensaje del usuario: {message_request.content}"
    )

    try:
        new_human_message = HumanMessage(content=message_request.content)

        # Llamada asíncrona al grafo
        output = await car_mentor_graph.ainvoke(
            {"messages": [new_human_message]},
            config=config
        )

        agent_response_messages: List[Message] = []

        if output and "messages" in output:
            # Buscamos la posición del HumanMessage que acabamos de enviar
            last_human_index = -1
            for idx, msg in enumerate(output["messages"]):
                if isinstance(msg, HumanMessage) and msg.content == new_human_message.content:
                    last_human_index = idx

            # Si encontramos nuestro HumanMessage, tomamos los AIMessage posteriores
            if last_human_index != -1:
                for msg in output["messages"][last_human_index + 1:]:
                    if isinstance(msg, AIMessage):
                        agent_response_messages.append(
                            Message(type="CarBlau_AI", content=msg.content)
                        )

            # Si no encontramos el index (caso raro), devolvemos todos los AIMessage finales
            if last_human_index == -1:
                for msg in reversed(output["messages"]):
                    if isinstance(msg, AIMessage):
                        agent_response_messages.insert(
                            0, Message(type="CarBlau_AI", content=msg.content)
                        )
                    elif isinstance(msg, HumanMessage):
                        break

            if not agent_response_messages:
                logger.warning(
                    f"El agente no generó nuevos mensajes para thread_id: {thread_id} tras el input del usuario."
                )

        logger.info(
            f"Respuesta del agente para thread_id: {thread_id}. "
            f"Mensajes: {len(agent_response_messages)}"
        )
        return AgentMessageResponse(
            thread_id=thread_id,
            agent_messages=agent_response_messages
        )

    except Exception as e:
        logger.error(
            f"Error al invocar el grafo para continuar conversación (thread_id: {thread_id}): {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al procesar la solicitud: {str(e)}"
        )


@app.get("/test", tags=["test"])
async def test_endpoint():
    """
    Endpoint de prueba para verificar que el servidor está operativo.
    """
    logger.info("Solicitud recibida en el endpoint de prueba ('/test').")
    return {"message": "¡El endpoint de prueba funciona correctamente!"}
