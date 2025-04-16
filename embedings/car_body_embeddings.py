from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
import vertexai
import json

PROJECT_ID = "thecarmentor-mvp2"
REGION = "europe-west1"
MODEL_ID = "text-multilingual-embedding-002"

# Inicializar Vertex AI
vertexai.init(project=PROJECT_ID, location=REGION)
model = TextEmbeddingModel.from_pretrained(MODEL_ID)

# Cargar tu archivo base_carroceria.json
with open("base_car_body.JSON", "r") as f:
    base_carroceria = json.load(f)

# Generar embeddings con contexto extendido
inputs = [
    TextEmbeddingInput(
        text=f"{doc['descripcion']}. Casos de uso: {doc['casos_uso']}. Palabras clave: {', '.join(doc['keywords'])}",
        task_type="RETRIEVAL_DOCUMENT"
    )
    for doc in base_carroceria
]

results = model.get_embeddings(inputs)

# Asociar cada embedding con su tipo_carroceria
embeddings_con_datos = []
for i, item in enumerate(base_carroceria):
    embeddings_con_datos.append({
        "tipo_carroceria": item["tipo_carroceria"],
        "descripcion": item["descripcion"],
        "casos_uso": item["casos_uso"],
        "keywords": item["keywords"],
        "embedding": results[i].values  # Vector de floats
    })

# Guardar el resultado enriquecido
with open("car_body_embeddings.json", "w") as f:
    json.dump(embeddings_con_datos, f)
