# utils/bigquery_tool.py
from google.cloud import bigquery
import logging
import logging
from google.cloud import bigquery

def buscar_producto_bd_solo_filtros(filtros: dict, pesos: dict, k: int = 5) -> list[dict]:
    client = bigquery.Client(project="thecarmentor-mvp2")

    sql = """
    SELECT
      nombre,
      ID,
      marca,
      modelo,
      cambio_automatico,
      tipo_mecanica,
      tipo_carroceria,
      indice_altura_interior,
      batalla,
      estetica,
      premium,
      singular,
      altura_libre_suelo,
      traccion,
      reductoras,
      (
        estetica * @peso_estetica
        + premium * @peso_premium
        + singular * @peso_singular
        + indice_altura_interior/1000 * @peso_altura
        + batalla/1000 * @peso_batalla
        + CASE
            WHEN traccion = 'ALL' THEN 1.0
            WHEN traccion = 'RWD' THEN 0.5
            ELSE 0.0
          END * @peso_traccion
        + (CASE WHEN reductoras THEN 1 ELSE 0 END) * @peso_reductoras
      ) AS score_total
    FROM `web_cars.match_coches_pruebas`
    WHERE 1=1
      AND cambio_automatico = TRUE
    """

    # Solo eléctricos (opcional)
    if str(filtros.get("solo_electricos", "")).strip().lower() in ["sí", "si"]:
        sql += "\n      AND tipo_mecanica = 'BEV'"

    # Filtro tipo_carroceria
    if filtros.get("tipo_carroceria"):
        sql += "\n      AND tipo_carroceria IN UNNEST(@tipo_carroceria)"

    # Orden y límite
    sql += "\n    ORDER BY score_total DESC\n    LIMIT @k\n"

    # Parámetros
    params = [
        bigquery.ScalarQueryParameter("peso_estetica",   "FLOAT64", pesos.get("estetica", 1)),
        bigquery.ScalarQueryParameter("peso_premium",    "FLOAT64", pesos.get("premium",  1)),
        bigquery.ScalarQueryParameter("peso_singular",   "FLOAT64", pesos.get("singular", 1)),
        bigquery.ScalarQueryParameter("peso_altura",     "FLOAT64", pesos.get("altura_libre_suelo", 1)),
        bigquery.ScalarQueryParameter("peso_batalla",    "FLOAT64", pesos.get("batalla", 1)),
        bigquery.ScalarQueryParameter("peso_traccion",   "FLOAT64", pesos.get("traccion", 1)),
        bigquery.ScalarQueryParameter("peso_reductoras", "FLOAT64", pesos.get("reductoras", 1)),
        bigquery.ScalarQueryParameter("k", "INT64", k),
    ]

    if filtros.get("tipo_carroceria"):
        params.append(
            bigquery.ArrayQueryParameter("tipo_carroceria", "STRING", filtros["tipo_carroceria"])
        )

    logging.debug("🔎 BigQuery SQL:\n%s", sql)
    logging.debug("🔎 BigQuery params: %s", [(p.name, getattr(p, 'value', getattr(p, 'values', None))) for p in params])
    print("🧠 SQL que se ejecuta:")
    print(sql)
    job = client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params))
    df = job.result().to_dataframe()
    return df.to_dict(orient="records")
