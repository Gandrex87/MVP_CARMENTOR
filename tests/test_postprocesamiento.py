# tests/test_postprocesamiento.py
import pytest
from utils.postprocessing import aplicar_postprocesamiento

@pytest.mark.parametrize("preferencias, filtros, tipo_mecanica_esperada", [
    ({"solo_electricos": "no"}, {"tipo_mecanica": None}, True),
    ({"solo_electricos": "si"}, {"tipo_mecanica": None}, False),
])
def test_tipo_mecanica(preferencias, filtros, tipo_mecanica_esperada):
    _, filtros_result = aplicar_postprocesamiento(preferencias, filtros)
    tiene_tipo_mecanica = filtros_result.get("tipo_mecanica") is not None
    assert tiene_tipo_mecanica == tipo_mecanica_esperada

@pytest.mark.parametrize("preferencias, expected", [
    ({"valora_estetica": "sí"}, 7.0),
    ({"valora_estetica": "no"}, 1.0),
])
def test_estetica_min(preferencias, expected):
    _, filtros = aplicar_postprocesamiento(preferencias, {"estetica_min": None})
    assert filtros["estetica_min"] == expected

@pytest.mark.parametrize("apasionado, premium, singular", [
    ("sí", 7.0, 7.0),
    ("no", 1.0, 1.0),
])
def test_premium_y_singular(apasionado, premium, singular):
    preferencias = {"apasionado_motor": apasionado}
    filtros = {"premium_min": None, "singular_min": None}
    _, filtros = aplicar_postprocesamiento(preferencias, filtros)
    assert filtros["premium_min"] == premium
    assert filtros["singular_min"] == singular
