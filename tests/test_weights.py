import pytest
# Ajusta la ruta según tu estructura
from utils.weights import compute_raw_weights, AVENTURA_RAW 
# Nota: No necesitamos importar los modelos Pydantic aquí, trabajamos con dicts

# ---- Pruebas para compute_raw_weights ----

# Escenario 1: Usuario "Base" (No alto, Sin aventura, No apasionado, No estética, No prioriza ancho)
def test_compute_raw_weights_base():
    preferencias_test = {
        "altura_mayor_190": "no",
        "aventura": "ninguna",
        "apasionado_motor": "no",
        "valora_estetica": "no" 
        # otros campos no relevantes para los pesos directos
    }
    # Los filtros mínimos vienen del post-procesamiento para este perfil
    estetica_min = 1.0
    premium_min = 1.0
    singular_min = 1.0
    priorizar_ancho_flag = False

    raw_weights = compute_raw_weights(
        preferencias=preferencias_test,
        estetica=estetica_min,
        premium=premium_min,
        singular=singular_min,
        priorizar_ancho=priorizar_ancho_flag
    )

    # Verificar pesos base y de aventura 'ninguna' (todos 0)
    assert raw_weights.get("estetica") == 1.0
    assert raw_weights.get("premium") == 1.0
    assert raw_weights.get("singular") == 1.0
    assert raw_weights.get("altura_libre_suelo") == 0.0 
    assert raw_weights.get("traccion") == 0.0
    assert raw_weights.get("reductoras") == 0.0
    # Verificar pesos bajos para dimensiones (no alto, no prioriza ancho)
    assert raw_weights.get("batalla") == 0.5 # Valor bajo de ejemplo
    assert raw_weights.get("indice_altura_interior") == 0.5 # Valor bajo de ejemplo
    assert raw_weights.get("ancho") == 0.5 # Valor bajo de ejemplo

# Escenario 2: Usuario Alto
def test_compute_raw_weights_alto():
    preferencias_test = {"altura_mayor_190": "sí", "aventura": "ninguna"}
    # Asumimos filtros y flags base
    estetica_min, premium_min, singular_min = 1.0, 1.0, 1.0
    priorizar_ancho_flag = False 

    raw_weights = compute_raw_weights(preferencias_test, estetica_min, premium_min, singular_min, priorizar_ancho_flag)

    # Verificar pesos ALTOS para batalla e índice, bajos para ancho
    assert raw_weights.get("batalla") == 6.0 # Valor alto de ejemplo
    assert raw_weights.get("indice_altura_interior") == 5.0 # Valor alto de ejemplo
    assert raw_weights.get("ancho") == 0.5 # Valor bajo (no se prioriza)
    # Verificar que aventura siga en 0
    assert raw_weights.get("altura_libre_suelo") == 0.0

# Escenario 3: Aventura Extrema (¡Usando tus valores actualizados!)
def test_compute_raw_weights_aventura_extrema():
    # Usamos los valores que definiste: altura=8, traccion=10, reductoras=8
    pesos_aventura_esperados = AVENTURA_RAW["extrema"] 
    preferencias_test = {"aventura": "extrema", "altura_mayor_190": "no"}
    estetica_min, premium_min, singular_min = 1.0, 1.0, 1.0
    priorizar_ancho_flag = False

    raw_weights = compute_raw_weights(preferencias_test, estetica_min, premium_min, singular_min, priorizar_ancho_flag)

    # Verificar pesos de aventura
    assert raw_weights.get("altura_libre_suelo") == pesos_aventura_esperados["altura_libre_suelo"] # 8.0
    assert raw_weights.get("traccion") == pesos_aventura_esperados["traccion"] # 10.0
    assert raw_weights.get("reductoras") == pesos_aventura_esperados["reductoras"] # 8.0
    # Verificar pesos bajos para dimensiones (no alto)
    assert raw_weights.get("batalla") == 0.5
    assert raw_weights.get("indice_altura_interior") == 0.5

# Escenario 4: Prioriza Ancho
def test_compute_raw_weights_prioriza_ancho():
    preferencias_test = {"altura_mayor_190": "no", "aventura": "ninguna"}
    estetica_min, premium_min, singular_min = 1.0, 1.0, 1.0
    priorizar_ancho_flag = True # <-- Flag activado

    raw_weights = compute_raw_weights(preferencias_test, estetica_min, premium_min, singular_min, priorizar_ancho_flag)

    # Verificar peso ALTO para ancho, bajos para batalla/índice
    assert raw_weights.get("ancho") == 6.0 # Valor alto de ejemplo
    assert raw_weights.get("batalla") == 0.5 
    assert raw_weights.get("indice_altura_interior") == 0.5

# Escenario 5: Combinado (Alto, Extremo, Apasionado/Estético, Prioriza Ancho)
def test_compute_raw_weights_combinado():
    preferencias_test = {
        "altura_mayor_190": "sí",
        "aventura": "extrema",
        "apasionado_motor": "sí", # Influye en premium/singular pasados como arg
        "valora_estetica": "sí"   # Influye en estetica pasado como arg
    }
    # Filtros/Pesos base altos por ser apasionado/estético
    estetica_min = 5.0 
    premium_min = 5.0
    singular_min = 5.0
    priorizar_ancho_flag = True # Asumimos que se activó

    raw_weights = compute_raw_weights(preferencias_test, estetica_min, premium_min, singular_min, priorizar_ancho_flag)
    
    pesos_aventura_esperados = AVENTURA_RAW["extrema"]

    # Verificar pesos altos en casi todo
    assert raw_weights.get("estetica") == 5.0
    assert raw_weights.get("premium") == 5.0
    assert raw_weights.get("singular") == 5.0
    assert raw_weights.get("altura_libre_suelo") == pesos_aventura_esperados["altura_libre_suelo"] # 8.0
    assert raw_weights.get("traccion") == pesos_aventura_esperados["traccion"] # 10.0
    assert raw_weights.get("reductoras") == pesos_aventura_esperados["reductoras"] # 8.0
    assert raw_weights.get("batalla") == 6.0 # Alto por ser alto
    assert raw_weights.get("indice_altura_interior") == 5.0 # Alto por ser alto
    assert raw_weights.get("ancho") == 6.0 # Alto por priorizar ancho
