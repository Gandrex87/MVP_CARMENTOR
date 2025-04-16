# tests/test_enums.py
from utils.enums import TipoCarroceria, TipoMecanica
from utils.conversion import get_enum_names


def test_get_enum_names():
    entrada = [TipoCarroceria.SUV, TipoCarroceria.PICKUP]
    esperado = ["SUV", "PICKUP"]
    assert get_enum_names(entrada) == esperado


def test_enum_values_tipo_carroceria():
    assert "SUV" in [e.value for e in TipoCarroceria]
    assert "MONOVOLUMEN" in [e.value for e in TipoCarroceria]


def test_enum_values_tipo_mecanica():
    assert "BEV" in [e.value for e in TipoMecanica]
    assert "DIESEL" in [e.value for e in TipoMecanica]
