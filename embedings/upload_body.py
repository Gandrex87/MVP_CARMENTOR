import pandas as pd
import json
from google.cloud import bigquery

# Cargar el archivo JSON
file = "car_body_embeddings.json"
with open(file, "r") as f:
    data = json.load(f)
    
# Convertir listas a strings donde sea necesario
for item in data:
    item["casos_uso"] = "; ".join(item.get("casos_uso", [])) if isinstance(item.get("casos_uso"), list) else item.get("casos_uso", "")
    item["keywords"] = [str(k) for k in item.get("keywords", [])] if isinstance(item.get("keywords"), list) else []

df = pd.DataFrame(data)

# Inicializar cliente de BigQuery
client = bigquery.Client()

# Nombre completo de la tabla destino
table_id = "thecarmentor-mvp2.web_cars.tipo_carroceria_embeddings"

# Definir el esquema (embedding como tipo FLOAT64 ARRAY, keywords como STRING ARRAY)
job_config = bigquery.LoadJobConfig(schema=[
    bigquery.SchemaField("tipo_carroceria", "STRING"),
    bigquery.SchemaField("descripcion", "STRING"),
    bigquery.SchemaField("casos_uso", "STRING"),  # Ahora sí es texto
    bigquery.SchemaField("keywords", "STRING", mode="REPEATED"),
    bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
])
# 

# Subir el DataFrame
job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
job.result()  # Espera que termine

print("✅ Embeddings subidos a BigQuery correctamente con contexto ampliado.")

