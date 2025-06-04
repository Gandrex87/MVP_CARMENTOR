# CarBlau:  Asistente IA experto para Encontrar el Coche Ideal 🚙💬

## 1. Introducción

**CarBlau** es un agente conversacional avanzado diseñado para ayudar a los usuarios a encontrar el vehículo que mejor se adapte a sus necesidades, preferencias y contexto particular. A través de una serie de preguntas interactivas, CarBlau recopila información detallada sobre el perfil del usuario, sus prioridades, situación de aparcamiento, condiciones climáticas de su zona, y presupuesto, para luego realizar una búsqueda inteligente en una base de datos de vehículos y presentar recomendaciones personalizadas con explicaciones claras.

El objetivo principal es simular la experiencia de hablar con un vendedor de coches experto y empático, pero con la potencia del análisis de datos y la inteligencia artificial para ofrecer resultados altamente relevantes.

## 2. Características Destacadas

* **Recopilación Detallada de Preferencias:** El agente indaga sobre más de 25 aspectos del perfil del usuario, incluyendo:
    * Dimensiones del conductor (altura, peso).
    * Uso del vehículo (profesional, personal, coche principal).
    * Necesidades de espacio (carga voluminosa, objetos especiales, remolque).
    * Situación de aparcamiento (garaje, problemas en calle, dimensiones del garaje).
    * Preferencias estéticas y de exclusividad.
    * Tipo de motorización y transmisión.
    * Estilo de conducción y nivel de aventura.
    * Importancia de la baja depreciación.
    * **Ratings 0-10** para 6 características clave: Fiabilidad/Durabilidad, Seguridad, Comodidad, Impacto Medioambiental, Costes de Uso/Mantenimiento (actualmente opcional), y Tecnología/Conectividad.
* **Adaptación al Contexto Geográfico y Climático:**
    * Solicita el código postal del usuario al inicio.
    * Consulta una base de datos para identificar características de la zona: ZBE (Zona de Bajas Emisiones), disponibilidad de GLP/GNV, y condiciones climáticas (lluvia, nieve, niebla, montaña).
* **Inferencia de Filtros Técnicos:** Traduce las preferencias del usuario en filtros técnicos iniciales para la búsqueda (ej: `estetica_min`, `tipo_mecanica`, `premium_min`, `singular_min`).
* **Recomendación de Tipos de Carrocería con RAG:** Utiliza un sistema de Generación Aumentada por Recuperación (RAG) sobre una base de conocimiento de tipos de carrocería para sugerir las más adecuadas según el perfil.
* **Cálculo de Pesos Dinámicos:** Asigna pesos de importancia a múltiples características del vehículo basándose en todas las preferencias recopiladas, incluyendo los ratings explícitos y las condiciones climáticas.
* **Lógica de Scoring Avanzada en BigQuery:**
    * Aplica Min-Max Scaling a las características de los coches.
    * Calcula un `score_total` para cada vehículo mediante una suma ponderada.
    * Implementa **penalizaciones y bonificaciones condicionales** (ej: por distintivo ambiental en ZBE, por antigüedad si se valora la tecnología, por características del coche que entran en conflicto con altas prioridades del usuario como la comodidad).
* **Explicaciones Personalizadas ("Por Qué este Coche"):** Para cada coche recomendado, el agente (opcionalmente usando un LLM) puede generar una breve explicación de por qué es una buena opción para ese usuario específico, basándose en los factores que más contribuyeron a su score.
* **Manejo de Conversación Flexible:**
    * Capacidad para guiar al usuario si no entiende una pregunta o un término.
    * Manejo de errores de validación de Pydantic para entradas incorrectas (ej: ratings fuera de rango), solicitando al usuario que reformule.
* **API con FastAPI:** Expone la funcionalidad del agente a través de una API RESTful, lista para ser integrada con frontends o consumida por otros servicios.
* **Persistencia de Conversaciones:** Diseñado para usar un checkpointer persistente (como PostgreSQL con `AsyncPostgresSaver`) para mantener el estado de las conversaciones, esencial para producción.

## 3. ¿Cómo Funciona? (Flujo de Interacción)

El agente opera a través de un grafo de estados (LangGraph) que gestiona el flujo de la conversación por etapas:

1.  **Recopilación de Código Postal y Clima:**
    * El agente saluda y solicita el código postal (CP) del usuario.
    * Valida el formato del CP.
    * Consulta la base de datos `zonas_climas` (en BigQuery) para obtener información sobre ZBE, disponibilidad de GLP/GNV, y condiciones climáticas predominantes (lluvia, nieve, niebla, montaña) asociadas a ese CP. Esta información se guarda en el estado.

2.  **Perfil del Usuario (Preferencias Generales y Ratings):**
    * El agente realiza una serie de preguntas para construir un perfil detallado, cubriendo los 25+ campos mencionados anteriormente (altura, uso, aventura, ratings 0-10, garaje, remolque, etc.).
    * Las preguntas se hacen de forma secuencial y condicional (ej: solo se pregunta por el tipo de uso profesional si el uso es profesional).
    * El LLM (`llm_solo_perfil`) extrae la información y actualiza el objeto `PerfilUsuario` en el estado.

3.  **Información de Pasajeros:**
    * Se pregunta sobre la frecuencia de viaje con acompañantes, número de niños en silla (X) y otros pasajeros (Z).
    * Esta información se usa en `aplicar_filtros_pasajeros_node` para calcular:
        * `plazas_min` (filtro duro para BQ).
        * `penalizar_puertas_bajas` (flag para el score si X >= 1 y frecuencia es "frecuente").
        * `priorizar_ancho` (flag para los pesos si Z >= 2).

4.  **Inferencia de Filtros Técnicos y Post-procesamiento:**
    * El nodo `inferir_filtros_node` llama a `llm_solo_filtros`. Este LLM recibe el `PerfilUsuario` completo y la `InfoClimaUsuario` como contexto.
    * Infiere valores iniciales para `estetica_min`, `tipo_mecanica`, `premium_min`, `singular_min`.
    * Luego, `aplicar_postprocesamiento_filtros` refina estos filtros:
        * Ajusta `estetica_min`, `premium_min`, `singular_min` según reglas de negocio (ej: basado en `apasionado_motor`, `valora_estetica`).
        * Modifica la lista de `tipo_mecanica` basándose en `solo_electricos` y la `InfoClimaUsuario` (ej: quita/añade GLP/GNV si la zona no/sí es compatible; ajusta por ZBE).

5.  **Preferencias Económicas:**
    * El agente pregunta al usuario si prefiere asesoramiento financiero (Modo 1) o definir él mismo el presupuesto (Modo 2).
    * Según la elección, se recopilan los datos necesarios (ingresos/ahorro/años para Modo 1; pago contado o cuota para Modo 2).

6.  **Generación de Criterios Finales (Secuencia de Nodos Refactorizada):**
    * `calcular_recomendacion_economia_modo1_node`: Si es Modo 1, calcula el presupuesto recomendado y actualiza los filtros.
    * `obtener_tipos_carroceria_rag_node`: Llama a `get_recommended_carrocerias`. Esta función construye una query semántica (usando `preferencias_usuario`, `info_pasajeros`, `info_clima`) y la envía al RAG para obtener una lista de `tipo_carroceria` adecuados.
    * `calcular_flags_dinamicos_node`: Calcula todos los flags booleanos (ej: `flag_penalizar_low_cost_comodidad`, `flag_penalizar_antiguo_por_tecnologia`, `aplicar_logica_distintivo_ambiental`, `es_municipio_zbe`) basados en las preferencias y el clima.
    * `calcular_pesos_finales_node`: Llama a `compute_raw_weights` (que usa todas las preferencias, ratings, y flags climáticos para generar pesos crudos) y luego a `normalize_weights` para obtener los pesos finales que suman 1.0.
    * `formatear_tabla_resumen_node`: Genera una tabla Markdown con el resumen de todo el contexto y preferencias recopiladas. (En el flujo actual, este mensaje se combina con los resultados de los coches).

7.  **Búsqueda de Coches en BigQuery (`buscar_coches_finales_node`):**
    * Este nodo recibe la tabla resumen, los filtros finales y los pesos.
    * Llama a `buscar_coches_bq`.
    * `buscar_coches_bq` construye una query SQL dinámica:
        * Aplica Min-Max Scaling a las características numéricas de los coches.
        * Aplica filtros `WHERE` (plazas, tipo mecánica, tipo carrocería, precio/cuota, etc.).
        * Calcula un `score_total` sumando las características escaladas ponderadas por los pesos del usuario, y añadiendo las bonificaciones/penalizaciones condicionales (por distintivo ambiental, ZBE, antigüedad, puertas, etc.).
        * Ordena por `score_total` y devuelve los `k` mejores coches, incluyendo sus características escaladas.
    * (Opcional) Se llama a `generar_explicacion_coche_con_llm` para cada coche, usando los datos escalados, los pesos y las preferencias para crear una justificación personalizada.
    * Se construye un `AIMessage` final que incluye la tabla resumen de criterios y la lista de coches recomendados (con sus explicaciones).
    * Se loguea la búsqueda completa a una tabla de BigQuery.

## 4. Lógica de Scoring y Personalización

El corazón de la personalización reside en cómo se traducen las preferencias del usuario en un `score_total` para cada coche.

* **Pesos Dinámicos:** La función `compute_raw_weights` asigna "pesos crudos" a más de 30 características potenciales (estética, seguridad, comodidad, par motor, bajo consumo, etc.) basándose en:
    * Ratings explícitos del usuario (0-10).
    * Respuestas sí/no a preguntas clave (ej: `apasionado_motor`, `prioriza_baja_depreciacion`, `arrastra_remolque`, problemas de garaje).
    * Condiciones contextuales (ej: `altura_mayor_190` afecta peso de `batalla`; `info_clima` afecta peso de `traccion` y `seguridad`).
    Estos pesos crudos se normalizan para que sumen 1.0, determinando la importancia relativa de cada factor en el score final.
* **Min-Max Scaling:** Las características numéricas de los coches en BigQuery se escalan a un rango [0, 1] para que sean comparables y puedan ser multiplicadas por los pesos normalizados. Para características donde "menos es mejor" (ej: consumo, peso, dimensiones de garaje), se usa un escalado invertido.
* **Filtros Duros:** Se aplican en la cláusula `WHERE` de BigQuery para descartar coches que no cumplen requisitos básicos (ej: `plazas_min`, `precio_maximo`, `tipo_mecanica` y `tipo_carroceria` seleccionados por RAG).
* **Bonificaciones y Penalizaciones Condicionales:** Se aplican ajustes directos (positivos o negativos) al `score_total` si se cumplen ciertas condiciones, activadas por flags:
    * **Comodidad:** Si el usuario valora mucho la comodidad, los coches muy "low-cost" o muy "deportivos" reciben una penalización.
    * **Tecnología vs. Antigüedad:** Si el usuario valora mucho la tecnología, los coches más antiguos (>5, >7, >10 años) reciben penalizaciones graduales.
    * **Impacto Ambiental (General):** Si el usuario valora el bajo impacto ambiental, los coches con distintivo CERO/0/ECO/C reciben un bonus, y los B/NA una penalización. Los coches de "ocasión" también reciben un pequeño bonus.
    * **Zona de Bajas Emisiones (ZBE):** Si el CP del usuario está en ZBE, la bonificación/penalización por distintivo ambiental es más fuerte.

## 5. Arquitectura y Tecnologías

* **Lenguaje:** Python 3.11+
* **Framework del Agente:** LangGraph (para construir el grafo de estados y la lógica conversacional).
* **Motor LLM:** Configurado para usar modelos de OpenAI (ej: `gpt-4o-mini`) o Google Vertex AI (ej: `gemini-1.5-flash`) a través de las integraciones de LangChain. Se utiliza `with_structured_output(method="function_calling")` para las salidas JSON.
* **API:** FastAPI con Uvicorn (para exponer el agente como un servicio web).
* **Base de Datos de Vehículos:** Google BigQuery.
* **Base de Conocimiento RAG:** Documento PDF procesado y almacenado en un índice vectorial FAISS con embeddings de OpenAI.
* **Persistencia de Conversaciones:** Diseñado para `AsyncPostgresSaver` (LangGraph) con PostgreSQL (recomendado Cloud SQL para producción).
* **Validación de Datos:** Pydantic.
* **Manipulación de Datos:** Pandas (para formatear resultados de BQ).

## 6. Estructura del Proyecto (Simplificada)

```markdown
/MVP_CARMENTOR
|-- api/
|   |-- main.py             # Aplicación FastAPI, endpoints
|-- config/
|   |-- llm.py              # Configuración e inicialización de LLMs
|   |-- settings.py         # Constantes centralizadas (MIN_MAX_RANGES, umbrales, etc.)
|-- graph/
|   |-- perfil/
|   |   |-- init.py
|   |   |-- builder.py        # Construcción del grafo LangGraph
|   |   |-- memory.py         # Configuración del Checkpointer (memoria)
|   |   |-- nodes.py          # Definición de todos los nodos del grafo
|   |   |-- state.py          # Modelos Pydantic para el estado y resultados LLM
|-- prompts/
|   |-- loader.py           # Utilidad para cargar prompts desde archivos
|   |-- system_prompt_cp.txt
|   |-- system_prompt_perfil.txt
|   |-- system_prompt_pasajeros.txt
|   |-- system_prompt_filtros_template.txt
|   |-- system_prompt_economia.txt
|   |-- system_prompt_explicacion_coche.txt
|-- utils/
|   |-- bigquery_tools.py   # Lógica para buscar coches en BQ (función buscar_coches_bq)
|   |-- bq_data_lookups.py  # Lógica para buscar datos de clima en BQ
|   |-- conversion.py       # Funciones de ayuda (ej: is_yes)
|   |-- enums.py            # Definiciones de todos los Enums
|   |-- explanation_generator.py # Lógica para generar "Por Qué este Coche"
|   |-- formatters.py       # Lógica para formatear tablas resumen
|   |-- postprocessing.py   # Lógica de post-procesamiento de filtros
|   |-- rag_carroceria.py   # Lógica RAG para tipos de carrocería
|   |-- rag_reader.py       # (Asumido) Lector de PDF y creador de Vector Store
|   |-- vector_store_module.py # (Asumido) Acceso al Vector Store
|   |-- weights.py          # Lógica para calcular pesos crudos y normalizados
|-- tests/                    # Pruebas unitarias y de integración
|   |-- ...
|-- .env                      # Variables de entorno (API keys, credenciales BBDD) - NO SUBIR A GIT
|-- requirements.txt          # Dependencias Python
|-- Dockerfile                # (Para producción) Definición de la imagen Docker
```
... otros archivos ...

## 7. Configuración y Ejecución (Desarrollo Local)

1.  **Clonar el Repositorio.**
2.  **Crear y Activar un Entorno Virtual:**
    ```bash
    python -m venv car_env
    source car_env/bin/activate  # macOS/Linux
    # car_env\Scripts\activate  # Windows
    ```
3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configurar Variables de Entorno:**
    * Crear un archivo `.env` en la raíz del proyecto.
    * Añadir las claves API necesarias (ej: `OPENAI_API_KEY`) y las credenciales para la base de datos del checkpointer (ej: `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`).
    * Configurar `GCLOUD_PROJECT` si se usa Vertex AI.
5.  **Base de Datos para Checkpointer (PostgreSQL):**
    * Asegurarse de tener una instancia de PostgreSQL accesible.
    * Para desarrollo local con Cloud SQL, ejecutar el [Cloud SQL Auth Proxy](https://cloud.google.com/sql/docs/postgres/connect-auth-proxy) y configurar `DB_HOST=127.0.0.1` en el `.env`.
6.  **Base de Datos de Vehículos (BigQuery):**
    * Asegurarse de tener acceso al proyecto y dataset de BigQuery con la tabla de coches.
    * Autenticarse con Google Cloud: `gcloud auth application-default login`.
7.  **Vector Store (FAISS):**
    * Asegurarse de que el índice FAISS (`faiss_carroceria_index`) exista y sea accesible por `get_vectorstore()`.
8.  **Iniciar la API FastAPI:**
    ```bash
    uvicorn api.main:app --reload
    ```
    La API estará disponible en `http://127.0.0.1:8000` y la documentación interactiva en `http://127.0.0.1:8000/docs`.

## 8. Próximos Pasos y Mejoras Futuras

* **Despliegue en Cloud Run:** Contenerizar la aplicación FastAPI con Docker y desplegarla.
* * **Generar Frontend simple:** Que permita realizar pruebas a los usuarios.
* **Refinamiento Continuo de Prompts:** Ajustar los prompts de los LLMs para mejorar la naturalidad y precisión de las extracciones y generaciones.
* **Mejora de la Lógica RAG:** Optimizar los documentos y la query para obtener recomendaciones de `tipo_carroceria` aún más precisas.
* **Pruebas de Usuario:** Realizar pruebas con usuarios reales para obtener feedback y refinar la experiencia.
* **Ampliación de la Base de Conocimiento:** Añadir más datos de coches y refinar las características en BigQuery y en la Base de datos principal de 149.000 coches.
* **Implementar "Explicación de Términos/Preguntas"** para mejorar la UX.
* **Implementar "Ampliar Información del Coche Bajo Demanda"** usando herramientas de búsqueda web.

---