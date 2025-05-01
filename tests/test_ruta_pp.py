import pytest
from graph.perfil.condition import ruta_post_preferencias
from graph.perfil.state import EstadoAnalisisPerfil

# Campos de ejemplo:
campos_pref = [
    "solo_electricos","uso_profesional","aventura",
    "transmision_preferida","valora_estetica",
    "altura_mayor_190","peso_mayor_100","apasionado_motor"
]
campos_filt = ["tipo_mecanica"]

def make_state(prefs, filts):
    return {
        "preferencias_usuario": prefs,
        "filtros_inferidos": filts
    }

def test_ruta_incompleta_vuelve_a_perfil():
    prefs = {c: None for c in campos_pref}
    filts = {c: None for c in campos_filt}
    state = make_state(prefs, filts)
    assert ruta_post_preferencias(state) == "validar_preferencias"

def test_ruta_pref_completa_filts_incompleto():
    prefs = {c: "sí" for c in campos_pref}
    filts = {"tipo_mecanica": None}
    state = make_state(prefs, filts)
    assert ruta_post_preferencias(state) == "validar_preferencias"

def test_ruta_completa_avanza_a_economia():
    prefs = {c: "sí" for c in campos_pref}
    filts = {"tipo_mecanica": ["GASOLINA"]}
    state = make_state(prefs, filts)
    assert ruta_post_preferencias(state) == "validar_economia"
