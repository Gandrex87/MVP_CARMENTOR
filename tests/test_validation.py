# En tests/test_utils.py (o test_validation.py)

import pytest 
# Ajusta la ruta de importación según tu estructura
from utils.validation import check_pasajeros_completo 
from graph.perfil.state import InfoPasajeros # Necesitamos importar el modelo

# --- Pruebas para check_pasajeros_completo ---

def test_check_pasajeros_none_input():
    """Prueba que devuelve False si la entrada es None."""
    assert check_pasajeros_completo(None) is False

def test_check_pasajeros_objeto_vacio():
    """Prueba que devuelve False si el objeto está vacío (frecuencia es None)."""
    info = InfoPasajeros() # frecuencia, X, Z serán None por defecto
    assert check_pasajeros_completo(info) is False

def test_check_pasajeros_frecuencia_nunca():
    """Prueba que devuelve True si frecuencia es 'nunca', sin importar X o Z."""
    info_1 = InfoPasajeros(frecuencia="nunca")
    info_2 = InfoPasajeros(frecuencia="nunca", num_ninos_silla=1, num_otros_pasajeros=2) # Aunque tenga X/Z
    assert check_pasajeros_completo(info_1) is True
    assert check_pasajeros_completo(info_2) is True

def test_check_pasajeros_frecuencia_ocasional_incompleto():
    """Prueba False para 'ocasional' si falta X o Z."""
    info_sin_xz = InfoPasajeros(frecuencia="ocasional")
    info_falta_z = InfoPasajeros(frecuencia="ocasional", num_ninos_silla=1)
    info_falta_x = InfoPasajeros(frecuencia="ocasional", num_otros_pasajeros=2)
    
    assert check_pasajeros_completo(info_sin_xz) is False
    assert check_pasajeros_completo(info_falta_z) is False
    assert check_pasajeros_completo(info_falta_x) is False

def test_check_pasajeros_frecuencia_ocasional_completo():
    """Prueba True para 'ocasional' si X y Z tienen valor (incluso 0)."""
    info_completo_1 = InfoPasajeros(frecuencia="ocasional", num_ninos_silla=1, num_otros_pasajeros=2)
    info_completo_2 = InfoPasajeros(frecuencia="ocasional", num_ninos_silla=0, num_otros_pasajeros=1)
    info_completo_3 = InfoPasajeros(frecuencia="ocasional", num_ninos_silla=2, num_otros_pasajeros=0)
    info_completo_4 = InfoPasajeros(frecuencia="ocasional", num_ninos_silla=0, num_otros_pasajeros=0) # Caso de 0 niños y 0 otros
    
    assert check_pasajeros_completo(info_completo_1) is True
    assert check_pasajeros_completo(info_completo_2) is True
    assert check_pasajeros_completo(info_completo_3) is True
    assert check_pasajeros_completo(info_completo_4) is True

def test_check_pasajeros_frecuencia_frecuente_incompleto():
    """Prueba False para 'frecuente' si falta X o Z."""
    info_sin_xz = InfoPasajeros(frecuencia="frecuente")
    info_falta_z = InfoPasajeros(frecuencia="frecuente", num_ninos_silla=0)
    info_falta_x = InfoPasajeros(frecuencia="frecuente", num_otros_pasajeros=1)
    
    assert check_pasajeros_completo(info_sin_xz) is False
    assert check_pasajeros_completo(info_falta_z) is False
    assert check_pasajeros_completo(info_falta_x) is False

def test_check_pasajeros_frecuencia_frecuente_completo():
    """Prueba True para 'frecuente' si X y Z tienen valor (incluso 0)."""
    info_completo_1 = InfoPasajeros(frecuencia="frecuente", num_ninos_silla=2, num_otros_pasajeros=1)
    info_completo_2 = InfoPasajeros(frecuencia="frecuente", num_ninos_silla=0, num_otros_pasajeros=2)
    info_completo_3 = InfoPasajeros(frecuencia="frecuente", num_ninos_silla=1, num_otros_pasajeros=0)
    info_completo_4 = InfoPasajeros(frecuencia="frecuente", num_ninos_silla=0, num_otros_pasajeros=0) 
    
    assert check_pasajeros_completo(info_completo_1) is True
    assert check_pasajeros_completo(info_completo_2) is True
    assert check_pasajeros_completo(info_completo_3) is True
    assert check_pasajeros_completo(info_completo_4) is True