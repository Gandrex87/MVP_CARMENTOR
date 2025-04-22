# utils/weights.py
# Escalar todo a un rango de 0 a 10 (igual que tus umbrales de estética, premium y singular), tu tabla de pesos de aventura podría quedar así:
AVENTURA_RAW = {
    "ninguna":   {"altura":  0,  "traccion":  0,  "reductoras":  0},
    "ocasional": {"altura":  5,  "traccion":  4,  "reductoras":  0},
    "extrema":   {"altura":  4,  "traccion": 10,  "reductoras":  7},
}

# utils/weights.py

def compute_raw_weights(estetica, premium, singular, aventura_level):
    """
    Devuelve un dict de pesos crudos para cada atributo.
    aventura_level puede ser un str ('ocasional', 'extrema'...) o un Enum NivelAventura.
    """
    # 1️⃣ Umbrales estáticos
    raw = {
        "estetica": estetica,
        "premium":  premium,
        "singular": singular
    }

    # 2️⃣ Normalizar la clave de aventura
    if hasattr(aventura_level, "value"):
        key = aventura_level.value
    else:
        key = aventura_level

    key = (str(key) or "").strip().lower()

    # 3️⃣ Obtener los pesos de aventura (o fallback a 'ninguna')
    aventura_weights = AVENTURA_RAW.get(key, AVENTURA_RAW["ninguna"])

    # 4️⃣ Merge
    raw.update(aventura_weights)
    print("→ Key usada:", key, "→ raw:", raw)
    return raw




def normalize_weights(raw_weights: dict) -> dict:
    total = sum(raw_weights.values()) or 1.0
    return {k: v/total for k, v in raw_weights.items()}