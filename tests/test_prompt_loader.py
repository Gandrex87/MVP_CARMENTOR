import pytest
from prompts.loader import cargar_prompt

# ---------- TESTS PARA PROMPT DE VALIDACIÓN DINÁMICA ----------

def test_validacion_dinamica_existe_y_no_vacio():
    prompt = cargar_prompt("validacion_dinamica.txt")
    assert isinstance(prompt, str), "El prompt debe ser una cadena de texto"
    assert len(prompt.strip()) > 0, "El contenido del prompt no debe estar vacío"


# ---------- TESTS PARA PROMPT DEL PERFIL ESTRUCTURADO ----------

def test_perfil_structured_prompt_existe_y_no_vacio():
    prompt = cargar_prompt("perfil_structured_prompt.txt")
    assert isinstance(prompt, str), "El prompt debe ser una cadena de texto"
    assert len(prompt.strip()) > 0, "El contenido del prompt no debe estar vacío"


# ---------- TEST PARA ARCHIVO NO ENCONTRADO ----------

def test_prompt_no_encontrado():
    with pytest.raises(FileNotFoundError):
        cargar_prompt("este_prompt_no_existe.txt")
