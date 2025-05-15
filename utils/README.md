# Descripción de las funciones utilitarias del Agente

Este módulo contiene funciones auxiliares reutilizables que permiten separar la lógica de negocio de tareas comunes como postprocesamiento, formateo y manejo de enumeraciones / contiene funciones genéricas y reutilizables.

- `postprocessing.py`: Contiene reglas defensivas para completar filtros y preferencias faltantes.
- `formatters.py`: Formatea la salida al usuario en tablas o bloques amigables.
- `enums.py`: Define las clases Enum utilizadas en el análisis de vehículos.
- `postprocessing.py` : Evitar errores como 'str' object has no attribute 'value'. Puede convertir una lista de enums como esta ->          [TipoCarroceria.SUV, TipoCarroceria.COUPE]-> ["SUV", "COUPE"]

- `bigquery_tools.py`

Funcionamiento Detallado de Componentes Clave
Para ofrecer recomendaciones personalizadas, el agente utiliza varias funciones especializadas. Dos de las más importantes en la lógica de selección y ranking de vehículos son compute_raw_weights y buscar_coches_bq.

- `weights.py`
  
1. `compute_raw_weights`
Esta función es el primer paso para traducir las diversas preferencias del usuario en un sistema numérico que permita comparar coches.

## Propósito Principal `compute_raw_weights`

Consolidar todas las preferencias del usuario (tanto las respuestas directas 'sí'/'no', las selecciones de enums como el nivel de aventura, y los ratings explícitos de 0-10) en un conjunto de "pesos crudos" o "puntuaciones de importancia inicial" para diferentes características de un vehículo. Estos pesos crudos aún no están listos para ser usados directamente en el ranking final, ya que no están en una escala comparable, pero reflejan la importancia inicial que el agente le da a cada aspecto.

## Entradas Principales (`Args`)


* `preferencias: Dict[str, Any]`: Un diccionario que contiene todas las respuestas del perfil del usuario, incluyendo:
* `aventura`: Nivel de aventura (ej: "ninguna", "ocasional", "extrema").
* `altura_mayor_190`: Si el usuario es alto ('sí'/'no').
* `rating_fiabilidad_durabilidad`: Calificación de 0-10 dada por el usuario.
* `rating_seguridad`: Calificación de 0-10.
* `rating_comodidad`: Calificación de 0-10.
* `rating_impacto_ambiental`: Calificación de 0-10.
* `rating_tecnologia_conectividad`: Calificación de 0-10.
* (`rating_costes_uso` actualmente omitido, pero podría incluirse aquí).
* `estetica_min_val`: Optional[float]: Valor numérico (ej: 1.0 o 5.0) derivado del post-procesamiento de las preferencias valora_estetica y apasionado_motor.
* `premium_min_val`: Optional[float]: Valor numérico (ej: 0.5 o 3.0) derivado del post-procesamiento de apasionado_motor.
* `singular_min_val`: Optional[float]: Valor numérico (ej: 1.0, 3.5 o 6.0) derivado del post-procesamiento de apasionado_motor y prefiere_diseno_exclusivo.
* `priorizar_ancho`: Optional[bool]: Un flag booleano que indica si se debe dar más importancia al ancho del vehículo (derivado de la información de pasajeros).


## Lógica Central de weights.py

1. **Pesos Base por Filtros Derivados**: Inicializa los pesos crudos para "`estetica`", "`premium`" y "`singular`" usando directamente los valores `estetica_min_val`, `premium_min_val` y `singular_min_val` recibidos. Estos valores ya reflejan una "importancia" derivada de las preferencias del usuario.
2. **Pesos por `Aventura`**: Consulta el diccionario `AVENTURA_RAW` usando el nivel de aventura del usuario para obtener los pesos crudos para `"altura_libre_suelo"`, `"traccion"` y `"reductoras"`.
3. **Pesos por Dimensiones del Conductor:** Si `altura_mayor_190` es 'sí', asigna pesos crudos predefinidos (más altos) a `"batalla"` e `"indice_altura_interior"`. Si es 'no', asigna pesos bajos.
4. **Peso por Ancho del Vehículo:** Si `priorizar_ancho` es `True`, asigna un peso crudo predefinido (alto) a `"ancho"`. Si es False, asigna un peso bajo.
5. **Pesos por Ratings Explícitos:** Para cada una de las 5 (o 6) nuevas características (Fiabilidad y Durabilidad, Seguridad, Comodidad, Impacto Ambiental, Tecnología y Conectividad), toma el rating numérico (0-10) proporcionado por el usuario directamente del diccionario `preferencias` y lo usa como el peso crudo para esa característica `(ej: raw["rating_seguridad"] = preferencias.get("rating_seguridad", 0.0))``.
6. **Salida** (Returns):`Dict[str, float]:` Un diccionario donde las claves son los nombres de las características (ej: `"estetica"`, `"traccion"`, `"rating_seguridad"`) y los valores son sus pesos crudos calculados.
Este diccionario luego se pasa a la función `normalize_weights` para escalar todos estos pesos crudos a una suma total de 1.0, haciéndolos comparables para el scoring final.

- `bigquery_tools.py`

2.`buscar_coches_bq`
Esta es la función principal que interactúa con la base de datos de coches en BigQuery para encontrar y clasificar vehículos según los criterios y preferencias del usuario.

## Propósito Principal `buscar_coches_bq`

Construir y ejecutar una query SQL dinámica en BigQuery que:

1. Aplica **filtros duros** para descartar coches que no cumplen requisitos básicos (ej: número de plazas, tipo de mecánica, precio máximo).
2. Calcula un **score de afinidad** (`score_total`) para los coches restantes, basado en una ponderación de múltiples características del vehículo según la importancia que el usuario les haya dado (los pesos normalizados).
3. Ordena los coches por este score y devuelve los k mejores.
Entradas Principales (`Args`):

- `filtros: Dict[str, Any]:` Un diccionario que contiene:
  
      - Filtros duros: `plazas_min`, `estetica_min` (si aún se usa como filtro), `tipo_mecanica`(lista), `tipo_carroceria` (lista).
      - Límites económicos: `precio_max_contado_recomendado` o `cuota_max_calculada` (o los directos del Modo 2 como `pago_contado`, `cuota_max`).
      - Flags booleanos para activar penalizaciones en el score: `penalizar_puertas_bajas`, `flag_penalizar_low_cost_comodidad`, `flag_penalizar_deportividad_comodidad`.
  
- `pesos: Dict[str, float]:` Un diccionario que contiene los pesos normalizados (suman 1.0) para todas las características que se consideran en el score_total (ej: `peso_estetica`, `peso_rating_seguridad`, `peso_ancho`, etc.). Estos vienen de `normalize_weights`(`compute_raw_weights`(...)).
`k: int:` El número máximo de coches a devolver.

## Lógica Central de bigquery_tools.py

1. Inicialización y Preparación de Pesos/Flags: Extrae los valores de los diccionarios filtros y pesos, estableciendo defaults (como 0.0 para pesos no especificados).
2. Construcción del SQL - CTE ScaledData:
La query define una "Common Table Expression" (CTE) llamada ScaledData.
Dentro de esta CTE, para cada característica numérica del coche que se usará en el score (estetica, premium, singular, altura_libre_suelo, batalla, indice_altura_interior, ancho, fiabilidad, durabilidad, seguridad, comodidad, tecnologia, acceso_low_cost, deportividad):
Se aplica Min-Max Scaling: (ValorActual - MinGlobal) / (MaxGlobal - MinGlobal). Esto transforma el valor original de la característica a una escala común de 0 a 1. Los MinGlobal y MaxGlobal se definen en la constante MIN_MAX_RANGES en el código Python y se "empotran" en el SQL. Se usa COALESCE y SAFE_DIVIDE(..., NULLIF(denominador,0)) para manejar NULLs y evitar división por cero, resultando en un valor escalado de 0 en esos casos.
Para características categóricas como traccion o booleanas como reductoras, se mapean a valores numéricos (ej: 0, 0.5, 1.0).
Se calculan términos de penalización condicional (ej: puertas_penalty, penalizaciones por acceso_low_cost o deportividad si la comodidad es alta) usando CASE WHEN @flag_booleano = TRUE AND condicion_coche THEN VALOR_PENALIZACION ELSE 0.0 END.
3. Construcción del SQL - SELECT Principal:
Selecciona las columnas originales del coche que se quieren devolver al usuario.
Calcula el score_total como una suma ponderada: score_total = (caracteristica1_scaled * @peso_caracteristica1) + (caracteristica2_scaled * @peso_caracteristica2) + ... + termino_penalizacion1 + termino_penalizacion2
4. Construción del SQL - Cláusula WHERE:
Se añaden dinámicamente las condiciones de filtro duro basadas en el diccionario filtros de entrada:
COALESCE(estetica, 0) >= @estetica_min (si estetica_min se decide mantener como filtro). Similar para premium y singular.
plazas >= @plazas_min.
tipo_mecanica IN UNNEST(@tipos_mecanica).
tipo_carroceria IN UNNEST(@tipos_carroceria).
cambio_automatico = TRUE/FALSE (si se especifica).
Condición económica: COALESCE(precio_compra_contado, ...) <= @precio_maximo O la fórmula de cuota ... <= @cuota_maxima.
5. Construción del SQL - ORDER BY y LIMIT:
ORDER BY score_total DESC, precio_compra_contado ASC: Ordena por el score calculado (mayor a menor) y usa el precio (menor a mayor) como criterio de desempate.
LIMIT @k: Limita el número de resultados.
6. Creación de Parámetros BQ: Se crea una lista de objetos bigquery.ScalarQueryParameter y bigquery.ArrayQueryParameter para todos los @variables usados en el SQL (pesos, valores de filtro, flags, k).
7. Ejecución de la Query: Se envía el SQL y los parámetros a BigQuery usando el cliente Python.

**Salida** (Returns)

Una tupla conteniendo:

1. List[Dict[str, Any]]: La lista de coches encontrados, donde cada coche es un diccionario.
   
2. str: El string SQL completo que se ejecutó.
   
3. List[Dict[str, Any]]: Una lista de los parámetros formateados que se usaron en la query (para logging).

////////////////////////////////

otros temas para seguimiento:

Explicación:

Filtro Duro: Un filtro duro se aplica en la cláusula WHERE de tu query SQL. Si un coche no cumple una condición del WHERE (ej: WHERE puertas > 3), ese coche es completamente eliminado del conjunto de resultados y ni siquiera se le calcula un score.
Ajuste de Score (Preferencia Suave/Penalización): La lógica del CASE WHEN que estamos discutiendo está dentro del cálculo del score_total, que ocurre en la cláusula SELECT (o en el CTE ScaledData que luego se usa en el SELECT).
Todos los coches que ya pasaron los filtros duros del WHERE llegan a esta etapa de cálculo de score.
La condición deportividad_bq_scaled >= 0.7 solo determina si a un coche específico se le aplica la penalización de -0.10 a su score_total o no.
Si deportividad_bq_scaled es 0.6 (debajo del umbral de 0.7): El CASE WHEN devuelve 0.0. El coche no es penalizado por este factor, y su score se calcula con los demás términos. Sigue siendo un candidato.
Si deportividad_bq_scaled es 0.8 (encima del umbral de 0.7) Y @flag_penalizar_deportividad_por_alta_comodidad es TRUE: El CASE WHEN devuelve -0.10. Este valor se suma al resto de los componentes del score del coche, efectivamente reduciendo su score_total. El coche sigue siendo un candidato, pero su "atractivo" (score) ha disminuido. Podría seguir apareciendo en los resultados si sus otros atributos son muy buenos, o podría bajar en el ranking.
En resumen:

Los umbrales dentro de los CASE WHEN para las penalizaciones no eliminan coches, solo ajustan su puntuación final si cumplen las condiciones para ser penalizados (es decir, si son "demasiado deportivos" cuando el usuario ha priorizado mucho la comodidad).

Esto te da la flexibilidad de decir: "Prefiero coches cómodos, y si un coche es excesivamente deportivo, eso le resta puntos para mí, pero no significa que lo descarte por completo si es sobresaliente en otras cosas que valoro".

¿Queda más claro así? Si te parece bien este enfoque, podemos continuar con la implementación en buscar_coches_bq.