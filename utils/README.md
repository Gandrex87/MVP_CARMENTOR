# Descricpción

Este módulo contiene funciones auxiliares reutilizables que permiten separar la lógica de negocio de tareas comunes como postprocesamiento, formateo y manejo de enumeraciones / contiene funciones genéricas y reutilizables.

- `postprocessing.py`: Contiene reglas defensivas para completar filtros y preferencias faltantes.
- `formatters.py`: Formatea la salida al usuario en tablas o bloques amigables.
- `enums.py`: Define las clases Enum utilizadas en el análisis de vehículos.
- `postprocessing.py` : Evitar errores como 'str' object has no attribute 'value'. Puede convertir una lista de enums como esta ->          [TipoCarroceria.SUV, TipoCarroceria.COUPE]-> ["SUV", "COUPE"]
