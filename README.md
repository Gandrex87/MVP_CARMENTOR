# MVP_CARMENTOR

 ```python
 mvp carmentor repo 2025

┌────────────────────────────┐
│     Usuario (chat)         │
└────────────┬───────────────┘
             │ mensaje natural
             ▼
┌────────────────────────────┐
│  Sub-Agente A: ANALISIS    │
    INTENCIÓN                │
│  (OpenAI GPT-4o-mini)      │
│  - Analiza mensaje         │
│  - Extrae preferencias     │
│  - Devuelve filtros        │
└────────────┬───────────────┘
             │ filtros estructurados
             ▼
┌────────────────────────────┐
│ Sub-Agente B: BÚSQUEDA BD  │
│ (Gemini Flash + BigQuery)  │
│ - Usa tools de búsqueda    │
│ - Aplica filtros           │
│ - Devuelve resultados      │
└────────────┬───────────────┘
             │ coches encontrados
             ▼
┌────────────────────────────┐
│      Presentación final    │
│ - Resume resultados        │
│ - Ofrece opciones extra    │
│ - Confirma con el usuario  │
└────────────────────────────┘

```

```python
🧠 Cómo se alinea con TipoCarroceria:
Categoría | Enum Mapping
Compacto o urbano | DOS_VOL, TRES_VOL, COUPE
Familiar y amplio | SUV, MONOVOLUMEN, FURGONETA
Aventura o trabajo | PICKUP, COMERCIAL, AUTOCARAVANA
Descubierto y con estilo | DESCAPOTABLE
```

✅ Te recomiendo avanzar hacia una lógica híbrida o totalmente estructurada con embeddings.

```python
Propuesta de arquitectura híbrida

Usuario → SubAgente 1 (LLM OpenAI) → Inferencias básicas
                             ↓
                 Consulta a Vertex AI Matching Engine
                             ↓
      Enriquecimiento con tipo_carroceria, etc.
                             ↓
           SubAgente 2 (Deploy en GCP) hace la búsqueda final

```

➡️ Este es el caso que estamos implementando:
Tú estás creando una base estructurada (base_carroceria.json) que representa "documentos/características" y luego harás una consulta (prompt del usuario) para hacer matching semántico contra ellos.

Recuerda
* RETRIEVAL_DOCUMENT: Para la base (carrocerías, fichas ,textos explicativos).
* RETRIEVAL_QUERY: Para la consulta del usuario ("busco un coche para montaña").

```python
car_mentor/
│
├── main.py                        # Punto de entrada del agente o la app
├── config.py                      # Variables de entorno y configuración general
├── requirements.txt               # Dependencias
├── .env                           # Claves API (no subir a repositorio)
│
├── 📁 agents/                     # Sub-agentes y flujos LangGraph
│   ├── perfil_agente.py           # Flujo del sub-agente A (perfil)
│   ├── busqueda_agente.py        # Flujo del sub-agente B (búsqueda BigQuery)
│   └── __init__.py
│
├── 📁 prompts/                    # Archivos de prompt de sistema (SystemMessage)
│   └── perfil_structured_prompt.txt
│
├── 📁 schemas/                    # Modelos Pydantic (Entrada, Salida, Estado)
│   ├── perfil_schema.py
│   └── resultado_perfil_schema.py
│
├── 📁 utils/                      # Funciones auxiliares y lógicas reutilizables
│   ├── embeddings.py             # Generación de embeddings
│   ├── bigquery.py               # Carga y consulta en BigQuery
│   ├── normalizer.py             # Funciones de normalización de texto
│   ├── postprocesamiento.py      # Lógica defensiva
│   └── __init__.py
│
├── 📁 tests/                      # Pruebas unitarias y de integración
│   ├── test_postprocesamiento.py
│   └── test_validacion.py
│
├── 📁 data/                       # Archivos base como JSONs o TSV
│   └── base_carroceria.json
│
└── 📁 notebooks/                  # Jupyter notebooks para experimentación
    └── exploracion_embeddings.ipynb
```

```python
carmentor_project/
│
├── config/
│   ├── settings.py         ← variables de entorno
│   ├── llm.py              ← modelos LLM
│   └── vertex.py           ← (opcional) inicialización de VertexAI
│
├── graph/
│   ├── builder.py
│   ├── nodes.py
│   ├── state.py
│   ├── memory.py
│   ├── condition.py
│   └── ...
│
├── utils/
│   ├── enums.py
│   ├── formatters.py
│   ├── conversions.py
│   ├── ...
│
├── prompts/
│   ├── perfil_structured_prompt.txt
│   ├── ...
│
├── main.py   ← punto de entrada (si usas uno)
└── README.md
