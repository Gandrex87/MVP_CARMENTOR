# tests/test_utils.py

import pytest
# Ajusta rutas de importación según tu estructura
from utils.validation import check_economia_completa
from graph.perfil.state import EconomiaUsuario 

# ---- Pruebas para check_economia_completa ----
def test_check_economia_modo1_incompleto():
    """Prueba False si modo=1 pero faltan ingresos o ahorro."""
    # Usar model_construct para crear el objeto SIN validación inicial
    econ_incompleto_1 = EconomiaUsuario.model_construct(modo=1)
    econ_incompleto_2 = EconomiaUsuario.model_construct(modo=1, ingresos=50000)
    econ_incompleto_3 = EconomiaUsuario.model_construct(modo=1, ahorro=10000)
    
    assert check_economia_completa(econ_incompleto_1) is False
    assert check_economia_completa(econ_incompleto_2) is False
    assert check_economia_completa(econ_incompleto_3) is False

# ... (test_check_economia_modo1_completo pasa como estaba) ...

def test_check_economia_modo2_sin_submodo():
    """Prueba False si modo=2 pero falta submodo."""
    # Usar model_construct
    econ_incompleto_1 = EconomiaUsuario.model_construct(modo=2)
    econ_incompleto_2 = EconomiaUsuario.model_construct(modo=2, pago_contado=20000)

    assert check_economia_completa(econ_incompleto_1) is False
    assert check_economia_completa(econ_incompleto_2) is False # Falta submodo

def test_check_economia_modo2_sub1_incompleto():
    """Prueba False si modo=2, submodo=1 pero falta pago_contado."""
    # Usar model_construct
    econ_incompleto = EconomiaUsuario.model_construct(modo=2, submodo=1)
    assert check_economia_completa(econ_incompleto) is False

# ... (test_check_economia_modo2_sub1_completo pasa como estaba) ...

def test_check_economia_modo2_sub2_incompleto():
    """Prueba False si modo=2, submodo=2 pero falta cuota_max."""
    # Usar model_construct
    econ_incompleto_1 = EconomiaUsuario.model_construct(modo=2, submodo=2)
    econ_incompleto_2 = EconomiaUsuario.model_construct(modo=2, submodo=2, entrada=3000)

    assert check_economia_completa(econ_incompleto_1) is False
    assert check_economia_completa(econ_incompleto_2) is False # Falta cuota_max
