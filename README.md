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





Aquí te explico los conceptos clave para lograr eso, sin entrar aún en el código específico:

1. Lograr Mayor Variedad en las Preguntas del Agente:

El problema actual es que, para asegurar la robustez, hemos tendido a "forzar" preguntas específicas (ya sea mediante los templates de _obtener_siguiente_pregunta_perfil o las instrucciones muy directas en <Reglas_Preguntas_Especificas> de los prompts). Para más naturalidad:

A) Ingeniería de Prompts Menos Rígida:

Instrucción: En lugar de "Usa esta pregunta EXACTA...", podrías instruir al LLM (ej: llm_solo_perfil) de forma más general: "Detecta qué información clave falta (ej: 'preferencia de transmisión'). Formula una pregunta amigable y natural para obtenerla. Puedes variar la formulación, pero asegúrate de que quede claro qué necesitas saber."
Ejemplos: Asegúrate de que los ejemplos en el prompt muestren diferentes formas de preguntar por la misma cosa.
Ventaja: Aprovecha la capacidad del LLM para generar lenguaje natural.
Desventaja: Pierdes algo de control. El LLM podría generar una pregunta ambigua o menos efectiva. Requiere ajustar y probar el prompt hasta que funcione bien consistentemente.
B) Múltiples Plantillas (Menos IA, Más Control):

Idea: En lugar de una pregunta fija en _obtener_siguiente_pregunta_perfil (nuestro fallback actual) o en las <Reglas_Preguntas_Especificas>, podrías tener una lista de 3-4 variaciones para cada pregunta clave.
Implementación: La función Python (_obtener_siguiente_pregunta_perfil o una nueva) elegiría una plantilla al azar de la lista correspondiente al campo faltante.
Ventaja: Tienes control total sobre las posibles preguntas.
Desventaja: Más trabajo manual para crear las plantillas. La variedad sigue siendo limitada a tus plantillas pre-escritas.
C) LLM dedicado a Re-formular (Más IA, Más Coste/Latencia):

Idea: Mantener la lógica que detecta qué falta (ej: _obtener_siguiente_pregunta_perfil te dice que falta apasionado_motor y la pregunta base es "¿Eres un apasionado...?"). Luego, hacer una llamada rápida a un LLM "creativo" (quizás llm_validacion con temperatura más alta) diciéndole: "Reformula esta pregunta de forma más conversacional: '¿Eres un apasionado del motor?'".
Ventaja: Mucha variedad y naturalidad potencial.
Desventaja: Añade una llamada LLM extra en cada turno de pregunta, incrementando coste y latencia.
Recomendación Conceptual: Empezaría probando la Opción A (Prompt Menos Rígido). Dale un poco más de libertad al llm_solo_perfil (y similares) para formular las preguntas en contenido_mensaje, pero monitoriza de cerca si sigue siendo efectivo en obtener la información necesaria.

2. Manejar Preguntas Contextuales del Usuario:

Este es un desafío mayor pero fundamental para simular a un vendedor. El agente necesita poder salirse momentáneamente del flujo de recopilación para responder dudas.

A) Detección de Intención + Enrutamiento (El Enfoque Más Robusto):

Clasificar Entrada: Al inicio de cada nodo principal (recopilar_preferencias, recopilar_economia, etc.) o en un nuevo nodo inicial, añade un paso para clasificar la intención del último mensaje del usuario:
¿Es una respuesta directa a mi última pregunta?
¿Es una pregunta sobre coches/finanzas/proceso?
¿Es una petición para cambiar algo ya dicho?
¿Es charla irrelevante? (Esto podría hacerse con otro LLM clasificador o con reglas heurísticas si las preguntas son predecibles).
Nueva Condición: Añade una arista condicional basada en esta intención.
Nodo/Lógica de Respuesta a Preguntas: Si la intención es una pregunta del usuario ("¿diferencia híbrido/eléctrico?"), redirige el flujo a un nuevo nodo especializado: responder_pregunta_usuario_node.
Implementación del Nodo de Respuesta: Este nodo usaría un LLM generalista (llm base), posiblemente apoyado por RAG sobre una base de conocimiento específica del sector automotriz que tú le proporciones (¡podrías crearla!), o incluso una herramienta (Tool) que busque en la web. Generaría la respuesta a la duda del usuario.
Volver al Flujo: Después de responder, este nodo necesita añadir la respuesta al historial y luego decidir cómo continuar. Lo más seguro es redirigir de vuelta al nodo que hizo la pregunta original (ej: preguntar_preferencias_node) para que repita la pregunta que había quedado pendiente antes de que el usuario preguntara su duda. Esto asegura que no se pierda el objetivo principal de recopilar información.
B) Integrar en Prompts Principales (Menos Robusto):

Idea: Modificar los prompts de llm_solo_perfil, llm_solo_filtros, etc., para que también intenten detectar y responder preguntas del usuario antes de extraer datos o hacer su propia pregunta.
Desventaja: Sobrecarga la tarea del LLM, aumenta la probabilidad de errores en la extracción de datos o en la respuesta a la pregunta. El control del flujo es mucho menor.
C) Usar Herramientas (Tools) de LangChain/LangGraph:

Idea: Si la respuesta a la pregunta del usuario requiere buscar información externa (tu base de conocimiento RAG, web), puedes definir esto como una "Herramienta". El LLM principal (llm_solo_perfil, etc.) puede ser instruido para que, si detecta una pregunta, en lugar de responderla él mismo, decida llamar a la herramienta apropiada. LangGraph tiene nodos específicos (ToolNode, ToolExecutor) para manejar esto.
Ventaja: Arquitectura muy potente y modular para agentes que necesitan interactuar con el exterior.
Desventaja: Añade la complejidad de definir y manejar herramientas dentro del grafo.
Recomendación Conceptual: El enfoque A (Detección de Intención + Enrutamiento + Nodo de Respuesta) es el más sólido y escalable para manejar interrupciones y preguntas del usuario de forma controlada dentro de un flujo principal de recopilación de datos. Usar RAG o Tools (Opción C) dentro del nodo de respuesta lo haría aún más potente.

En resumen:

Para hacerlo más conversacional, necesitas dar más libertad (controlada) al LLM para variar sus preguntas (Ingeniería de Prompts) y, fundamentalmente, añadir una capa de detección de intención y una ruta alternativa en tu grafo para manejar las preguntas que te haga el usuario, idealmente con un nodo dedicado que pueda acceder a conocimiento relevante (general o RAG) antes de retomar el flujo principal.

Estos cambios son significativos, pero son los que realmente elevan al agente a un nivel superior de interacción. ¿Sobre cuál de estos conceptos te gustaría profundizar más?


Fuentes y contenido relacionado
