import pytest
from utils.pre import extraer_preferencias_iniciales

def test_extraer_preferencias_iniciales_familia():
    texto = "Necesito un coche para la familia"
    resultado = extraer_preferencias_iniciales(texto)
    assert resultado == {"uso_profesional": "no"}

def test_extraer_preferencias_iniciales_altura_sobre_umbral():
    texto = "Mido 1.93 m"
    resultado = extraer_preferencias_iniciales(texto)
    assert resultado.get("altura_mayor_190") == "sí"

def test_extraer_preferencias_iniciales_altura_bajo_umbral():
    texto = "Mido 1.80m"
    resultado = extraer_preferencias_iniciales(texto)
    assert resultado.get("altura_mayor_190") == "no"

def test_extraer_preferencias_iniciales_peso_sobre_umbral():
    texto = "Peso 120 kg aproximadamente"
    resultado = extraer_preferencias_iniciales(texto)
    assert resultado.get("peso_mayor_100") == "sí"

def test_extraer_preferencias_iniciales_peso_bajo_umbral():
    texto = "Peso 80kg"
    resultado = extraer_preferencias_iniciales(texto)
    assert resultado.get("peso_mayor_100") == "no"

def test_extraer_preferencias_iniciales_completo():
    texto = "Quiero un coche para mi familia, mido 1.93m y peso 80 kg"
    resultado = extraer_preferencias_iniciales(texto)
    assert resultado == {
        "uso_profesional": "no",
        "altura_mayor_190": "sí",
        "peso_mayor_100": "no"
    }
