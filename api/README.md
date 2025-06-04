# CarMentor Agent API

## Descripción

Esta API proporciona acceso a CarMentor, un agente de IA conversacional diseñado para ayudar a los usuarios a encontrar recomendaciones de coches personalizadas. El agente guía al usuario a través de varias etapas para perfilar sus necesidades y preferencias antes de ofrecer sugerencias.

La API está construida con FastAPI y utiliza LangGraph para orquestar la lógica del agente. Una característica clave es su capacidad para recordar el progreso de la conversación utilizando un sistema de memoria persistente implementado con PostgreSQL.

## Tech Stack

* **Python:** (Especifica tu versión, ej: 3.11+)
* **FastAPI:** Para construir la API web.
* **LangGraph:** Para definir y ejecutar el flujo conversacional del agente.
* **Pydantic:** Para la validación de datos de la API.
* **PostgreSQL:** Como backend de base deatos para la persistencia de la memoria de conversación (checkpoints de LangGraph).
* **Psycopg (async):** Adaptador de PostgreSQL para Python asíncrono.

## Prerrequisitos

* Python (versión especificada arriba).
* Una instancia de PostgreSQL en ejecución y accesible.
* Credenciales y detalles de conexión para la base de datos PostgreSQL.
* (Opcional) Claves de API para los modelos de lenguaje (LLM) utilizados por los nodos del grafo, si se configuran externamente.

## Configuración e Instalación

1.  **Clonar el Repositorio (si aplica):**
    ```bash
    # git clone <tu-repositorio-url>
    # cd <directorio-del-proyecto>/api # O donde esté este README
    ```

2.  **Crear y Activar un Entorno Virtual:**
    ```bash
    python -m venv car_env
    source car_env/bin/activate  # En macOS/Linux
    # car_env\Scripts\activate    # En Windows
    ```

3.  **Instalar Dependencias:**
    Asegúrate de tener un archivo `requirements.txt` con todas las dependencias (FastAPI, Uvicorn, LangGraph, langgraph-checkpoint-postgres, psycopg[binary], python-dotenv, etc.).
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar Variables de Entorno:**
    Crea un archivo `.env` en el directorio raíz de la API (donde está `main.py`) con las siguientes variables:
    
    ```dotenv
    # Credenciales de la Base de Datos PostgreSQL
    DB_USER="tu_usuario_postgres"
    DB_PASSWORD="tu_contraseña_postgres"
    DB_HOST="localhost_o_tu_host_postgres" # ej: localhost o la IP/DNS de tu Cloud SQL
    DB_PORT="5432" # Puerto estándar de PostgreSQL
    DB_NAME="tu_nombre_de_bd"

    # Otras variables que puedas necesitar (ej. claves API para LLMs)
    # OPENAI_API_KEY="sk-..."
    # ANTHROPIC_API_KEY="..."
    ```
    **Nota:** El archivo `.env` se carga automáticamente por `python-dotenv` en `main.py`.

## Ejecutar la Aplicación

Abre tu terminal o línea de comandos.

Navega hasta el directorio donde guardaste main.py. Si lo pusiste en una subcarpeta api, navega a la carpeta que contiene api.

Ejecuta Uvicorn:

Si main.py está en la raíz de donde abriste la terminal:
Bash

```Bash
python -m uvicorn main:app --reload

```

Si main.py está en una subcarpeta api:

```Bash
python -m uvicorn api.main:app --reload
```

## Para conectarme a instancia Cloud Sql

En una nueva terminal:

```Bash
./cloud-sql-proxy thecarmentor-mvp2:europe-west1:carblau-sql-instance -p 5434
```

## Documentación de la API (Swagger/OpenAPI)

Una vez que la aplicación esté en ejecución, puedes acceder a la documentación interactiva de la API (generada automáticamente por FastAPI) en:

* Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* ReDoc: [http://127.0.0.1:8000/redoc]([http://127.0.0.1:8000/redoc)
  
## Endpoints de la API

1. Raíz
   * Método: GET
   * Path: /
   * Descripción: Endpoint de bienvenida.
   * Respuesta: {"message": "¡Bienvenido a la API del Agente CarBlau!"}
2. Test
   * Método: GET
   * Path: /test
   * Descripción: Endpoint de prueba para verificar que la API está operativa.
   * Respuesta: {"message": "¡El endpoint de prueba funciona correctamente!"}
3. Iniciar Conversación
   * Método: POST
   * Path: /conversation/start
   * Descripción: Inicia una nueva conversación con el agente CarMentor.
   * Cuerpo de la Solicitud (Opcional, JSON):

```JSON
{
    "initial_message": "Hola, busco un coche familiar." 
}
```

(Basado en el modelo Pydantic StartConversationRequest)

Respuesta (JSON):

```JSON
{
    "thread_id": "uuid-generado-para-la-conversacion",
    "agent_messages": [
        {"type": "CarBlau_AI", "content": "Hola, soy CarBlau. ¿Podrías indicarme tu código postal para comenzar?"}
    ]
}
```

(Basado en el modelo Pydantic StartConversationResponse)
4. Enviar Mensaje a una Conversación Existente
   * Método: POST
   * Path: /conversation/{thread_id}/message
   * Descripción: Envía un mensaje de usuario a una conversación existente, identificada por thread_id.
   * Parámetro de Path:
   * thread_id (string, UUID): El identificador único de la conversación devuelto por el endpoint /conversation/start.
   * Cuerpo de la Solicitud (JSON):

```JSON
{
    "content": "Mi código postal es 28010."
} 
```

(Basado en el modelo Pydantic UserMessageRequest)
Respuesta (JSON):

```JSON
{
    "thread_id": "uuid-de-la-conversacion-actual",
    "agent_messages": [
        {"type": "CarBlau_AI", "content": "Gracias. ¿Podrías decirme más sobre tus preferencias principales?"}
    ]
}
```

(Basado en el modelo Pydantic AgentMessageResponse)

## Sistema de Memoria con LangGraph y PostgreSQL

El agente CarMentor utiliza un sistema de memoria persistente para recordar el estado de las conversaciones. Esto permite a los usuarios retomar conversaciones interrumpidas y al agente mantener el contexto.

**Tecnología:** Se usa la funcionalidad de `"checkpointing"` de LangGraph.
Checkpointer: Se utiliza `langgraph.checkpoint.postgres.aio.AsyncPostgresSaver` para guardar y cargar los checkpoints de forma asíncrona en una base de datos PostgreSQL.

**Estado Persistido:** El estado completo del grafo de LangGraph, definido como `EstadoAnalisisPerfil` (ver graph/perfil/state.py), se guarda en cada checkpoint. Esto incluye el historial de mensajes, la información recopilada del usuario (código postal, preferencias, economía, etc.) y cualquier estado intermedio del agente.

**thread_id:** Cada conversación se asocia con un `thread_id` único (un UUID v4). Este thread_id es la clave que vincula una secuencia de interacciones del usuario con su estado persistido en la base de datos. Es fundamental para cargar el estado correcto y continuar una conversación.

Estructura en la Base de Datos
LangGraph, a través de AsyncPostgresSaver, crea y gestiona automáticamente las siguientes tablas principales en la base de datos PostgreSQL especificada:

**checkpoints:** Almacena metadatos sobre cada checkpoint, incluyendo:
thread_id: El identificador de la conversación.
checkpoint_id: Un ID único para el snapshot del estado.

**ts:** Timestamp del checkpoint.
parent_checkpoint_id: ID del checkpoint padre en el mismo hilo.
... y otras columnas de metadatos.
**checkpoint_blobs:** Almacena el estado serializado `(EstadoAnalisisPerfil)` como un blob binario, vinculado a la tabla checkpoints por `checkpoint_id`.

**Ciclo de Vida de la Memoria en la Aplicación**
Evento startup de FastAPI (main.py):
Se leen las credenciales de la base de datos desde el archivo .env.

Se llama a `ensure_tables_exist` (definida en graph/perfil/memory.py) para crear las tablas `checkpoints` y `checkpoint_blobs` en PostgreSQL si aún no existen. Esta función utiliza una instancia temporal de `AsyncPostgresSaver` con async with para ejecutar el método `setup()`.
Se crea una instancia "persistente" de A`syncPostgresSaver` utilizando `AsyncPostgresSaver.from_conn_string()`.
Se obtiene la instancia real del saver llamando a await gestor_de_contexto`.__aenter__() ` sobre el gestor devuelto por `from_conn_string()`. Esta instancia se guarda globalmente.
Se establece esta instancia global del saver mediante set_checkpointer_instance.
Se compila el grafo de LangGraph (car_mentor_graph), que internamente obtiene el saver configurado mediante get_memory().

**Durante las Solicitudes API:**
El endpoint /conversation/start genera un nuevo thread_id.
Tanto /start como /conversation/{thread_id}/message invocan el grafo (car_mentor_graph.ainvoke(...)) pasando el thread_id en el objeto config.
`AsyncPostgresSaver` utiliza este thread_id para guardar el nuevo estado del grafo (checkpoint) o cargar el estado anterior si la conversación continúa.
Evento shutdown de FastAPI (main.py):
Se llama a `await` gestor_de_contexto`.__aexit__(...)` para cerrar de forma limpia la conexión a la base de datos mantenida por la instancia persistente del saver.

**Beneficios**
**Persistencia de Conversación:** Los usuarios pueden retomar conversaciones donde las dejaron.
**Contexto Mantenido:** El agente recuerda información previa dentro de la misma conversación.
**Robustez:** El progreso no se pierde ante interrupciones o reinicios del servidor (hasta el último checkpoint).
Retomar Conversaciones (Frontend)
Para que un usuario retome una conversación, el frontend (no incluido en este backend) necesitaría:

Al iniciar una conversación, recibir el thread_id de la respuesta del endpoint /conversation/start.
Almacenar este thread_id de forma persistente en el lado del cliente (ej: en localStorage del navegador).
Para mensajes subsiguientes, o si el usuario vuelve a la aplicación, el frontend recuperaría el thread_id almacenado y lo usaría para llamar al endpoint /conversation/{thread_id}/message.
Si no hay thread_id almacenado, el frontend iniciaría una nueva conversación llamando a /conversation/start.

### **Estructura del Proyecto (Directorio API)**

```markdown
.
├── .env                # Variables de entorno (NO versionar si contiene secretos)
├── main.py             # Aplicación FastAPI, endpoints, eventos startup/shutdown
├── graph/              # Lógica del agente LangGraph
│   ├── builder.py          # Definición y compilación del grafo principal
│   ├── __init__.py
│   └── perfil/             # Módulos específicos para el perfilado de coches
│       ├── __init__.py
│       ├── condition.py    # Lógica condicional para las aristas del grafo
│       ├── memory.py       # Configuración del checkpointer AsyncPostgresSaver
│       ├── nodes.py        # Nodos (funciones) que componen el grafo
│       └── state.py        # Definición del estado del grafo (EstadoAnalisisPerfil)
└── requirements.txt    # Dependencias de Python
```
