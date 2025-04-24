# utils/weights.py
# cada tuple a la prioridad relativa que quieres en ese nivel de aventura.
# “ninguna”: 0 en todo, porque no te importa nada off-road.
# “ocasional”: priorizas un poco el espacio (altura) y la tracción, pero no las reductoras.
# “extrema”: la tracción y reductoras dominan, y el espacio importa menos en comparación.

AVENTURA_RAW = {
  "ninguna":   {"altura_libre_suelo":  0,   "traccion":  0,  "reductoras":  0},
  "ocasional": {"altura_libre_suelo":  6,   "traccion":  4,  "reductoras":  1},
  "extrema":   {"altura_libre_suelo":  2,   "traccion": 10,  "reductoras":  8},
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

    # 4️⃣ Combinar
    raw.update({
        "altura_libre_suelo": aventura_weights["altura_libre_suelo"],
        "traccion":           aventura_weights["traccion"],
        "reductoras":         aventura_weights["reductoras"],
    })

    return raw




def normalize_weights(raw_weights: dict) -> dict:
    total = sum(raw_weights.values()) or 1.0
    return {k: v/total for k, v in raw_weights.items()}