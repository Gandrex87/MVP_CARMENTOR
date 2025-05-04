# utils/weights.py
# cada tuple a la prioridad relativa que quieres en ese nivel de aventura.
# “ninguna”: 0 en todo, porque no te importa nada off-road.
# “ocasional”: priorizas un poco el espacio (altura) y la tracción, pero no las reductoras.
# “extrema”: la tracción y reductoras dominan, y el espacio importa menos en comparación.
# Ademas se refactoriza compute_raw_weights para que trate batalla e indice_altura_interior como preferencias suaves, cuya importancia (peso) dependerá de si el usuario indicó ser alto (altura_mayor_190='sí').

AVENTURA_RAW = {
  "ninguna":   {"altura_libre_suelo":  0,   "traccion":  0,  "reductoras":  0},
  "ocasional": {"altura_libre_suelo":  6,   "traccion":  4,  "reductoras":  1},
  "extrema":   {"altura_libre_suelo":  8,   "traccion": 10,  "reductoras":  8},
}
# En utils/weights.py

from typing import Optional, Dict, Any # Añadir tipos
# Importar is_yes y Enums
from .conversion import is_yes
from .enums import NivelAventura 
# En utils/weights.py

# ... (AVENTURA_RAW como lo definiste) ...
AVENTURA_RAW = {
  "ninguna":   {"altura_libre_suelo":  0,   "traccion":  0,  "reductoras":  0},
  "ocasional": {"altura_libre_suelo":  6,   "traccion":  4,  "reductoras":  1},
  "extrema":   {"altura_libre_suelo":  8,   "traccion": 10,  "reductoras":  8},
}

from typing import Optional, Dict, Any
from .conversion import is_yes
# Importa PerfilUsuario solo si quieres usarlo en el type hint
# from graph.state import PerfilUsuario 

# --- Función compute_raw_weights Recomendada ---
def compute_raw_weights(
    preferencias: Optional[Dict[str, Any]], # Recibe preferencias como dict (más simple)
    estetica: Optional[float], 
    premium: Optional[float], 
    singular: Optional[float]
    ) -> Dict[str, float]: # Especificar tipo de retorno
    """
    Calcula pesos crudos para cada atributo, incluyendo batalla e índice de altura
    basados en la preferencia de altura del usuario. Usa 0.0 como fallback.
    """
    # Usar 0.0 como fallback si los valores de filtro son None
    raw = {
        "estetica": float(estetica or 0.0),
        "premium":  float(premium or 0.0),
        "singular": float(singular or 0.0)
    }
    print(f"DEBUG (Weights) ► Pesos crudos iniciales (est/prem/sing): {raw}")

    # Pesos de Aventura
    aventura_level_val = preferencias.get("aventura") if preferencias else None
    # Normalizar clave aventura (manejar None y obtener .value si es Enum)
    if hasattr(aventura_level_val, "value"): 
        key_aventura = aventura_level_val.value 
    else:
        key_aventura = str(aventura_level_val or "").strip().lower()
        
    aventura_weights = AVENTURA_RAW.get(key_aventura, AVENTURA_RAW["ninguna"])
    raw["altura_libre_suelo"] = float(aventura_weights.get("altura_libre_suelo", 0.0))
    raw["traccion"] = float(aventura_weights.get("traccion", 0.0))
    raw["reductoras"] = float(aventura_weights.get("reductoras", 0.0))
    print(f"DEBUG (Weights) ► Pesos crudos tras añadir aventura: {raw}")

    # Pesos basados en altura_mayor_190
    altura_pref_val = preferencias.get("altura_mayor_190") if preferencias else None
    if is_yes(altura_pref_val):
        print("DEBUG (Weights) ► Usuario alto. Asignando pesos altos a batalla/índice.")
        # ¡Valores ejemplo!Podemos ajustar según importancia
        raw["batalla"] = 6.0 
        raw["indice_altura_interior"] = 5.0 
    else:
        print("DEBUG (Weights) ► Usuario NO alto. Asignando pesos bajos a batalla/índice.")
         # ¡Valores de ejemplo! Ajusta según importancia (quizás 0.0 si no importan nada?)
        raw["batalla"] = 0.5 
        raw["indice_altura_interior"] = 0.5 
    
    # Asegurar que todos los valores sean float para normalize_weights
    raw_float = {k: float(v or 0.0) for k, v in raw.items()}
    
    print(f"DEBUG (Weights) ► Pesos Crudos FINALES: {raw_float}")
    return raw_float

# normalize_weights se mantiene igual (quizás con el DEBUG print que añadí antes)
def normalize_weights(raw_weights: dict) -> dict:
    """Normaliza los pesos crudos para que sumen 1.0."""
    valid_values = [v for v in raw_weights.values() if isinstance(v, (int, float))]
    total = sum(valid_values) or 1.0 
    normalized = {k: (v / total) if isinstance(v, (int, float)) else 0.0 for k, v in raw_weights.items()}
    print(f"DEBUG (Normalize Weights) ► Pesos Normalizados: {normalized}")
    return normalized