# Descripción de las funciones utilitarias del Agente

Este módulo contiene funciones auxiliares reutilizables que permiten separar la lógica de negocio de tareas comunes como postprocesamiento, formateo y manejo de enumeraciones / contiene funciones genéricas y reutilizables.

- `postprocessing.py`: Contiene reglas defensivas para completar filtros y preferencias faltantes.
- `formatters.py`: Formatea la salida al usuario en tablas o bloques amigables.
- `enums.py`: Define las clases Enum utilizadas en el análisis de vehículos.
- `postprocessing.py` : Evitar errores como 'str' object has no attribute 'value'. Puede convertir una lista de enums como esta ->          [TipoCarroceria.SUV, TipoCarroceria.COUPE]-> ["SUV", "COUPE"]

- `bigquery_tools.py`

Funcionamiento Detallado de Componentes Clave
Para ofrecer recomendaciones personalizadas, el agente utiliza varias funciones especializadas. Dos de las más importantes en la lógica de selección y ranking de vehículos son compute_raw_weights y buscar_coches_bq.

## `weights.py`
  
1. `compute_raw_weights`
Esta función es el primer paso para traducir las diversas preferencias del usuario en un sistema numérico que permita comparar coches.

### Propósito Principal `compute_raw_weights`

Consolidar todas las preferencias del usuario (tanto las respuestas directas 'sí'/'no', las selecciones de enums como el nivel de aventura, y los ratings explícitos de 0-10) en un conjunto de "pesos crudos" o "puntuaciones de importancia inicial" para diferentes características de un vehículo. Estos pesos crudos aún no están listos para ser usados directamente en el ranking final, ya que no están en una escala comparable, pero reflejan la importancia inicial que el agente le da a cada aspecto.

### Entradas Principales (`Args`)


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
* `transporta_carga_voluminosa` == 'sí': Favorecer las columnas BQ maletero_minimo y maletero_maximo
* `necesita_espacio_objetos_especiales` == 'sí' (lo que implica que la anterior también fue 'sí'):
Favorecer tipo_carroceria: `[MONOVOLUMEN, FAMILIAR, FURGONETA, SUV]` (Esto lo manejaremos en RAG - Paso 6).
Desfavorecer/Eliminar tipo_carroceria: `[3VOL, COUPE, DESCAPOTABLE]` (También en RAG).
Favorecer las columnas BQ `largo` y `ancho`.

### Lógica Central de weights.py

1. **Pesos Base por Filtros Derivados**: Inicializa los pesos crudos para "`estetica`", "`premium`" y "`singular`" usando directamente los valores `estetica_min_val`, `premium_min_val` y `singular_min_val` recibidos. Estos valores ya reflejan una "importancia" derivada de las preferencias del usuario.
2. **Pesos por `Aventura`**: Consulta el diccionario `AVENTURA_RAW` usando el nivel de aventura del usuario para obtener los pesos crudos para `"altura_libre_suelo"`, `"traccion"` y `"reductoras"`.
3. **Pesos por Dimensiones del Conductor:** Si `altura_mayor_190` es 'sí', asigna pesos crudos predefinidos (más altos) a `"batalla"` e `"indice_altura_interior"`. Si es 'no', asigna pesos bajos.
4. **Peso por Ancho del Vehículo:** Si `priorizar_ancho` es `True`, asigna un peso crudo predefinido (`alto`) a `"ancho"`. Si es False, asigna un peso bajo.
5. **Pesos por Ratings Explícitos:** Para cada una de las 5 (o 6) nuevas características (Fiabilidad y Durabilidad, Seguridad, Comodidad, Impacto Ambiental, Tecnología y Conectividad), toma el rating numérico (0-10) proporcionado por el usuario directamente del diccionario `preferencias` y lo usa como el peso crudo para esa característica `(ej: raw["rating_seguridad"] = preferencias.get("rating_seguridad", 0.0))``.
6. **Salida** (Returns):`Dict[str, float]:` Un diccionario donde las claves son los nombres de las características (ej: `"estetica"`, `"traccion"`, `"rating_seguridad"`) y los valores son sus pesos crudos calculados.
Este diccionario luego se pasa a la función `normalize_weights` para escalar todos estos pesos crudos a una suma total de 1.0, haciéndolos comparables para el scoring final.


## `bigquery_tools.py`

2.`buscar_coches_bq`
Esta es la función principal que interactúa con la base de datos de coches en BigQuery para encontrar y clasificar vehículos según los criterios y preferencias del usuario.

### Propósito Principal `buscar_coches_bq`

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

### Lógica Central de bigquery_tools.py

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
cambio_automatico = TRUE/FALSE (si se especifica).
Condición económica: COALESCE(precio_compra_contado, ...) <= @precio_maximo O la fórmula de cuota ... <= @cuota_maxima.
5. Construción del SQL - ORDER BY y LIMIT:
ORDER BY score_total DESC, precio_compra_contado ASC: Ordena por el score calculado (mayor a menor) y usa el precio (menor a mayor) como criterio de desempate.
LIMIT @k: Limita el número de resultados.
6. Creación de Parámetros BQ: Se crea una lista de objetos bigquery.ScalarQueryParameter y bigquery.ArrayQueryParameter para todos los @variables usados en el SQL (pesos, valores de filtro, flags, k).
7. Ejecución de la Query: Se envía el SQL y los parámetros a BigQuery usando el cliente Python.

**Salida** (Returns)

Una tupla conteniendo:

1. `List[Dict[str, Any]]`: La lista de coches encontrados, donde cada coche es un diccionario.
   
2. str: El string SQL completo que se ejecutó.
   
3. `List[Dict[str, Any]]`: Una lista de los parámetros formateados que se usaron en la query (para logging).

4. Análisis Conceptual del Enfoque para calificaciones de tecnologia>= 7:

Definición de Rangos y Penalizaciones:
Primero, definimos claramente los rangos de antigüedad:

0-5 años: Sin penalización (valor de ajuste = 0.0)
5 a 7 años: Penalización X (ej: -0.10)

7 a 10 años: Penalización Y (ej: -0.20, más fuerte que X)

10 años: Penalización Z (ej: -0.30, la más fuerte)
Estos valores de penalización (X, Y, Z) serían constantes negativas que restaríamos al score.

## `rag_carroceria.py` - Recomendación de Tipos de Carrocería

Este módulo es responsable de una parte crucial de la personalización de las recomendaciones: sugerir los **tipos de carrocería** más adecuados para el usuario antes de realizar la búsqueda final en la base de datos de vehículos. Para ello, utiliza un enfoque de **Generación Aumentada por Recuperación (RAG)**.

### Funcionamiento Principal

El corazón de este módulo es la función `get_recommended_carrocerias`. Su objetivo es tomar las diversas preferencias del usuario y traducirlas en una consulta semántica para buscar en una base de datos vectorial de tipos de carrocería.

#### 1. Fuente de Conocimiento (Vector Store)

- **Origen de los Datos:** La información sobre los diferentes tipos de carrocería (ej: SUV, BERLINA, COUPE, TODOTERRENO, etc.), sus descripciones y una serie de *tags* asociados, se carga inicialmente desde un archivo PDF (manejado por `utils/rag_reader.py`).
  
- **Embeddings y Almacenamiento Vectorial:**
  - Cada tipo de carrocería, junto con su descripción y tags, se convierte en un "documento".
  - Se utilizan modelos de *embeddings* (específicamente `OpenAIEmbeddings`) para convertir el contenido textual de estos documentos en representaciones numéricas (vectores). Estos vectores capturan el significado semántico del texto.
  - Estos vectores se almacenan y se indexan en un almacén vectorial eficiente, en este caso, **FAISS** (`langchain_community.vectorstores.FAISS`). Este índice permite búsquedas rápidas por similitud semántica.
  
- **Acceso al Vector Store:** La función `get_vectorstore()` se encarga de cargar o construir este índice FAISS para que esté disponible para las búsquedas.

#### 2. La Función `get_recommended_carrocerias`

- **Propósito:** Dada las preferencias del usuario, generar una lista de los `k` tipos de carrocería más relevantes.

- **Entradas Principales (`Args`):**
  * `preferencias: Dict[str, Any]`: Un diccionario que contiene las preferencias del perfil del usuario. Los campos clave utilizados incluyen:
  * `solo_electricos` ('sí'/'no')
  * `valora_estetica` ('sí'/'no')
  * `apasionado_motor` ('sí'/'no')
  * `aventura` (ej: "ninguna", "ocasional", "extrema")
  * `uso_profesional` ('sí'/'no')
  * `tipo_uso_profesional` (ej: "carga", "pasajeros", "mixto")
  * `necesita_espacio_objetos_especiales` ('sí'/'no')
  * `rating_comodidad` (calificación 0-10)
  * `info_pasajeros: Optional[Dict[str, Any]]`: Un diccionario con información sobre los pasajeros habituales (frecuencia, número de niños en silla, número de otros pasajeros).
  * `k: int`: El número deseado de tipos de carrocería a recomendar.

- **Lógica de Construcción de la Query RAG:**
    1. **Inicialización:** Se obtiene una instancia del vector store FAISS.
    2. **Construcción de `partes_query`:** Se crea dinámicamente una lista de palabras y frases clave (`partes_query`) basada en las preferencias del usuario:
        * Se añaden términos básicos si ciertas preferencias son afirmativas (ej: "eléctrico" si `solo_electricos='sí'`; "diseño" si `valora_estetica='sí'`).
        * **Sinónimos:** Se utilizan diccionarios predefinidos de sinónimos (ej: `AVENTURA_SYNONYMS`, `ESTETICA_VALORADA_SYNONYMS`, `USO_PROF_CARGA_SYNONYMS`, etc.) para enriquecer la query. Por ejemplo, si `aventura="extrema"`, se añaden términos como "off-road", "terrenos difíciles".
        * **Lógica Condicional para Espacio:**
            * Si `necesita_espacio_objetos_especiales='sí'`, se añaden términos clave como "gran capacidad de carga", "maletero amplio", "versatilidad interior".
            * Si `rating_comodidad` es alto (ej: >= 8), se añaden términos relacionados con el confort y los tipos de carrocería espaciosos (ej: "confort de marcha", "berlina confortable", "SUV familiar cómodo").
        * **Lógica para Pasajeros:** Si se llevan pasajeros frecuentemente o niños en silla, se añaden términos como "espacio para pasajeros", "coche familiar grande", "muchas plazas".
    3. **Formación de la Query String:** Las `partes_query` se unen para formar una única cadena de texto (`query_str`). Se eliminan duplicados y se utiliza una query de fallback si no se generaron partes.
    4. **Búsqueda por Similitud:** Se ejecuta `vs.similarity_search(query_str, k=k+2)` contra el índice FAISS. Esta búsqueda devuelve los documentos (tipos de carrocería con sus descripciones/tags) cuyos vectores son semánticamente más similares al vector de la `query_str` generada. Se piden `k+2` resultados para tener un pequeño margen para el post-filtrado.
    5. **Extracción de Tipos Únicos:** De los documentos devueltos, se extraen los nombres de los tipos de carrocería (almacenados en la metadata de cada documento), asegurando que no haya duplicados.
    6. **Post-Filtrado (Lógica de Exclusión):**
        * Si `necesita_espacio_objetos_especiales='sí'`, se aplica un filtro para **eliminar** explícitamente tipos de carrocería menos prácticos para carga (como "3VOL", "COUPE", "DESCAPOTABLE") de la lista de recomendaciones. Se incluye una lógica para revertir a los resultados RAG originales si este filtro elimina todas las opciones.
        * *(Opcional)* Se podría añadir una lógica similar para el post-filtrado basado en `rating_comodidad` si el enriquecimiento de la query no es suficiente para favorecer los tipos deseados.
    7. **Fallback Final:** Si después de todo el proceso no se obtienen tipos de carrocería, se devuelve una lista de fallback genérica (ej: ["SUV", "BERLINA", "FAMILIAR", "COMPACTO"]).

- **Salida (`Returns`):**
  
`List[str]`: Una lista de los `k` nombres de tipos de carrocería más recomendados según la búsqueda RAG y el post-filtrado.

### Importancia en el Flujo del Agente

La lista de `tipo_carroceria` devuelta por `get_recommended_carrocerias` se guarda en el estado (`filtros_inferidos.tipo_carroceria`) y luego se utiliza como un **filtro duro** en la cláusula `WHERE` de la query final a BigQuery (`AND tipo_carroceria IN UNNEST(@tipos_carroceria)`). Esto asegura que la búsqueda final de coches se restrinja a los tipos de carrocería que el sistema RAG ha considerado más apropiados para las necesidades expresadas por el usuario, especialmente en términos de espacio, uso y aventura.

Este componente permite al agente ir más allá de simples coincidencias de palabras clave, utilizando la comprensión semántica para guiar una de las decisiones de filtrado más importantes.

## Diferencia entre Pesos y Bonificaciones/Penalizaciones Fijas

Es fundamental tener clara la diferencia entre los **pesos** (que se normalizan y multiplican por características escaladas) y estas **bonificaciones/penalizaciones fijas**. Ambas son formas de ajustar el `score_total`, pero funcionan de manera diferente y sirven para propósitos ligeramente distintos.

---

## 1. Pesos (Calculados por `compute_raw_weights` y `normalize_weights`)

* **Origen**: Vienen de las preferencias del usuario (ratings 0-10, respuestas sí/no a preguntas como "apasionado del motor", "altura > 1.90", etc.) y de la lógica de "importancia relativa" que hemos definido (ej: `AVENTURA_RAW`).
* **Proceso**:

  1. `compute_raw_weights` asigna un *peso crudo* a cada característica.

     * Ej: `rating_seguridad = 8` → `raw["rating_seguridad"] = 8.0`
     * Ej: `apasionado_motor = 'sí'` → `raw["premium"] = 3.0`
  2. `normalize_weights` suma todos los pesos crudos y divide cada uno por la suma total, obteniendo pesos normalizados que suman 1.0.

     * Ej: `peso_normalizado_seguridad = 0.15`, `peso_normalizado_premium = 0.05`
* **Aplicación en SQL**:

  1. Cada característica del coche se escala a un rango 0-1 (`seguridad_scaled`, `premium_scaled`).
  2. El `score_total` se construye sumando el producto de cada característica escalada por su peso normalizado:

     ```sql
     score_total =
       (seguridad_scaled * @peso_rating_seguridad)
       + (premium_scaled * @peso_premium)
       + ...
     ```
* **Efecto**:

  * **Ponderación Relativa**: Los pesos normalizados determinan qué proporción del "presupuesto total de importancia" (que es 1.0) se asigna a cada característica.
  * **Comparación Continua**: Favorece a los coches que son mejores en las características con mayor peso.

---

## 2. Bonificaciones/Penalizaciones Fijas (Tus `BONUS_...` y `PENALTY_...`)

* **Origen**: Vienen de condiciones específicas y binarias que se cumplen o no, activadas por un flag booleano calculado en Python.

  * Ej: `flag_aplicar_logica_distintivo = TRUE` (por `rating_impacto_ambiental >= 8`).
  * Ej: `flag_es_municipio_zbe = TRUE` (CP en ZBE).
* **Proceso**:

  1. Los flags booleanos se pasan a la query BigQuery (`@flag_aplicar_logica_distintivo`, etc.).
  2. En el SQL, se usan cláusulas `CASE WHEN` para sumar o restar valores fijos al `score_total` si la condición se cumple.
* **Aplicación en SQL**:

  ```sql
  score_total = ( ... suma de términos ponderados ... )
    + (CASE WHEN @flag_aplicar_logica_distintivo THEN
        CASE
          WHEN UPPER(distintivo_ambiental) IN ('CERO','0','ECO','C') THEN 0.15  -- BONUS_DISTINTIVO_GENERAL
          WHEN UPPER(distintivo_ambiental) IN ('B','NA') THEN -0.15            -- PENALTY_DISTINTIVO_GENERAL
          ELSE 0.0
        END
      ELSE 0.0 END)
    + (CASE WHEN @flag_es_municipio_zbe THEN
        CASE
          WHEN UPPER(distintivo_ambiental) IN ('CERO','0','ECO','C') THEN 0.25  -- BONUS_ZBE
          WHEN UPPER(distintivo_ambiental) IN ('B','NA') THEN -0.50            -- PENALTY_ZBE
          ELSE 0.0
        END
      ELSE 0.0 END)
    + (CASE WHEN @flag_aplicar_logica_distintivo AND COALESCE(ocasion, FALSE)
            THEN 0.10                                                     -- BONUS_OCASION
            ELSE 0.0 END)
    -- ... y las penalizaciones por antigüedad, comodidad vs low-cost/deportividad ...
  ```
* **Efecto**:

  * **Ajuste Directo y Discreto**: Es un "empujón" o "castigo" fijo, independiente de qué tan "bueno" sea el coche en esa característica.
  * **Manejo de Reglas de Negocio**: Ideal para reglas como ZBE o categoría de ocasión.
  * **Impacto Fuerte**: Un penalización de -0.50 puede hundir un coche en el ranking.

---

## 3. Diferencias Clave y Cuándo Usar Cada Uno

| Característica      | Pesos (compute + normalize)                                | Bonificaciones/Penalizaciones Fijas (CASE WHEN)                           |
| ------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------- |
| **Propósito**       | Importancia relativa de características continuas (0-1).   | Ajustes discretos basados en condiciones específicas o reglas de negocio. |
| **Cálculo**         | Ratings → pesos crudos → normalización (sum = 1.0).        | Valores fijos (+/-) aplicados si cumple la condición.                     |
| **Efecto en Score** | Multiplicativo con la característica escalada.             | Aditivo directo (todo o nada).                                            |
| **Sensibilidad**    | Sensible a cuánto mejor es un coche en la característica.  | Sensible a si cumple o no la condición.                                   |
| **Ejemplos**        | "Quiero mucha seguridad" → `seguridad_scaled * alto_peso`. | "Estoy en ZBE" → +0.25 o -0.50 según distintivo.                          |

---

## 4. Exportar a Hojas de Cálculo

* **¿Se están "cargando" mucho los pesos?**

  * Sí: si `rating_fiabilidad_durabilidad`, `rating_impacto_ambiental` y `rating_costes_uso` son altos, la suma de esos pesos normalizados acentúa las columnas BQ correspondientes.
* **Con Bonificaciones/Penalizaciones**:

  * Cada bonus/penalty es independiente y se suma como líneas separadas en la hoja.

---

## 5. Recomendación

Tu enfoque actual de usar ambos mecanismos es **potente**:

1. Los **pesos** capturan la importancia relativa de las preferencias del usuario.
2. Las **bonificaciones/penalizaciones** implementan reglas de negocio o ajustes fuertes.

Asegúrate de que los valores fijos estén en una escala adecuada en relación con los scores ponderados (generalmente 0 a 1). Un bonus de +0.25 o una penalización de -0.50 debe usarse con cautela para no desbalancear el ranking.

6. Lógica Actual (con el "doble chequeo")
   
```sql
-- Penalización para 'acceso_low_cost'
+ (CASE 
       WHEN @flag_penalizar_low_cost_comodidad = TRUE -- (1er chequeo: ¿Prioriza el usuario la comodidad?)
            AND acceso_low_cost_scaled >= 0.7     -- (2do chequeo: ¿Este coche es MUY "low_cost"?)
       THEN -0.20 -- Aplicar penalización
       ELSE 0.0 
   END)
```
Cómo funciona:

Se verifica el flag @flag_penalizar_low_cost_comodidad, que es TRUE si el usuario dio un rating alto a "Comodidad" (>= 7). Si el flag es FALSE, la penalización no se aplica.

Si el flag es TRUE, se evalúa acceso_low_cost_scaled >= 0.7.

Solo si ambas condiciones se cumplen, se resta 0.20 al score_total.

1. Columna Original en BQ `acceso_low_cost`: Tiene una escala, por ejemplo, de 1.0 a 10.0 (según tu `MIN_MAX_RANGES`, donde asumimos que un valor más alto, como 10.0, significa "más low_cost" o más básico, lo cual es menos deseable si se busca confort).

2. Escalado Min-Max (`acceso_low_cost_scaled`): En el SQL, transformamos el valor original de `acceso_low_cost` a un valor normalizado entre 0.0 y 1.0.

- Si `acceso_low_cost` original es 1.0 (el mínimo, menos "low_cost"), entonces acceso_low_cost_scaled será 0.0.
  
- Si `acceso_low_cost` original es 10.0 (el máximo, más "low_cost"), entonces acceso_low_cost_scaled será 1.0.
  
- Si `acceso_low_cost` original es, por ejemplo, 7.3, y el rango es (1.0, 10.0): `escalado = (7.3 - 1.0) / (10.0 - 1.0) = 6.3 / 9.0 = 0.7`
  
3. Umbral de Penalización (UMBRAL_LOW_COST_PENALIZABLE = 0.7):
Este umbral, tal como lo tienes definido en tus constantes Python (ej: UMBRAL_LOW_COST_PENALIZABLE = 0.7), se compara directamente con el valor escalado (acceso_low_cost_scaled) en el SQL:

```sql

  ... AND acceso_low_cost_scaled >= {UMBRAL_LOW_COST_PENALIZABLE} ... 
  -- que se convierte en:
  ... AND acceso_low_cost_scaled >= 0.7 ...
  Esto significa que la penalización se aplica si el valor escalado del coche para acceso_low_cost es 0.7 o más.
```

Efecto:
Esta lógica garantiza que solo los coches excesivamente "low-cost" (valor escalado ≥ 0.7) reciban la penalización, y únicamente cuando al usuario le importa mucho la comodidad.


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


