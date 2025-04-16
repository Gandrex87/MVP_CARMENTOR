# tests/test_conversions.py
from utils.conversion import normalize_text_sql

def test_normalize_text_sql():
    texto = "Café con leche y azúcar"
    resultado = normalize_text_sql(texto)
    assert resultado == "cafe con leche y azucar"


def test_normalize_remueve_simbolos():
    texto = "Fiat-500@2023!"
    resultado = normalize_text_sql(texto)
    assert resultado == "fiat 5002023"