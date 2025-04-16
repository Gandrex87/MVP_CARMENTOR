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
