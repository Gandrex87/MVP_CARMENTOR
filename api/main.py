# main.py
from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
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


# # Cargar variables de entorno ANTES de cualquier import que las use
# load_dotenv() 

# # --- Configuración de Logging ---
# logging.basicConfig(level=logging.DEBUG) #INFO PARA CUANDO PASE A PRODUCCION
# logger = logging.getLogger(__name__) # Logger para este módulo

# # --- Variables Globales ---
# car_mentor_graph = None
# # Para gestionar el ciclo de vida del checkpointer persistente
# _checkpointer_context_manager = None # Guardará el gestor de contexto
# _persistent_checkpointer_instance = None # Guardará la instancia real del AsyncPostgresSaver

# # --- Modelos Pydantic (sin cambios) ---
# class Message(BaseModel): # ...
#     type: str = Field(..., description="Tipo de mensaje: 'CarBlau_AI' o 'user'.")
#     content: str = Field(..., description="Contenido textual del mensaje.")
# class StartConversationRequest(BaseModel): # ...
#     initial_message: Optional[str] = Field(None,description="Mensaje inicial opcional del usuario para empezar la conversación.")
# class StartConversationResponse(BaseModel): # ...
#     thread_id: str = Field(description="Identificador único para la nueva conversación.")
#     agent_messages: List[Message] = Field(description="Lista de los primeros mensajes del agente.")
# class UserMessageRequest(BaseModel): # ...
#     content: str = Field(..., description="Contenido del mensaje del usuario.")
# class AgentMessageResponse(BaseModel): # ...
#     thread_id: str = Field(description="Identificador de la conversación.")
#     agent_messages: List[Message] = Field(description="Lista de los mensajes de respuesta del agente.")

# # --- Instancia de FastAPI ---
# app = FastAPI(
#     title="CarBlau Agent API",
#     description="API para interactuar con el agente CarBlau y obtener recomendaciones de coches.",
#     version="0.2.0"
# )

# # --- AÑADIR MIDDLEWARE DE CORS ---
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Para producción, considera limitarlo a tu dominio de frontend
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# # --- Evento de Startup ---
# @app.on_event("startup")
# async def startup_event():
#     global car_mentor_graph, _checkpointer_context_manager, _persistent_checkpointer_instance
#     logger.info("Ejecutando evento de startup de FastAPI para CarBlau Agent...")
#     start_time = time.time()
#     logger.info(f"[TIMING] STARTUP: Evento de startup iniciado en t={time.time() - start_time:.2f}s")

#      # 1. Cargar configuración de la base de datos
#     db_user = os.environ.get("DB_USER")
#     db_password = os.environ.get("DB_PASSWORD")
#     db_host = os.environ.get("DB_HOST")  # En Cloud Run será: /cloudsql/instance-connection-name
#     db_port = os.environ.get("DB_PORT", "5432")
#     db_name = os.environ.get("DB_NAME")
#     logger.info(f"[TIMING] STARTUP: Variables de BBDD cargadas en t={time.time() - start_time:.2f}s")
    
#     if not all([db_user, db_password, db_host, db_name]):
#         logger.error("CRÍTICO: Faltan variables de BBDD. El agente NO funcionará.")
#         raise RuntimeError("Configuración de base de datos incompleta.")

#     conn_string = ""
#     # Detectar si estamos en el entorno de Cloud Run con un socket de Cloud SQL
#     if db_host and db_host.startswith("/cloudsql/"):
#         logger.info(f"Detectado socket de Cloud SQL en: {db_host}")
#         # Para psycopg, la conexión a un socket Unix se especifica usando el parámetro 'host'.
#         # El formato es una cadena de pares clave=valor (DSN), no una URL.
#         conn_string = f"dbname='{db_name}' user='{db_user}' password='{db_password}' host='{db_host}'"
#         logger.info(f"Cadena de conexión generada para Cloud SQL (formato DSN): dbname='{db_name}' user='{db_user}' password='******' host='{db_host}'")
#     else:
#         # Mantener la lógica original para conexiones locales/TCP (desarrollo)
#         logger.info(f"Usando conexión TCP estándar a {db_host}:{db_port}")
#         conn_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
#         logger.info(f"Cadena de conexión PostgreSQL (formato URL): {conn_string.replace(db_password, '******')}")
    
#     logger.info(f"[TIMING] STARTUP: Cadena de conexión construida en t={time.time() - start_time:.2f}s")

#     try:
#         # 2. Asegurar que las tablas del checkpointer existan
#         logger.info("Verificando/creando tablas para el checkpointer...")
#         logger.info(f"[TIMING] STARTUP: Llamando a ensure_tables_exist... en t={time.time() - start_time:.2f}s")
#         await ensure_tables_exist(conn_string)
#         logger.info("Tablas del checkpointer verificadas/creadas (vía ensure_tables_exist).")
#         logger.info(f"[TIMING] STARTUP: ensure_tables_exist completado en t={time.time() - start_time:.2f}s")
        
#         # 3. Crear el GESTOR DE CONTEXTO para AsyncPostgresSaver
#         _checkpointer_context_manager = AsyncPostgresSaver.from_conn_string(conn_string)
#         logger.info("Gestor de contexto AsyncPostgresSaver creado.")
#         logger.info(f"[TIMING] STARTUP: Gestor de contexto AsyncPostgresSaver creado en t={time.time() - start_time:.2f}s")

#         # 4. "Entrar" en el contexto para obtener la INSTANCIA REAL del saver
#         #    Esto también abrirá la conexión a la base de datos.
#         _persistent_checkpointer_instance = await _checkpointer_context_manager.__aenter__()
#         logger.info("Instancia real de AsyncPostgresSaver obtenida (conexión a BD abierta).")
#         logger.info(f"[TIMING] STARTUP: Instancia de AsyncPostgresSaver obtenida en t={time.time() - start_time:.2f}s")


#         # 5. Establecer la instancia REAL globalmente
#         set_checkpointer_instance(_persistent_checkpointer_instance)
#         logger.info("Instancia persistente de AsyncPostgresSaver configurada globalmente.")
#         logger.info(f"[TIMING] STARTUP: Instancia configurada globalmente en t={time.time() - start_time:.2f}s")

#         # 6. Construir y compilar el grafo
#         logger.info("Compilando el grafo del agente CarBlau...")
#         car_mentor_graph = build_sequential_agent_graph()
#         logger.info("Grafo del agente CarBlau compilado y listo.")

#     except ImportError as e:
#         logger.error(f"CRÍTICO: Error de importación en startup: {e}.", exc_info=True)
#         raise RuntimeError(f"Error de importación crítico: {e}")
#     except Exception as e:
#         logger.error(f"FALLO CRÍTICO en startup: {e}", exc_info=True)
#         raise RuntimeError(f"No se pudo inicializar el agente: {e}")
#     logger.info(f"[TIMING] STARTUP: ¡EVENTO DE STARTUP COMPLETADO EXITOSAMENTE en t={time.time() - start_time:.2f}s!")

# # --- AÑADIR EVENTO DE SHUTDOWN ---
# @app.on_event("shutdown")
# async def shutdown_event():
#     global _checkpointer_context_manager
#     logger.info("Ejecutando evento de shutdown de FastAPI...")
#     if _checkpointer_context_manager:
#         # Llama al método de salida del contexto para cerrar la conexión
#         await _checkpointer_context_manager.__aexit__(None, None, None)
#         logger.info("Conexión del checkpointer de la base de datos cerrada correctamente.")
#     logger.info("Shutdown completo.")

# # --- Endpoints (sin cambios en su lógica interna, solo dependen de que car_mentor_graph esté listo) ---
# @app.get("/", tags=["root"])
# async def read_root(): # ... (como antes)
#     logger.info("Solicitud recibida en el endpoint raíz ('/').")
#     return {"message": "¡Bienvenido a la API del Agente CarBlau!"}

# @app.post("/conversation/start", response_model=StartConversationResponse, status_code=201, tags=["conversation"])
# async def start_conversation(request_data: Optional[StartConversationRequest] = None): # ... (como antes)
#     if not car_mentor_graph:
#         logger.error("Intento de iniciar conversación, pero el grafo no está disponible (falló en startup).")
#         raise HTTPException(status_code=503, detail="El servicio del agente no está disponible en este momento.")
#     # ... (resto de la lógica del endpoint como en el Canvas anterior)
#     thread_id = str(uuid.uuid4())
#     config = {"configurable": {"thread_id": thread_id}}
#     logger.info(f"Iniciando nueva conversación con thread_id: {thread_id}")
#     initial_messages_for_graph: List[BaseMessage] = []
#     if request_data and request_data.initial_message:
#         initial_messages_for_graph.append(HumanMessage(content=request_data.initial_message))
#     try:
#         output = await car_mentor_graph.ainvoke({"messages": initial_messages_for_graph}, config=config)
#         agent_response_messages: List[Message] = []
#         if output and "messages" in output:
#             start_index = len(initial_messages_for_graph)
#             for msg in output["messages"][start_index:]:
#                 if isinstance(msg, AIMessage):
#                     agent_response_messages.append(Message(type="CarBlau_AI", content=msg.content))
#         if not agent_response_messages and not (request_data and request_data.initial_message):
#             agent_response_messages.append(Message(type="CarBlau_AI", content="Hola, soy CarBlau. ¿Podrías indicarme tu código postal para comenzar?"))
#         return StartConversationResponse(thread_id=thread_id, agent_messages=agent_response_messages)
#     except Exception as e:
#         logger.error(f"Error al invocar grafo en /start (thread_id: {thread_id}): {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# @app.post("/conversation/{thread_id}/message", response_model=AgentMessageResponse, tags=["conversation"])
# async def send_message(
#     message_request: UserMessageRequest,
#     thread_id: str = Path(..., min_length=36, max_length=36, regex=r"^[a-f0-9-]+$", 
#                         description="El ID del hilo de la conversación existente (formato UUID).")
# ): # ... (como antes)
#     if not car_mentor_graph:
#         logger.error(f"Intento de mensaje a {thread_id}, pero grafo no disponible.")
#         #raise HTTPException(status_code=503, detail="El servicio del agente no está disponible.")
#         raise HTTPException(status_code=HTTPStatus.SERVICE_UNAVAILABLE, detail="El servicio del agente no está disponible")
#     if not message_request.content.strip():
#         raise HTTPException(status_code=400, detail="El contenido del mensaje no puede estar vacío.")
#     config = {"configurable": {"thread_id": thread_id}}
#     logger.info(f"Continuando {thread_id}. Usuario: {message_request.content}")
#     try:
#         new_human_message = HumanMessage(content=message_request.content)
#         output = await car_mentor_graph.ainvoke({"messages": [new_human_message]}, config=config)
#         agent_response_messages: List[Message] = []
#         if output and "messages" in output:
#             temp_agent_msgs = []
#             for msg in reversed(output["messages"]):
#                 if isinstance(msg, AIMessage): temp_agent_msgs.insert(0, Message(type="CarBlau_AI", content=msg.content))
#                 elif isinstance(msg, HumanMessage): break 
#             agent_response_messages = temp_agent_msgs
#         if not agent_response_messages: logger.warning(f"Agente no generó mensajes para {thread_id}.")
#         return AgentMessageResponse(thread_id=thread_id, agent_messages=agent_response_messages)
#     except Exception as e:
#         logger.error(f"Error al invocar grafo en /message (thread_id: {thread_id}): {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# @app.get("/test", tags=["test"])
# async def test_endpoint(): # ... (como antes)
#     logger.info("Solicitud recibida en el endpoint de prueba ('/test').")
#     return {"message": "¡El endpoint de prueba funciona correctamente!"}

# # if __name__ == "__main__":
# #     import uvicorn
# #     # Asegúrate de que load_dotenv() se llame antes si ejecutas así
# #     # uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) # reload=True para desarrollo


# Cargar variables de entorno ANTES de cualquier import que las use
load_dotenv() 




# --- Variables Globales ---
car_mentor_graph = None
_checkpointer_context_manager = None
_persistent_checkpointer_instance = None

# --- Modelos Pydantic para la API ---
# Modelo para un único mensaje en la conversación
class Message(BaseModel):
    id: Optional[str] = Field(None, description="ID único del mensaje, opcional.")
    role: str = Field(..., description="Rol del emisor: 'user' o 'agent'.")
    content: str = Field(..., description="Contenido textual del mensaje.")

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
    version="0.1.3"
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
    # ... (Tu lógica de startup para la BBDD y el grafo se mantiene igual, es correcta)
    # ... (Omitido por brevedad, pero debe estar aquí)
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
        # Invocamos el grafo sin mensajes para obtener la primera pregunta
        output = await car_mentor_graph.ainvoke({"messages": []}, config=config)
        
        agent_response_messages: List[Message] = []
        if output and "messages" in output:
            for msg in output["messages"]:
                if isinstance(msg, AIMessage):
                    agent_response_messages.append(Message(role="agent", content=msg.content))
        
        # ✅ CORREGIDO: El return ahora usa la clave 'messages' que el frontend espera.
        return StartConversationResponse(thread_id=thread_id, messages=agent_response_messages)
    except Exception as e:
        logger.error(f"Error al invocar grafo en /start (thread_id: {thread_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del agente: {str(e)}")


# ✅ CORREGIDO: La función ahora espera el modelo UserMessageRequest que contiene una lista.
@app.post("/conversation/{thread_id}/message", response_model=AgentMessageResponse, tags=["conversation"])
async def send_message(
    message_request: UserMessageRequest,
    thread_id: str = Path(...)
):
    if not car_mentor_graph:
        raise HTTPException(status_code=HTTPStatus.SERVICE_UNAVAILABLE, detail="El servicio del agente no está disponible.")
    
    # ✅ CORREGIDO: Extraemos el contenido del primer mensaje de la lista.
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
            # Devolvemos el historial completo para mantener el frontend sincronizado
            for msg in output["messages"]:
                 agent_response_messages.append(Message(
                     id=msg.id, 
                     role="agent" if isinstance(msg, AIMessage) else "user", 
                     content=msg.content
                ))

        return AgentMessageResponse(thread_id=thread_id, messages=agent_response_messages)
    except Exception as e:
        logger.error(f"Error al invocar grafo en /message (thread_id: {thread_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del agente: {str(e)}")
