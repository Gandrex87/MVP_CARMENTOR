# utils/bigquery_tool.py
from google.cloud import bigquery
import logging

def buscar_producto_bd_solo_filtros(filtros: dict, pesos: dict, k: int = 5) -> list[dict]:
    """
    Recupera coches de BigQuery aplicando hard-filters y soft-weights.
    - Hard filters: cambio_automatico verdadero y filtro de solo_electricos → tipo_mecanica BEV
    - Soft filters: estética, premium, singular, confort (altura y batalla) ponderados en score_total
    """
    client = bigquery.Client(project="thecarmentor-mvp2")
    sql = """
    SELECT
      nombre,
      ID,
      marca,
      modelo,
      cambio_automatico,
      reductoras,
      tipo_mecanica,
      indice_altura_interior,
      batalla,
      estetica,
      premium,
      singular,
      (
        estetica              * @peso_estetica
        + premium             * @peso_premium
        + singular            * @peso_singular
        + indice_altura_interior/1000 * @peso_altura
        + batalla/1000               * @peso_batalla
        + (
          CASE
            WHEN traccion = 'ALL' THEN 1.0
            WHEN traccion = 'RWD' THEN 0.5
            ELSE 0.0
          END
          ) * @peso_traccion
        + (CASE WHEN reductoras THEN 1 ELSE 0 END) * @peso_reductoras
        ) AS score_total
      FROM `web_cars.match_coches_pruebas`
      WHERE 1=1
        AND cambio_automatico = TRUE
        AND (
          @solo_electricos = FALSE
          OR (@solo_electricos = TRUE AND tipo_mecanica = 'BEV')
        )
    ORDER BY score_total DESC
    LIMIT @k
    """
    params = [
        bigquery.ScalarQueryParameter("solo_electricos", "BOOL", filtros.get("solo_electricos", "no")=="sí"),
        bigquery.ScalarQueryParameter("peso_estetica", "FLOAT64", pesos.get("estetica", 1)),
        bigquery.ScalarQueryParameter("peso_premium",  "FLOAT64", pesos.get("premium", 1)),
        bigquery.ScalarQueryParameter("peso_singular", "FLOAT64", pesos.get("singular", 1)),
        bigquery.ScalarQueryParameter("peso_altura_libre_suelo", "FLOAT64", pesos["altura_libre_suelo"]),
        bigquery.ScalarQueryParameter("peso_batalla",           "FLOAT64", pesos["batalla"]),
        bigquery.ScalarQueryParameter("peso_traccion",          "FLOAT64", pesos["traccion"]),
        bigquery.ScalarQueryParameter("peso_reductoras",        "FLOAT64", pesos["reductoras"]),
        bigquery.ScalarQueryParameter("k",                      "INT64",   k),
    ]

    # Loguear SQL y parámetros
    logging.debug("🔎 BigQuery SQL: %s", sql)
    logging.debug("🔎 BigQuery params: %s", [(p.name, getattr(p, 'value', getattr(p, 'values', None))) for p in params])

    job = client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params))
    df  = job.result().to_dataframe()

    logging.debug("📊 Filas devueltas: %d", len(df))
    if not df.empty:
        logging.debug("📋 Muestra: %s", df.head().to_string())

    return df.to_dict(orient="records")