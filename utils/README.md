# Descripción

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

Recordemos cómo se maneja la preferencia de aventura="extrema" y cómo esos valores {"altura_libre_suelo": 8, "traccion": 10, "reductoras": 8} influyen en los resultados de la búsqueda en BigQuery.

Es un proceso de varios pasos que va desde la definición de esos pesos "crudos" hasta su aplicación en la query SQL:

Definición en AVENTURA_RAW (en utils/weights.py):

Tú has definido que para el nivel "extrema", la importancia relativa cruda de las características de aventura es:

```python
AVENTURA_RAW = {
  # ... otros niveles ...
  "extrema":   {"altura_libre_suelo":  8,   "traccion": 10,  "reductoras":  8},
}
```

Esto significa que, cuando un usuario elige "aventura extrema", quieres que la traccion sea el factor más importante de estos tres, seguido por altura_libre_suelo y reductoras con igual importancia (8 puntos crudos cada uno).
Cálculo de Pesos Crudos Totales (en compute_raw_weights dentro de utils/weights.py):

Cuando el nodo finalizar_y_presentar_node llama a compute_raw_weights, le pasa el objeto preferencias (que contendría aventura='extrema').
La función compute_raw_weights usa preferencias.get("aventura") para obtener "extrema".
Busca en AVENTURA_RAW["extrema"] y añade estos valores (8, 10, 8) al diccionario raw junto con los otros pesos crudos que calcula (para estetica, premium, singular, batalla, indice_altura_interior, ancho).
Ejemplo de raw devuelto por compute_raw_weights (antes de normalizar): Si para un usuario con aventura extrema, los otros factores tuvieran pesos crudos bajos (ej: estetica=1, premium=1, singular=1, batalla=0.5, indice=0.5, ancho=0.5), el diccionario raw podría verse así:

```python

raw = {
    "estetica": 1.0, "premium": 1.0, "singular": 1.0, 
    "altura_libre_suelo": 8.0, "traccion": 10.0, "reductoras": 8.0,
    "batalla": 0.5, "indice_altura_interior": 0.5, "ancho": 0.5
} 
(Nota: los valores exactos dependerán de las otras preferencias del usuario).
```

Normalización de Pesos (en normalize_weights dentro de utils/weights.py):

Esta función toma el diccionario raw del paso anterior.

```python
Suma todos los valores crudos (ej: 1+1+1+8+10+8+0.5+0.5+0.5 = 30.5).
Divide cada valor crudo individual por esta suma total.
Impacto: Como altura_libre_suelo (8), traccion (10) y reductoras (8) son números grandes en el diccionario raw comparados con otros, sus pesos normalizados (los que realmente se envían a BigQuery como @peso_altura, @peso_traccion, @peso_reductoras) serán proporcionalmente altos.
Siguiendo el ejemplo:
peso_altura sería 8.0 / 30.5 = ~0.262
peso_traccion sería 10.0 / 30.5 = ~0.328
peso_reductoras sería 8.0 / 30.5 = ~0.262
Mientras que peso_estetica sería 1.0 / 30.5 = ~0.033
Este diccionario de pesos normalizados se guarda en state['pesos'].
```

Uso en la Query de BigQuery (en buscar_coches_bq):

La función recibe este diccionario de pesos normalizados.
En el cálculo del score_total dentro del SQL, cada característica del coche (escalada con Min-Max a un rango 0-1) se multiplica por su peso normalizado correspondiente:

```python

( ...
  + altura_scaled * @peso_altura  -- @peso_altura será ~0.262 (alto)
  + traccion_scaled * @peso_traccion -- @peso_traccion será ~0.328 (muy alto)
  + reductoras_scaled * @peso_reductoras -- @peso_reductoras será ~0.262 (alto)
  + estetica_scaled * @peso_estetica -- @peso_estetica será ~0.033 (bajo)
  ... 
) AS score_total

```

Impacto en el Ranking Final:

Debido a que los @peso_altura, @peso_traccion y @peso_reductoras son significativamente más altos que los pesos de otras características (para este perfil de "aventura extrema"), los coches que tengan buenos valores en altura_libre_suelo, traccion (ej: 'ALL') y reductoras (ej: True) recibirán una mayor contribución de estos factores a su score_total.
El ORDER BY score_total DESC hará que estos coches con altas capacidades off-road (porque fueron fuertemente ponderados) aparezcan más arriba en los resultados.
En resumen: Al definir valores crudos altos en AVENTURA_RAW para "extrema", te aseguras de que, después de la normalización, los pesos finales para esas características de aventura sean dominantes en el cálculo del score, priorizando así los vehículos más capaces en off-road para ese tipo de usuario.

Revisemos cómo lo estamos manejando en tu query SQL actual:

1. traccion (Valores: 'ALL', 'FWD', 'RWD', u otros/NULL)

Tu SQL Actual:

```python

CASE 
    WHEN traccion = 'ALL' THEN 1.0 
    WHEN traccion = 'RWD' THEN 0.5 
    ELSE 0.0 
END * @peso_traccion
```

Análisis:
Mapeo a Numérico: Estás convirtiendo la categoría de tracción en un valor numérico (1.0, 0.5, 0.0). Esto es una práctica común y necesaria para incluirla en un score sumatorio.
Escala 0-1: Los valores resultantes (0, 0.5, 1) están en una escala que es comparable (aunque más discreta) con las características escaladas con Min-Max (que también van de 0 a 1). Esto es bueno porque significa que el @peso_traccion tendrá un impacto relativo coherente.

Lógica de los Valores:
'ALL' (tracción total/4x4) obtiene el máximo (1.0), lo cual tiene sentido si la tracción es importante (ej. para aventura).
'RWD' (tracción trasera) obtiene un valor intermedio (0.5). Esto podría tener sentido si consideras que RWD ofrece ciertas ventajas sobre FWD en algunos contextos (quizás más deportivo o algo de capacidad en terrenos sueltos), pero menos que AWD/4WD para off-road puro.
ELSE 0.0 cubre 'FWD' (tracción delantera) y cualquier valor NULL o inesperado, dándoles la menor contribución.

Opinión: Está bien manejado para el propósito de un score que valora la capacidad de tracción (especialmente para aventura). La clave es que el @peso_traccion se ajuste según el perfil del usuario.
Si el usuario busca aventura="extrema", @peso_traccion será alto, y esta parte del score será muy influyente.
Si el usuario busca aventura="ninguna", compute_raw_weights debería asignar un peso crudo de 0 a traccion, resultando en @peso_traccion = 0.0. En este caso, el tipo de tracción del coche no afectará el score, lo cual es correcto.

La valoración de RWD como 0.5 es una decisión de diseño. Si para ciertos perfiles FWD fuera preferible (ej. por eficiencia en ciudad para un coche pequeño), esta lógica se podría complicar o el peso de tracción debería ser cero para ese perfil. Pero tal como está, para un factor que contribuye positivamente cuando se valora la "capacidad", es razonable.
2. reductoras (Valores: TRUE, FALSE, o NULL)

Tu SQL Actual:

```python

(CASE WHEN COALESCE(reductoras, FALSE) THEN 1.0 ELSE 0.0 END) * @peso_reductoras

```

Análisis:
Mapeo a Numérico: Convierte un booleano (o NULL tratado como FALSE) a 1.0 (si tiene reductoras) o 0.0 (si no tiene).
Escala 0-1: Perfecto, se alinea con las otras características escaladas.
Lógica de los Valores: Es una característica binaria: o se tiene o no se tiene. Un 1.0 para "sí" y 0.0 para "no" es directo y claro. COALESCE(reductoras, FALSE) maneja bien los NULLs.
Opinión: Está muy bien manejado. Es la forma estándar y correcta de incorporar una característica booleana importante en un score ponderado. Al igual que con la tracción, la importancia real vendrá del valor de @peso_reductoras derivado del perfil del usuario.
Conclusión General:

La forma en que estás manejando traccion y reductoras en la query es correcta y una práctica habitual. Las estás convirtiendo a una escala numérica (idealmente 0-1) para que puedan ser ponderadas junto con las otras características que has escalado con Min-Max.

Puntos Clave para que Funcione Bien:

Valores de Mapeo Coherentes: Asegúrate de que los valores numéricos que asignas (0, 0.5, 1 para tracción; 0, 1 para reductoras) reflejen la "deseabilidad" relativa de esas opciones dentro del contexto en que se les da peso.
Lógica de P
esos en compute_raw_weights: Lo más importante es que la función compute_raw_weights asigne pesos crudos a traccion y reductoras que tengan sentido para cada perfil. Por ejemplo:
aventura="extrema" -> pesos crudos altos para ambos.
aventura="ocasional" -> peso crudo moderado para tracción, bajo/cero para reductoras.
aventura="ninguna" -> pesos crudos cero para ambos.
Si la lógica de asignación de pesos es correcta, entonces el impacto de estas características en el score_total será el adecuado para cada tipo de usuario.



## Funcion que realiza la normalizacion: compute_raw_weights()

```python
if priorizar_ancho:
    raw["ancho"] = 6.0 # <-- Peso crudo ALTO
else:
    raw["ancho"] = 0.5 # <-- Peso crudo BAJO

Normalización de Pesos (en normalize_weights):
```

Esta función toma todos los pesos crudos calculados (estetica, premium, altura_libre_suelo, ancho, etc.) y los suma para obtener un total.
Luego, divide cada peso crudo individual entre ese total para obtener los pesos normalizados (que suman 1.0).
Impacto: Como el peso crudo de "ancho" es ahora mucho más grande (6.0) en comparación con los otros pesos crudos (que podrían ser 1.0, 5.0, 8.0, etc.) cuando priorizar_ancho es True, su proporción respecto al total será mayor. Por lo tanto, el peso normalizado final para "ancho" (el valor @peso_ancho que enviamos a BigQuery) será significativamente más alto que si priorizar_ancho hubiera sido False (donde el peso crudo era solo 0.5).
Cálculo del Score en BigQuery (en buscar_coches_bq):
```python
La query SQL calcula el score_total sumando varias partes. Una de esas partes es la contribución del ancho: ... + COALESCE(SAFE_DIVIDE(COALESCE(ancho, min_ancho) - min_ancho, max_ancho - min_ancho), 0) * @peso_ancho ...
COALESCE(SAFE_DIVIDE(...), 0) calcula el ancho del coche escalado entre 0 (si es el mínimo) y 1 (si es el máximo).
Este valor escalado (0 a 1) se multiplica por @peso_ancho.

Impacto: Cuando priorizar_ancho era True, @peso_ancho tiene un valor normalizado alto. Por lo tanto, los coches que realmente son más anchos (y tienen un valor escalado cercano a 1) recibirán una puntuación adicional mucho mayor de este componente que los coches estrechos. Si priorizar_ancho era False, @peso_ancho es bajo, y la contribución del ancho al score total es mínima, sin importar si el coche es ancho o estrecho.
Ordenación en BigQuery:

Finalmente, ORDER BY score_total DESC ordena los coches.
Como los coches más anchos recibieron una "bonificación" mayor en su score_total (gracias al alto peso_ancho que se activó por priorizar_ancho=True), es más probable que aparezcan más arriba en la lista de resultados.
En resumen: El flag priorizar_ancho = True no actúa como un filtro, sino que aumenta la "importancia" (el peso normalizado) de la característica ancho en la fórmula matemática que calcula la puntuación final de cada coche. Esto hace que los coches más anchos obtengan una ventaja en el ranking cuando esa característica es relevante para el usuario.
```
