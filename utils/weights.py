# utils/weights.py
# cada tuple a la prioridad relativa que quieres en ese nivel de aventura.
# “ninguna”: 0 en todo, porque no te importa nada off-road.
# “ocasional”: priorizas un poco el espacio (altura) y la tracción, pero no las reductoras.
# “extrema”: la tracción y reductoras dominan, y el espacio importa menos en comparación.
# Ademas se refactoriza compute_raw_weights para que trate batalla e indice_altura_interior como preferencias suaves, cuya importancia (peso) dependerá de si el usuario indicó ser alto (altura_mayor_190='sí').


from typing import Optional, Dict, Any # Añadir tipos
# Importar is_yes y Enums
from .conversion import is_yes
from .enums import NivelAventura 
from graph.perfil.state import PerfilUsuario # Importar para type hint

# En utils/weights.py

# ... (AVENTURA_RAW como lo definiste) ...
AVENTURA_RAW = {
  "ninguna":   {"altura_libre_suelo":  0,   "traccion":  0,  "reductoras":  0},
  "ocasional": {"altura_libre_suelo":  6,   "traccion":  4,  "reductoras":  1},
  "extrema":   {"altura_libre_suelo":  8,   "traccion": 10,  "reductoras":  8},
}

# --- Función compute_raw_weights CORREGIDA ---
def compute_raw_weights(
    preferencias: Optional[PerfilUsuario], # <-- Cambiar Type Hint a PerfilUsuario
    estetica: Optional[float], 
    premium: Optional[float], 
    singular: Optional[float],
    priorizar_ancho: Optional[bool] # <-- NUEVO ARGUMENTO BOOLEANO
    ) -> Dict[str, float]: 
    """
    Calcula pesos crudos. Accede a preferencias usando notación de punto.
    """
    # Usar 0.0 como fallback si los valores de filtro son None
    raw = {
        "estetica": float(estetica or 0.0),
        "premium":  float(premium or 0.0),
        "singular": float(singular or 0.0)
    }
    print(f"DEBUG (Weights) ► Pesos crudos iniciales (est/prem/sing): {raw}")

    # Pesos de Aventura
    key_aventura = "ninguna" # Default
    if preferencias and preferencias.aventura: # <-- Acceso con punto y verificar que no sea None
        aventura_level_val = preferencias.aventura # <-- Acceso con punto
        if hasattr(aventura_level_val, "value"): 
            key_aventura = aventura_level_val.value 
        else:
            key_aventura = str(aventura_level_val).strip().lower()
            
    aventura_weights = AVENTURA_RAW.get(key_aventura, AVENTURA_RAW["ninguna"])
    raw["altura_libre_suelo"] = float(aventura_weights.get("altura_libre_suelo", 0.0))
    raw["traccion"] = float(aventura_weights.get("traccion", 0.0))
    raw["reductoras"] = float(aventura_weights.get("reductoras", 0.0))
    print(f"DEBUG (Weights) ► Pesos crudos tras añadir aventura: {raw}")

    # Pesos basados en altura_mayor_190
    altura_pref_val = preferencias.altura_mayor_190 if preferencias else None # <-- Acceso con punto
    if is_yes(altura_pref_val):
        # ¡Valores ejemplo!Podemos ajustar según importancia
        print("DEBUG (Weights) ► Usuario alto. Asignando pesos altos a batalla/índice.")
        raw["batalla"] = 6.0 # Ejemplo
        raw["indice_altura_interior"] = 5.0 # Ejemplo
    else:
         # ¡Valores de ejemplo! Ajusta según importancia (quizás 0.0 si no importan nada?)
        print("DEBUG (Weights) ► Usuario NO alto. Asignando pesos bajos a batalla/índice.")
        raw["batalla"] = 0.5 # Ejemplo
        raw["indice_altura_interior"] = 0.5 # Ejemplo
    # --- NUEVA LÓGICA PARA PESO DE ANCHO ---
    # 4️⃣ Añadir peso para 'ancho' basado en 'priorizar_ancho'
    if priorizar_ancho: # Si el flag que viene del estado es True
        # Asignar un peso crudo ALTO a la anchura
        # ¡Ajusta este valor! Debe ser significativo comparado con otros (ej: aventura, estetica)
        raw["ancho"] = 6.0  # Ejemplo de peso alto
        print(f"DEBUG (Weights) ► Priorizar Ancho=True. Asignando peso crudo alto a ancho: {raw['ancho']}")
    else:
        # Asignar un peso crudo BAJO (o cero) si no se prioriza
        raw["ancho"] = 0.5  # Ejemplo de peso muy bajo pero no cero
        print(f"DEBUG (Weights) ► Priorizar Ancho=False/None. Asignando peso crudo bajo a ancho: {raw['ancho']}")
    # --- FIN NUEVA LÓGICA ---
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
