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
