import pytest
from utils.formatters import get_enum_names
from utils.enums import TipoMecanica

def test_get_enum_names_formatters():
    lista = [TipoMecanica.GASOLINA, TipoMecanica.DIESEL]
    assert get_enum_names(lista) == ["GASOLINA", "DIESEL"]
