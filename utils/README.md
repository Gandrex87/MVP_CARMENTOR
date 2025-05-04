# Descricpción

Este módulo contiene funciones auxiliares reutilizables que permiten separar la lógica de negocio de tareas comunes como postprocesamiento, formateo y manejo de enumeraciones / contiene funciones genéricas y reutilizables.

- `postprocessing.py`: Contiene reglas defensivas para completar filtros y preferencias faltantes.
- `formatters.py`: Formatea la salida al usuario en tablas o bloques amigables.
- `enums.py`: Define las clases Enum utilizadas en el análisis de vehículos.
- `postprocessing.py` : Evitar errores como 'str' object has no attribute 'value'. Puede convertir una lista de enums como esta ->          [TipoCarroceria.SUV, TipoCarroceria.COUPE]-> ["SUV", "COUPE"]

- `bigquery_tools.py`

Min-Max Scaling (Aplicado a los coches en BQ):

Entrada: Toma el valor real de una característica para un coche específico en la base de datos (ej: estetica = 8, altura_libre_suelo = 200).
Propósito: Convierte ese valor real a una escala común [0, 1] para que pueda ser comparado y ponderado justamente con otras características que originalmente tenían escalas diferentes.
Ejemplo: Si la estética va de 1 a 10, estetica=8 se convierte en (8 - 1) / (10 - 1) = 7 / 9 = 0.77. Si la altura va de 120 a 300, altura=200 se convierte en (200 - 120) / (300 - 120) = 80 / 180 = 0.44.
Funcionan Juntos:

Calculas los pesos_calculados (normalizados a suma 1) usando compute_raw_weights y normalize_weights en finalizar_y_presentar_node.
Pasas estos pesos_calculados a buscar_coches_bq.
Dentro de buscar_coches_bq, la query SQL:
Obtiene los valores reales de las características de cada coche.
Aplica Min-Max Scaling a esos valores reales para llevarlos al rango [0, 1].
Multiplica cada valor escalado [0, 1] por su peso_calculado correspondiente (del diccionario pesos).
Suma estos productos para obtener el score_total.


Opción A: Rangos Fijos "Suficientemente Amplios" (Pragmática y Simple):