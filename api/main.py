# main.py
from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid 
import logging
import os 
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage


# Cargar variables de entorno ANTES de cualquier import que las use
load_dotenv() 

# --- Configuración de Logging ---
logging.basicConfig(level=logging.DEBUG) #INFO PARA CUANDO PASE A PRODUCCION
logger = logging.getLogger(__name__) # Logger para este módulo

# --- Importaciones del Agente LangGraph ---
from graph.perfil.memory import ensure_tables_exist, set_checkpointer_instance
from graph.perfil.builder import build_sequential_agent_graph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# --- Variables Globales ---
car_mentor_graph = None
# Para gestionar el ciclo de vida del checkpointer persistente
_checkpointer_context_manager = None # Guardará el gestor de contexto
_persistent_checkpointer_instance = None # Guardará la instancia real del AsyncPostgresSaver

# --- Modelos Pydantic (sin cambios) ---
class Message(BaseModel): # ...
    type: str = Field(..., description="Tipo de mensaje: 'CarBlau_AI' o 'user'.")
    content: str = Field(..., description="Contenido textual del mensaje.")
class StartConversationRequest(BaseModel): # ...
    initial_message: Optional[str] = Field(None,description="Mensaje inicial opcional del usuario para empezar la conversación.")
class StartConversationResponse(BaseModel): # ...
    thread_id: str = Field(description="Identificador único para la nueva conversación.")
    agent_messages: List[Message] = Field(description="Lista de los primeros mensajes del agente.")
class UserMessageRequest(BaseModel): # ...
    content: str = Field(..., description="Contenido del mensaje del usuario.")
class AgentMessageResponse(BaseModel): # ...
    thread_id: str = Field(description="Identificador de la conversación.")
    agent_messages: List[Message] = Field(description="Lista de los mensajes de respuesta del agente.")

# --- Instancia de FastAPI ---
app = FastAPI(
    title="CarBlau Agent API",
    description="API para interactuar con el agente CarBlau y obtener recomendaciones de coches.",
    version="0.1.0"
)

# --- Evento de Startup ---
@app.on_event("startup")
async def startup_event():
    global car_mentor_graph, _checkpointer_context_manager, _persistent_checkpointer_instance
    logger.info("Ejecutando evento de startup de FastAPI para CarBlau Agent...")

     # 1. Cargar configuración de la base de datos
    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASSWORD")
    db_host = os.environ.get("DB_HOST")  # En Cloud Run será: /cloudsql/instance-connection-name
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME")

    if not all([db_user, db_password, db_host, db_name]):
        logger.error("CRÍTICO: Faltan variables de BBDD. El agente NO funcionará.")
        raise RuntimeError("Configuración de base de datos incompleta.")

    conn_string = ""
    # Detectar si estamos en el entorno de Cloud Run con un socket de Cloud SQL
    if db_host and db_host.startswith("/cloudsql/"):
        logger.info(f"Detectado socket de Cloud SQL en: {db_host}")
        # Para psycopg, la conexión a un socket Unix se especifica usando el parámetro 'host'.
        # El formato es una cadena de pares clave=valor (DSN), no una URL.
        conn_string = f"dbname='{db_name}' user='{db_user}' password='{db_password}' host='{db_host}'"
        logger.info(f"Cadena de conexión generada para Cloud SQL (formato DSN): dbname='{db_name}' user='{db_user}' password='******' host='{db_host}'")
    else:
        # Mantener la lógica original para conexiones locales/TCP (desarrollo)
        logger.info(f"Usando conexión TCP estándar a {db_host}:{db_port}")
        conn_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        logger.info(f"Cadena de conexión PostgreSQL (formato URL): {conn_string.replace(db_password, '******')}")


    try:
        # 2. Asegurar que las tablas del checkpointer existan
        logger.info("Verificando/creando tablas para el checkpointer...")
        await ensure_tables_exist(conn_string)
        logger.info("Tablas del checkpointer verificadas/creadas (vía ensure_tables_exist).")
        
        # 3. Crear el GESTOR DE CONTEXTO para AsyncPostgresSaver
        _checkpointer_context_manager = AsyncPostgresSaver.from_conn_string(conn_string)
        logger.info("Gestor de contexto AsyncPostgresSaver creado.")

        # 4. "Entrar" en el contexto para obtener la INSTANCIA REAL del saver
        #    Esto también abrirá la conexión a la base de datos.
        _persistent_checkpointer_instance = await _checkpointer_context_manager.__aenter__()
        logger.info("Instancia real de AsyncPostgresSaver obtenida (conexión a BD abierta).")

        # 5. Establecer la instancia REAL globalmente
        set_checkpointer_instance(_persistent_checkpointer_instance)
        logger.info("Instancia persistente de AsyncPostgresSaver configurada globalmente.")

        # 6. Construir y compilar el grafo
        logger.info("Compilando el grafo del agente CarBlau...")
        car_mentor_graph = build_sequential_agent_graph()
        logger.info("Grafo del agente CarBlau compilado y listo.")

    except ImportError as e:
        logger.error(f"CRÍTICO: Error de importación en startup: {e}.", exc_info=True)
        raise RuntimeError(f"Error de importación crítico: {e}")
    except Exception as e:
        logger.error(f"FALLO CRÍTICO en startup: {e}", exc_info=True)
        raise RuntimeError(f"No se pudo inicializar el agente: {e}")

# --- Endpoints (sin cambios en su lógica interna, solo dependen de que car_mentor_graph esté listo) ---
@app.get("/", tags=["root"])
async def read_root(): # ... (como antes)
    logger.info("Solicitud recibida en el endpoint raíz ('/').")
    return {"message": "¡Bienvenido a la API del Agente CarBlau!"}

@app.post("/conversation/start", response_model=StartConversationResponse, status_code=201, tags=["conversation"])
async def start_conversation(request_data: Optional[StartConversationRequest] = None): # ... (como antes)
    if not car_mentor_graph:
        logger.error("Intento de iniciar conversación, pero el grafo no está disponible (falló en startup).")
        raise HTTPException(status_code=503, detail="El servicio del agente no está disponible en este momento.")
    # ... (resto de la lógica del endpoint como en el Canvas anterior)
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    logger.info(f"Iniciando nueva conversación con thread_id: {thread_id}")
    initial_messages_for_graph: List[BaseMessage] = []
    if request_data and request_data.initial_message:
        initial_messages_for_graph.append(HumanMessage(content=request_data.initial_message))
    try:
        output = await car_mentor_graph.ainvoke({"messages": initial_messages_for_graph}, config=config)
        agent_response_messages: List[Message] = []
        if output and "messages" in output:
            start_index = len(initial_messages_for_graph)
            for msg in output["messages"][start_index:]:
                if isinstance(msg, AIMessage):
                    agent_response_messages.append(Message(type="CarBlau_AI", content=msg.content))
        if not agent_response_messages and not (request_data and request_data.initial_message):
            agent_response_messages.append(Message(type="CarBlau_AI", content="Hola, soy CarBlau. ¿Podrías indicarme tu código postal para comenzar?"))
        return StartConversationResponse(thread_id=thread_id, agent_messages=agent_response_messages)
    except Exception as e:
        logger.error(f"Error al invocar grafo en /start (thread_id: {thread_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.post("/conversation/{thread_id}/message", response_model=AgentMessageResponse, tags=["conversation"])
async def send_message(
    message_request: UserMessageRequest,
    thread_id: str = Path(..., min_length=36, max_length=36, regex=r"^[a-f0-9-]+$", 
                        description="El ID del hilo de la conversación existente (formato UUID).")
): # ... (como antes)
    if not car_mentor_graph:
        logger.error(f"Intento de mensaje a {thread_id}, pero grafo no disponible.")
        raise HTTPException(status_code=503, detail="El servicio del agente no está disponible.")
    if not message_request.content.strip():
        raise HTTPException(status_code=400, detail="El contenido del mensaje no puede estar vacío.")
    config = {"configurable": {"thread_id": thread_id}}
    logger.info(f"Continuando {thread_id}. Usuario: {message_request.content}")
    try:
        new_human_message = HumanMessage(content=message_request.content)
        output = await car_mentor_graph.ainvoke({"messages": [new_human_message]}, config=config)
        agent_response_messages: List[Message] = []
        if output and "messages" in output:
            temp_agent_msgs = []
            for msg in reversed(output["messages"]):
                if isinstance(msg, AIMessage): temp_agent_msgs.insert(0, Message(type="CarBlau_AI", content=msg.content))
                elif isinstance(msg, HumanMessage): break 
            agent_response_messages = temp_agent_msgs
        if not agent_response_messages: logger.warning(f"Agente no generó mensajes para {thread_id}.")
        return AgentMessageResponse(thread_id=thread_id, agent_messages=agent_response_messages)
    except Exception as e:
        logger.error(f"Error al invocar grafo en /message (thread_id: {thread_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/test", tags=["test"])
async def test_endpoint(): # ... (como antes)
    logger.info("Solicitud recibida en el endpoint de prueba ('/test').")
    return {"message": "¡El endpoint de prueba funciona correctamente!"}

# if __name__ == "__main__":
#     import uvicorn
#     # Asegúrate de que load_dotenv() se llame antes si ejecutas así
#     # uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) # reload=True para desarrollo
