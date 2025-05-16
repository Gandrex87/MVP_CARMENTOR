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
    estetica_min_val: Optional[float],      # Renombrado para claridad (viene de filtros.estetica_min)
    premium_min_val: Optional[float],       # Renombrado para claridad (viene de filtros.premium_min)
    singular_min_val: Optional[float],      # Renombrado para claridad (viene de filtros.singular_min)
    priorizar_ancho: Optional[bool] # <-- NUEVO ARGUMENTO BOOLEANO
    ) -> Dict[str, float]: 
    """
    Calcula pesos crudos. Accede a preferencias usando notación de punto.
    """
    
    raw = {} # Inicializar el diccionario de pesos crudos
    # Usar 0.0 como fallback si los valores de filtro son None
    raw = {
        "estetica": float(estetica_min_val or 0.0),
        "premium":  float(premium_min_val or 0.0),
        "singular": float(singular_min_val or 0.0)
    }
    print(f"DEBUG (Weights) ► Pesos crudos iniciales (est/prem/sing): {raw}")

    # Pesos de Aventura
    aventura_level_str = None
    if preferencias: # Verificar si el diccionario preferencias existe
        aventura_level_input = preferencias.get("aventura") # <-- USO DE .get()
        if hasattr(aventura_level_input, "value"): # Por si acaso llega el Enum
            aventura_level_str = aventura_level_input.value
        elif aventura_level_input is not None:
            aventura_level_str = str(aventura_level_input).strip().lower()
        else:
            aventura_level_str = "ninguna" # Default si aventura es None en el dict
    else: # Si preferencias es None
        aventura_level_str = "ninguna" # Default
        
    aventura_weights_map = AVENTURA_RAW.get(aventura_level_str, AVENTURA_RAW["ninguna"])
    raw["altura_libre_suelo"] = float(aventura_weights_map.get("altura_libre_suelo", 0.0))
    raw["traccion"] = float(aventura_weights_map.get("traccion", 0.0))
    raw["reductoras"] = float(aventura_weights_map.get("reductoras", 0.0))
    print(f"DEBUG (Weights) ► Pesos crudos tras añadir aventura: {raw}")

    #
    # Pesos basados en altura_mayor_190
    altura_pref_val = preferencias.get("altura_mayor_190") if preferencias else None # <-- USO DE .get()
    if is_yes(altura_pref_val):
        print("DEBUG (Weights) ► Usuario alto. Asignando pesos a batalla/índice.")
        raw["batalla"] = 5.0 
        raw["indice_altura_interior"] = 5.0 
    else:
        print("DEBUG (Weights) ► Usuario NO alto. Asignando pesos bajos a batalla/índice.")
        raw["batalla"] = 1.0 
        raw["indice_altura_interior"] = 1.0 
    print(f"DEBUG (Weights) ► Pesos crudos tras añadir dims por altura: {raw}")

    # Peso para 'ancho' basado en 'priorizar_ancho'
    if priorizar_ancho: 
        raw["ancho"] = 5.0  
        print(f"DEBUG (Weights) ► Priorizar Ancho=True. Asignando peso crudo alto a ancho: {raw['ancho']}")
    else:
        raw["ancho"] = 1.0  
        print(f"DEBUG (Weights) ► Priorizar Ancho=False/None. Asignando peso crudo bajo a ancho: {raw['ancho']}")
        
    # --- NUEVO PESO CRUDO PARA DEPRECIACIÓN ---
    if is_yes(preferencias.get("prioriza_baja_depreciacion")):
        raw["devaluacion"] = 5.0 # Si 'sí', peso crudo de 5.0
    else: # 'no' o None
        raw["devaluacion"] = 1.0 # Si 'no' o no especificado, peso crudo de 1.0
    print(f"DEBUG (Weights) ► Peso crudo para devaluacion (basado en prioriza_baja_depreciacion='{preferencias.get('prioriza_baja_depreciacion')}'): {raw['devaluacion']}")
   
    # --- NUEVA LÓGICA PARA RATINGS DIRECTOS 0-10 ---
    # 5. Añadir pesos crudos directamente de los ratings del usuario    
    # Añadir pesos crudos directamente de los ratings del usuario
    if preferencias: # Verificar si el diccionario preferencias existe
        raw["rating_fiabilidad_durabilidad"] = float(preferencias.get("rating_fiabilidad_durabilidad") or 0.0)
        raw["rating_seguridad"] = float(preferencias.get("rating_seguridad") or 0.0)
        raw["rating_comodidad"] = float(preferencias.get("rating_comodidad") or 0.0)
        raw["rating_impacto_ambiental"] = float(preferencias.get("rating_impacto_ambiental") or 0.0)
        #raw["rating_costes_uso"] = float(preferencias.get("rating_costes_uso") or 0.0)
        raw["rating_tecnologia_conectividad"] = float(preferencias.get("rating_tecnologia_conectividad") or 0.0)
    else: # Si preferencias es None, poner defaults para los ratings
        raw["rating_fiabilidad_durabilidad"] = 0.0
        raw["rating_seguridad"] = 0.0
        raw["rating_comodidad"] = 0.0
        raw["rating_impacto_ambiental"] = 0.0
        #raw["rating_costes_uso"] = 0.0
        raw["rating_tecnologia_conectividad"] = 0.0
        
  
    print(f"DEBUG (Weights) ► Pesos crudos tras añadir ratings: {raw}")
    raw_float = {k: float(v or 0.0) for k, v in raw.items()}
    
    #print(f"DEBUG (Weights) ► Pesos Crudos FINALES: {raw_float}")
    return raw_float


# normalize_weights se mantiene igual (quizás con el DEBUG print que añadí antes)
def normalize_weights(raw_weights: dict) -> dict:
    """Normaliza los pesos crudos para que sumen 1.0."""
    valid_values = [v for v in raw_weights.values() if isinstance(v, (int, float))]
    total = sum(valid_values) or 1.0 
    normalized = {k: (v / total) if isinstance(v, (int, float)) else 0.0 for k, v in raw_weights.items()}
    print(f"DEBUG (Normalize Weights) ► Pesos Normalizados: {normalized}")
    return normalized
