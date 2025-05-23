# Mentor: Agente IA Recomendador de Vehículos con LangGraph 🚗💬

Este repositorio contiene el código fuente de "Mentor", un agente conversacional basado en LLMs (Modelos Grandes de Lenguaje) construido con Python y el framework **LangGraph**. El objetivo principal del agente es entender las necesidades, preferencias y situación económica de un usuario a través de una conversación turno a turno para, finalmente, poder recomendarle tipos de vehículos que se ajusten a su perfil.

## ✨ Características Principales

* **Conversación Multi-Turno:** Mantiene el contexto y recopila información a lo largo de varios intercambios con el usuario.
* **Recopilación Estructurada de Datos:** Utiliza LLMs con salida estructurada (validada por Pydantic) para extraer información clave en diferentes etapas.
* **Flujo Multi-Etapa:** La conversación sigue un flujo lógico definido:
    1.  **Perfil de Usuario:** Recopila preferencias generales (altura, peso, uso profesional, estética, eléctricos, transmisión, pasión por motor, nivel de aventura).
    2.  **Filtros Técnicos:** Infiere filtros técnicos basados en el perfil (batalla mínima, índice altura interior, estética mínima, tipo de mecánica, premium/singularidad mínima).
    3.  **Perfil Económico:** Recopila información económica según dos modos (asesoramiento financiero o presupuesto definido por el usuario).
    4.  **Finalización y Recomendación:**
        * Utiliza **RAG (Retrieval-Augmented Generation)** sobre un documento PDF para recomendar tipos de carrocería adecuados.
        * Calcula **pesos numéricos** basados en las preferencias para una posible ponderación futura de recomendaciones.
        * Presenta un **resumen final** en formato tabla Markdown.
* **Manejo Robusto de Conversación:** Implementa el patrón "Nodo Pregunta -> END" en LangGraph para asegurar un flujo conversacional estable turno a turno, incluso cuando se requieren aclaraciones.
* **Manejo de Errores:** Captura errores de validación de los LLMs y solicita aclaraciones al usuario.
* **Modularidad:** Código organizado en módulos para el grafo, utilidades (procesamiento, validación, formato, RAG, pesos), prompts y estado.
* **Pruebas Unitarias:** Incluye pruebas (usando `pytest` y `unittest.mock`) para verificar la lógica de los nodos individuales del grafo.

## 🏗️ Arquitectura y Tecnologías

El agente está construido sobre **LangGraph**, una extensión de LangChain para crear aplicaciones LLM stateful y cíclicas.

* **Orquestación:** Se utiliza `langgraph.graph.StateGraph` para definir el flujo de la aplicación.
* **Estado:** El estado de la conversación se gestiona con un `TypedDict` que contiene modelos Pydantic (`PerfilUsuario`, `FiltrosInferidos`, `EconomiaUsuario`) y el historial de mensajes (`add_messages`).
* **Nodos:** Funciones Python que encapsulan la lógica de cada paso (llamar a LLMs, validar, aplicar reglas, preguntar, finalizar).
* **Aristas:** Conexiones entre nodos, incluyendo `add_edge` (flujo directo) y `add_conditional_edges` (enrutamiento basado en el estado y funciones de validación).
* **LLMs:** Se integra con modelos de OpenAI (inicialmente `gpt-4o-mini`, con posibilidad de usar `gpt-4o` para tareas complejas como la economía) a través de LangChain. Se utiliza `with_structured_output` para obtener respuestas JSON validadas con Pydantic.
* **RAG:** Utiliza `pdfplumber` para leer datos de carrocerías desde un PDF, `langchain_openai.OpenAIEmbeddings` para generar embeddings y `langchain_community.vectorstores.FAISS` para crear y consultar un almacén vectorial.
* **Persistencia:** Utiliza `langgraph.checkpoint.memory.MemorySaver` para mantener el estado de la conversación en memoria (adecuado para desarrollo/pruebas).
* **Pruebas:** `pytest` y `unittest.mock`.
* **Otros:** Pydantic (modelado de datos y validación), Python estándar.

## 📂 Estructura del Proyecto (Ejemplo)

```python
├── graph/                  # Lógica principal del grafo LangGraph
│   ├── perfil/             # Nodos, builder, state, etc. específicos (o todo junto)
│   │   ├── init.py
│   │   ├── builder.py      # Define y compila el StateGraph
│   │   ├── nodes.py        # Funciones de los nodos (recopilar, validar, preguntar, inferir, finalizar)
│   │   ├── state.py        # Definición del TypedDict y modelos Pydantic (Perfil, Filtros, Economia, Resultados LLM)
│   │   └── memory.py       # Configuración del checkpointer (MemorySaver)
│   └── init.py
├── utils/                  # Funciones de utilidad reutilizables
│   ├── init.py
│   ├── conversion.py     # Funciones de normalización, is_yes, get_enum_names
│   ├── enums.py          # Definiciones de los Enums (TipoMecanica, NivelAventura, etc.)
│   ├── formatters.py     # formatear_preferencias_en_tabla
│   ├── postprocessing.py # aplicar_postprocesamiento_perfil, aplicar_postprocesamiento_filtros
│   ├── preprocessing.py  # (Opcional) extraer_preferencias_iniciales
│   ├── rag_carroceria.py # Lógica RAG para obtener carrocerías
│   ├── rag_reader.py     # Lector del PDF para RAG
│   ├── validation.py     # Funciones check_*_completeness
│   └── weights.py        # Lógica para calcular pesos
├── prompts/                # Archivos de texto con los prompts del sistema
│   ├── init.py
│   ├── loader.py         # (Opcional) Lógica para cargar prompts
│   ├── system_prompt_perfil.txt
│   ├── system_prompt_filtros_template.txt
│   └── system_prompt_economia_structured.txt
├── tests/                  # Pruebas unitarias/integración
│   ├── init.py
│   ├── test_nodes.py       # Pruebas para los nodos del grafo
│   ├── test_utils.py       # Pruebas para funciones de utilidad (opcional)
│   └── test_formatters.py  # Pruebas para la función de formato
├── .env                    # Archivo para variables de entorno (¡añadir a .gitignore!)
├── requirements.txt        # Dependencias del proyecto
├── main_conversation.py    # (Ejemplo) Script principal para interactuar con el agente
└── README.md               # Este archivo
```

## 📈 Estado Actual

* El flujo secuencial del grafo (Perfil -> Filtros -> Economía -> Finalización) está implementado y funcional.
* Los nodos individuales y las funciones de utilidad clave tienen pruebas unitarias que pasan.
* El patrón "Nodo Pregunta -> END" asegura una conversación estable turno a turno.
* El manejo de errores para ValidationErrors del LLM de economía está implementado.
Áreas de Mejora / Próximos Pasos:
Fiabilidad LLM Economía: Monitorizar y potencialmente seguir afinando el prompt system_prompt_economia_structured.txt o confirmar que el modelo más potente (gpt-4o) resuelve los ValidationError de forma consistente.
* Calidad RAG: Revisar la lógica de construcción de la query y los resultados de get_recommended_carrocerias para asegurar que las recomendaciones de carrocería sean pertinentes.
* Lógica de Pesos: Validar si el cálculo de pesos refleja adecuadamente la importancia de los atributos.
* Pruebas End-to-End: Realizar más pruebas de conversación completas con diferentes perfiles de usuario.
  
## Pensando en pasos futuros para despliegue

¡Excelente! Pensar en cómo llevar tu agente a producción es un paso muy importante. Usar FastAPI y luego desplegarlo en Cloud Run es una excelente elección y una ruta muy común y efectiva para aplicaciones basadas en Python como la tuya.

Aquí te presento un desglose conceptual de cómo sería ese proceso y qué implicaciones tendría:

Hoja de Ruta Conceptual para la Puesta en Producción:

### Encapsular la Lógica del Agente:

Tu grafo LangGraph (build_sequential_agent_graph()) y la lógica de conversación (run_conversation o una versión adaptada) necesitan ser accesibles de una forma que una API pueda llamar.

* Crear una API con FastAPI:

  * Propósito: FastAPI actuará como la "puerta de entrada" a tu agente. Recibirá solicitudes HTTP (por ejemplo, de un frontend, una app móvil, u otro servicio) y las pasará a tu agente LangGraph.
  * Endpoints Clave:
POST /conversation/start: Podría iniciar una nueva conversación, generar un thread_id (si no se proporciona uno) y devolver el primer mensaje del agente.
POST /conversation/{thread_id}/message: Recibe un mensaje del usuario para un thread_id existente, lo pasa al grafo LangGraph, y devuelve la respuesta del agente.
  * (Opcional) GET /conversation/{thread_id}/history: Para recuperar el historial de una conversación.
  * Manejo de Estado: La persistencia de la conversación (el thread_id y el estado asociado) es crucial.
  * Checkpointer: El MemorySaver que usamos para desarrollo no es adecuado para producción porque se pierde si la instancia se reinicia. Necesitarás un checkpointer persistente. LangGraph ofrece integraciones con:
Redis: Muy buena opción para estado en memoria rápido y persistente.
PostgreSQL/SQLite (con SqliteSaver o PgSaver): Buenas si ya tienes una base de datos relacional o quieres una solución basada en archivos para empezar.
LangServe: Aunque LangServe puede desplegar grafos LangGraph directamente, si quieres más control con FastAPI, usarías un checkpointer compatible.
El thread_id será la clave para recuperar y guardar el estado de cada conversación.

* Contenerización con Docker:

  * Propósito: Empaquetar tu aplicación FastAPI (junto con todas sus dependencias Python, tu código LangGraph, prompts, etc.) en una imagen de contenedor Docker. Esto asegura que funcione de manera consistente en cualquier entorno.
Dockerfile: Definirás las instrucciones para construir la imagen (instalar Python, copiar tu código, instalar requirements.txt, exponer el puerto de FastAPI, y el comando para iniciar el servidor Uvicorn con FastAPI).
requirements.txt: Debe listar todas las librerías necesarias (fastapi, uvicorn, langgraph, langchain, langchain-openai, google-cloud-bigquery, python-dotenv, etc.).

* Despliegue en Cloud Run:

  * Propósito: Cloud Run es una plataforma serverless de Google Cloud que ejecuta contenedores Docker. Es ideal porque escala automáticamente (incluso a cero si no hay tráfico, ahorrando costes) y gestiona la infraestructura por ti.

  * Pasos:
    * Construir y Subir la Imagen Docker: Construyes tu imagen Docker localmente y la subes a un registro de contenedores como Google Artifact Registry (o Google Container Registry).
    * Crear un Servicio en Cloud Run: Configuras un nuevo servicio en Cloud Run, apuntando a la imagen Docker que subiste.

* Configuración:
  * Variables de Entorno: Configura variables de entorno en Cloud Run para tus secretos (como OPENAI_API_KEY, credenciales de BQ si no usas ADC del entorno, configuración del checkpointer persistente).
  * Conexión a BigQuery: Si tu Cloud Run necesita acceder a BigQuery, asegúrate de que la cuenta de servicio que usa Cloud Run tenga los permisos necesarios para BigQuery.
  * Conexión al Checkpointer Persistente: Si usas Redis o una base de datos SQL para el checkpointer, Cloud Run necesitará poder conectarse a esa instancia (ej: a través de VPC Connector si está en una red privada).
CPU y Memoria: Ajusta los recursos según la carga esperada.
Escalado: Configura el mínimo y máximo de instancias.
URL Pública: Cloud Run te dará una URL HTTPS pública para acceder a tu API.
  * (Opcional pero Recomendado) API Gateway / Load Balancer:
Para mayor seguridad, gestión de tráfico, SSL personalizado, etc., podrías poner Google Cloud API Gateway o un Load Balancer delante de tu servicio Cloud Run.

* Consideraciones Adicionales:

  * Manejo de Errores en la API: Tu API FastAPI debe manejar errores de forma elegante (ej: si el grafo falla, si un thread_id no existe) y devolver códigos de estado HTTP apropiados.
  * Seguridad de la API: Considera cómo asegurarás tus endpoints (ej: claves API, autenticación si es necesario).
Logging y Monitorización en Producción: Cloud Run se integra con Google Cloud Logging y Monitoring. Asegúrate de que tu aplicación FastAPI y LangGraph generen logs útiles. LangSmith sigue siendo invaluable aquí.
  * Costes: Ten en cuenta los costes de Cloud Run, BigQuery, el servicio de checkpointer (Redis/SQL), y las llamadas a la API de OpenAI.
  * Actualizaciones: Define un proceso para actualizar tu aplicación (construir nueva imagen Docker, desplegar nueva revisión en Cloud Run).

### ¿Es Complejo?

Sí, llevar una aplicación a producción siempre tiene su complejidad, pero la ruta FastAPI + Docker + Cloud Run es una de las más directas y bien documentadas para aplicaciones Python. La mayor complejidad inicial estará en:

Configurar correctamente el checkpointer persistente para LangGraph.
Escribir el Dockerfile y configurar el despliegue en Cloud Run con las variables de entorno y permisos correctos.
En resumen:

Tu idea de FastAPI + Cloud Run es excelente. Es una pila tecnológica moderna, escalable y gestionada que se adapta muy bien a los agentes LangGraph. La clave será manejar bien la persistencia del estado de la conversación y la configuración del entorno en la nube.

¿Te gustaría que profundicemos en alguno de estos puntos, por ejemplo, cómo se vería un endpoint básico de FastAPI o qué checkpointer podría ser más adecuado para empezar?
