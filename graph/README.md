# Descripción

Cada archivo cumple un propósito:

- nodes.py = lógica de procesamiento.

- builder.py = conexión entre nodos.

- state.py = define qué datos maneja el grafo.

- memory.py = si en el futuro usas Redis u otro checkpoint.

Mucho más limpio para testear, mantener y compartir en equipos.

```python
graph/
├── perfil/                  # SubAgente-A
│   ├── builder.py
│   ├── nodes.py
│
├── busqueda/               # SubAgente-B
│   ├── builder.py
│   ├── nodes.py
│
├── state.py                # Estado común compartido entre agentes
├── memory.py
└── utils/                  # enums.py, conversions.py, etc.

```

```python
perfil/
    ├── builder.py   # Construye el grafo (StateGraph)
    ├── nodes.py     # Define funciones que representan nodos
    ├── state.py     # Define el schema del estado compartido (TypedDict)
    ├── memory.py    # Opcional: configuración de memoria para el flujo
```
Las 5 Claves para la Etapa de CP y Clima:

## codigo_postal_usuario: Optional[str]

Propósito: Almacena el código postal validado y final que el usuario proporciona. Este es el CP "oficial" que usaremos para la búsqueda de clima y potencialmente para otras lógicas.
¿Por qué? Necesitamos un lugar para el dato limpio y definitivo.
info_clima_usuario: Optional[InfoClimaUsuario]

Propósito: Almacena el resultado de la búsqueda en tu tabla zona_climas usando el codigo_postal_usuario. Será un objeto con los flags booleanos (ZONA_NIEVE, ZBE, etc.).
¿Por qué? Este es el output estructurado de la búsqueda de clima, que luego usarán otros nodos (RAG, pesos, etc.).
codigo_postal_extraido_temporal: Optional[str]

Propósito: Guarda temporalmente lo que el llm_cp_extractor cree que es el código postal, justo después de que el LLM procesa la respuesta del usuario.
¿Por qué? El nodo recopilar_cp_node llama al LLM. El LLM devuelve un ResultadoCP que contiene codigo_postal_extraido. Este valor aún no ha sido validado por nuestra lógica de Python (ej: ¿son 5 dígitos? ¿es numérico?). El nodo validar_cp_node necesita este valor "crudo" del LLM para realizar esas validaciones antes de decidir si es el codigo_postal_usuario final. Es un paso intermedio.
tipo_mensaje_cp_llm: Optional[Literal["PREGUNTA_ACLARACION", "CP_OBTENIDO", "ERROR"]]

Propósito: Guarda temporalmente el tipo_mensaje que devuelve el llm_cp_extractor (dentro del objeto ResultadoCP).
¿Por qué? El nodo validar_cp_node necesita saber qué "intención" tenía el LLM.
Si el LLM dice CP_OBTENIDO, validar_cp_node entonces verifica el codigo_postal_extraido_temporal.
Si el LLM dice PREGUNTA_ACLARACION, validar_cp_node sabe que debe dirigir el flujo para que se haga esa pregunta de aclaración. Es otra pieza de información transitoria entre el nodo de recopilación y el nodo de validación.
_decision_cp_validation: Optional[Literal["buscar_clima", "repreguntar_cp"]]

Propósito: Guarda la decisión de enrutamiento que toma el nodo validar_cp_node después de analizar el codigo_postal_extraido_temporal y el tipo_mensaje_cp_llm.
¿Por qué? En LangGraph, cuando tienes una arista condicional (add_conditional_edges), la función de condición (nuestra ruta_decision_cp) necesita leer algún valor del estado para decidir a qué nodo saltar. validar_cp_node calcula la decisión y la pone en esta clave del estado para que ruta_decision_cp la use. La _ al principio sugiere que es una clave "interna" para la lógica del grafo.
