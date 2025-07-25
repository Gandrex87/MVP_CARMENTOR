# main.py
from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict
import uuid
from http import HTTPStatus
import time
import logging
import os 
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from fastapi.middleware.cors import CORSMiddleware
# --- Importaciones del Agente LangGraph ---
from graph.perfil.memory import ensure_tables_exist, set_checkpointer_instance
from graph.perfil.builder import build_sequential_agent_graph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# --- Configuración de Logging ---
# En producción, considera cambiar level=logging.INFO
logging.basicConfig(level=logging.DEBUG) 
logger = logging.getLogger(__name__)

# Cargar variables de entorno ANTES de cualquier import que las use
load_dotenv() 


# --- Variables Globales ---
car_mentor_graph = None
_checkpointer_context_manager = None
_persistent_checkpointer_instance = None
# --- 1. Definimos los modelos para la respuesta estructurada ---

class Car(BaseModel):
    """Define la estructura de un único coche en la recomendación."""
    name: str
    specs: List[str]
    imageUrl: Optional[str] = None
    price: str
    score: str
    analysis: str

class CarRecommendationPayload(BaseModel):
    """Define el objeto completo de la recomendación de coches."""
    type: str = "car_recommendation"
    introText: str
    cars: List[Car]
    
# ✅ MODELO MODIFICADO: Ahora el tipo de payload es explícito
class MessagePayload(BaseModel):
    payload: Optional[CarRecommendationPayload] = None
    


class Message(BaseModel):
    id: Optional[str] = Field(None, description="ID único del mensaje, opcional.")
    role: str
    content: str = Field(..., description="Rol del emisor: 'user' o 'agent'.")
    # Añadimos el campo para los datos estructurados
    additional_kwargs: Optional[MessagePayload] = Field(None, alias="additional_kwargs")

# ✅ CORREGIDO: Modelo de respuesta para /start
# La clave ahora es 'messages' para coincidir con el frontend.
class StartConversationResponse(BaseModel):
    thread_id: str = Field(description="Identificador único para la nueva conversación.")
    messages: List[Message] = Field(description="Lista de los primeros mensajes del agente.")


# ✅ CORREGIDO: Modelo de petición para /message
# Ahora espera un objeto que contiene una lista de mensajes, como lo envía el frontend.
class UserMessageRequest(BaseModel):
    messages: List[Message]

# Modelo de respuesta para /message
class AgentMessageResponse(BaseModel):
    thread_id: str = Field(description="Identificador de la conversación.")
    messages: List[Message] = Field(description="Lista de los mensajes de respuesta del agente.")

# --- Instancia de FastAPI ---
app = FastAPI(
    title="CarBlau Agent API",
    description="API para interactuar con el agente CarBlau y obtener recomendaciones de coches.",
    version="0.2.0"
)

# --- Middleware de CORS ---
# Permite que tu frontend (ej. localhost:3000) se comunique con esta API.
app.add_middleware(
    CORSMiddleware,
    # ✅ IMPORTANTE: Para producción, reemplaza "*" por la URL de tu frontend.
    #allow_origins=["http://localhost:3000", "http://localhost:5173", "*"], 
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Eventos de Startup y Shutdown ---
@app.on_event("startup")
async def startup_event():
    global car_mentor_graph, _checkpointer_context_manager, _persistent_checkpointer_instance
    logger.info("Ejecutando evento de startup de FastAPI para CarBlau Agent...")
    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASSWORD")
    db_host = os.environ.get("DB_HOST")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME")
    
    if not all([db_user, db_password, db_host, db_name]):
        raise RuntimeError("Configuración de base de datos incompleta.")

    conn_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    if db_host.startswith("/cloudsql/"):
        conn_string = f"dbname='{db_name}' user='{db_user}' password='{db_password}' host='{db_host}'"

    await ensure_tables_exist(conn_string)
    _checkpointer_context_manager = AsyncPostgresSaver.from_conn_string(conn_string)
    _persistent_checkpointer_instance = await _checkpointer_context_manager.__aenter__()
    set_checkpointer_instance(_persistent_checkpointer_instance)
    car_mentor_graph = build_sequential_agent_graph()
    logger.info("¡EVENTO DE STARTUP COMPLETADO EXITOSAMENTE!")

@app.on_event("shutdown")
async def shutdown_event():
    # ... (Tu lógica de shutdown se mantiene igual, es correcta)
    if _checkpointer_context_manager:
        await _checkpointer_context_manager.__aexit__(None, None, None)
        logger.info("Conexión del checkpointer cerrada.")

# --- Endpoints de la API ---
@app.get("/", tags=["root"])
async def read_root():
    return {"message": "¡Bienvenido a la API del Agente CarBlau!"}


@app.get("/test", tags=["test"])
async def test_endpoint(): # ... (como antes)
    logger.info("Solicitud recibida en el endpoint de prueba ('/test').")

# ✅ CORREGIDO: La ruta ahora es /start para coincidir con el frontend.
@app.post("/start", response_model=StartConversationResponse, status_code=201, tags=["conversation"])
async def start_conversation():
    if not car_mentor_graph:
        raise HTTPException(status_code=503, detail="El servicio del agente no está disponible.")
    
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    logger.info(f"Iniciando nueva conversación con thread_id: {thread_id}")

    try:
        output = await car_mentor_graph.ainvoke({"messages": []}, config=config)
        
        agent_response_messages: List[Message] = []
        if output and "messages" in output:
            for msg in output["messages"]:
                # Usamos la misma lógica robusta de conversión aquí
                message_data = {
                    "id": msg.id,
                    "role": "agent" if isinstance(msg, AIMessage) else "user",
                    "content": msg.content
                }
                if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
                    message_data["additional_kwargs"] = msg.additional_kwargs
                agent_response_messages.append(Message(**message_data))
        
        return StartConversationResponse(thread_id=thread_id, messages=agent_response_messages)
    except Exception as e:
        logger.error(f"Error al invocar grafo en /start: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del agente: {str(e)}")

@app.post("/conversation/{thread_id}/message", response_model=AgentMessageResponse, tags=["conversation"])
async def send_message(
    message_request: UserMessageRequest,
    thread_id: str = Path(...)
):
    if not car_mentor_graph:
        raise HTTPException(status_code=HTTPStatus.SERVICE_UNAVAILABLE, detail="El servicio del agente no está disponible.")
    
    if not message_request.messages or not message_request.messages[0].content.strip():
        raise HTTPException(status_code=400, detail="El contenido del mensaje no puede estar vacío.")
    
    user_content = message_request.messages[0].content
    config = {"configurable": {"thread_id": thread_id}}
    logger.info(f"Continuando {thread_id}. Usuario: {user_content}")
    
    try:
        new_human_message = HumanMessage(content=user_content)
        output = await car_mentor_graph.ainvoke({"messages": [new_human_message]}, config=config)
        
        agent_response_messages: List[Message] = []
        if output and "messages" in output:
            # ✅ INICIO DE LA LÓGICA DE CONVERSIÓN CORREGIDA
            for msg in output["messages"]:
                message_data = {
                    "id": msg.id,
                    "role": "agent" if isinstance(msg, AIMessage) else "user",
                    "content": msg.content
                }
                
                # Comprobamos si el mensaje tiene 'additional_kwargs' y no es nulo
                if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
                    # Si los tiene, los añadimos al diccionario.
                    message_data["additional_kwargs"] = msg.additional_kwargs

                # Creamos la instancia del modelo Pydantic a partir del diccionario
                agent_response_messages.append(Message(**message_data))
            # ✅ FIN DE LA LÓGICA DE CONVERSIÓN

        return AgentMessageResponse(thread_id=thread_id, messages=agent_response_messages)
    except Exception as e:
        logger.error(f"Error al invocar grafo en /message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del agente: {str(e)}")


# @app.post("/conversation/{thread_id}/message", response_model=AgentMessageResponse, tags=["conversation"])
# async def send_message(
#     message_request: UserMessageRequest,
#     thread_id: str = Path(...)
# ):
#     if not car_mentor_graph:
#         raise HTTPException(status_code=HTTPStatus.SERVICE_UNAVAILABLE, detail="El servicio del agente no está disponible.")
    
#     if not message_request.messages or not message_request.messages[0].content.strip():
#         raise HTTPException(status_code=400, detail="El contenido del mensaje no puede estar vacío.")
    
#     user_content = message_request.messages[0].content
    
#     # ==============================================================================
#     # ▼▼▼ INICIO DE LA LÓGICA MODIFICADA ▼▼▼
#     # ==============================================================================
    
#     # 1. Construimos el "config maestro" que incluye las interrupciones.
#     config = {
#         "configurable": {"thread_id": thread_id},
#         "interrupt_after": [
#             "generar_mensaje_transicion_perfil",
#             "generar_mensaje_transicion_pasajeros"
#         ]
#     }
    
#     logger.info(f"Continuando {thread_id}. Usuario: '{user_content}'. Usando config con interrupciones.")
    
#     try:
#         # 2. Invocamos el grafo con el mensaje del usuario.
#         #    El grafo se ejecutará hasta que termine o encuentre una interrupción.
#         new_human_message = HumanMessage(content=user_content)
#         output = await car_mentor_graph.ainvoke({"messages": [new_human_message]}, config=config)
        
#         # 3. Comprobación de continuación: Si el grafo se detuvo, lo continuamos UNA VEZ.
#         #    Esto es más seguro que un bucle 'while' en un entorno async como FastAPI.
#         current_state = await car_mentor_graph.get_state(config)
#         if current_state.next:
#             logger.info(f"Grafo interrumpido en {thread_id}. Continuando ejecución para finalizar el turno...")
#             output = await car_mentor_graph.ainvoke(None, config=config)

#         # 4. Procesamos la salida FINAL, que ahora contiene TODOS los mensajes generados.
#         agent_response_messages: List[Message] = []
#         if output and "messages" in output:
#             for msg in output["messages"]:
#                 message_data = {
#                     "id": msg.id,
#                     "role": "agent" if isinstance(msg, AIMessage) else "user",
#                     "content": msg.content
#                 }
#                 if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
#                     message_data["additional_kwargs"] = msg.additional_kwargs
#                 agent_response_messages.append(Message(**message_data))

#         # El frontend recibirá la lista completa de mensajes, incluyendo la transición
#         # y la siguiente pregunta, y podrá mostrarlos.
#         return AgentMessageResponse(thread_id=thread_id, messages=agent_response_messages)
    
#     except Exception as e:
#         logger.error(f"Error al invocar grafo en /message: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Error interno del agente: {str(e)}")

#     # ==============================================================================
#     # ▲▲▲ FIN DE LA LÓGICA MODIFICADA ▲▲▲
#     # ==============================================================================