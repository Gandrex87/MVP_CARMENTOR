# tests/test_postprocessing.py (o tests/test_utils.py)

import pytest
from typing import List, Optional
from utils.postprocessing import aplicar_postprocesamiento_perfil
from utils.conversion import is_yes
from graph.perfil.state import PerfilUsuario, FiltrosInferidos 
from utils.enums import TipoMecanica, NivelAventura, Transmision # Para crear objetos PerfilUsuario

# --- Pruebas para aplicar_postprocesamiento_filtros ---

def test_postproc_filtros_inputs_none():
    """Prueba que devuelve el filtro original si preferencias o filtros son None."""
    prefs_none = aplicar_postprocesamiento_perfil(FiltrosInferidos(), None)
    assert prefs_none is not None # Devuelve el objeto FiltrosInferidos original
    
    filtros_none = aplicar_postprocesamiento_perfil(None, PerfilUsuario())
    assert filtros_none is None

def test_postproc_filtros_estetica():
    """Prueba la lógica de estetica_min."""
    prefs_si_estetica = PerfilUsuario(valora_estetica="sí")
    prefs_no_estetica = PerfilUsuario(valora_estetica="no")
    prefs_none_estetica = PerfilUsuario(valora_estetica=None)

    filtros_base = FiltrosInferidos() # estetica_min es None por defecto
    
    res_si = aplicar_postprocesamiento_perfil(filtros_base, prefs_si_estetica)
    assert res_si.estetica_min == 5.0

    # Probar que no cambia si ya es 5.0 (basado en la lógica if !=)
    filtros_ya_5 = FiltrosInferidos(estetica_min=5.0)
    res_si_ya_5 = aplicar_postprocesamiento_perfil(filtros_ya_5, prefs_si_estetica)
    assert res_si_ya_5.estetica_min == 5.0

    res_no = aplicar_postprocesamiento_perfil(filtros_base, prefs_no_estetica)
    assert res_no.estetica_min == 1.0
    
    res_none = aplicar_postprocesamiento_perfil(filtros_base, prefs_none_estetica)
    assert res_none.estetica_min == 1.0

def test_postproc_filtros_premium():
    """Prueba la lógica de premium_min basada en apasionado_motor."""
    prefs_si_apasionado = PerfilUsuario(apasionado_motor="sí")
    prefs_no_apasionado = PerfilUsuario(apasionado_motor="no")

    filtros_base = FiltrosInferidos() # premium_min es None

    res_si = aplicar_postprocesamiento_perfil(filtros_base, prefs_si_apasionado)
    assert res_si.premium_min == 3.0

    res_no = aplicar_postprocesamiento_perfil(filtros_base, prefs_no_apasionado)
    assert res_no.premium_min == 1.0

# Pruebas para la lógica aditiva de singular_min
@pytest.mark.parametrize("apasionado, exclusivo, esperado_singular", [
    ("sí", "sí", 6.0), # 3.0 (apasionado) + 3.0 (exclusivo)
    ("sí", "no", 4.0), # 3.0 (apasionado) + 0.5 (no exclusivo)
    ("sí", None, 4.0), # 3.0 (apasionado) + 0.5 (exclusivo None)
    ("no", "sí", 4.0), # 0.5 (no apasionado) + 3.0 (exclusivo)
    ("no", "no", 1.0), # 0.5 (no apasionado) + 0.5 (no exclusivo)
    ("no", None, 1.0), # 0.5 (no apasionado) + 0.5 (exclusivo None)
    (None, "sí", 4.0), # 0.5 (apasionado None) + 3.0 (exclusivo)
    (None, "no", 2.0), # 0.5 (apasionado None) + 0.5 (no exclusivo)
    (None, None, 2.0), # 0.5 (apasionado None) + 0.5 (exclusivo None)
])
def test_postproc_filtros_singular_aditivo(apasionado, exclusivo, esperado_singular):
    prefs = PerfilUsuario(apasionado_motor=apasionado, prefiere_diseno_exclusivo=exclusivo)
    filtros_base = FiltrosInferidos() # singular_min es None

    res = aplicar_postprocesamiento_perfil(filtros_base, prefs)
    assert res.singular_min == esperado_singular

def test_postproc_filtros_tipo_mecanica_default():
    """Prueba que asigna mecánicas default si solo_electricos='no' y tipo_mecanica falta."""
    prefs = PerfilUsuario(solo_electricos="no")
    # Caso 1: tipo_mecanica es None
    filtros_sin_mecanica = FiltrosInferidos(tipo_mecanica=None)
    res1 = aplicar_postprocesamiento_perfil(filtros_sin_mecanica, prefs)
    assert isinstance(res1.tipo_mecanica, list)
    assert TipoMecanica.GASOLINA in res1.tipo_mecanica
    assert TipoMecanica.DIESEL in res1.tipo_mecanica

    # Caso 2: tipo_mecanica es lista vacía
    filtros_mecanica_vacia = FiltrosInferidos(tipo_mecanica=[])
    res2 = aplicar_postprocesamiento_perfil(filtros_mecanica_vacia, prefs)
    assert isinstance(res2.tipo_mecanica, list)
    assert TipoMecanica.GASOLINA in res2.tipo_mecanica

def test_postproc_filtros_tipo_mecanica_no_cambia_si_electricos_si():
    """Prueba que NO cambia tipo_mecanica si solo_electricos='sí'."""
    prefs = PerfilUsuario(solo_electricos="sí")
    # LLM podría haber inferido BEV y REEV como en tu regla de post-proc
    filtros_con_bev_reev = FiltrosInferidos(tipo_mecanica=[TipoMecanica.BEV, TipoMecanica.REEV])
    res = aplicar_postprocesamiento_perfil(filtros_con_bev_reev, prefs)
    # La regla de mecánicas default no debe activarse
    assert res.tipo_mecanica == [TipoMecanica.BEV, TipoMecanica.REEV] 

    # Probar regla de solo_electricos='si' -> BEV, REEV
    # (Asegúrate que esta regla esté activa y sea la que quieres)
    filtros_sin_mecanica = FiltrosInferidos(tipo_mecanica=None)
    res_forzado_electricos = aplicar_postprocesamiento_perfil(filtros_sin_mecanica, prefs)
    if hasattr(filtros_sin_mecanica, 'tipo_mecanica'): # Si tu función realmente la modifica
        assert TipoMecanica.BEV in res_forzado_electricos.tipo_mecanica
        assert TipoMecanica.REEV in res_forzado_electricos.tipo_mecanica


def test_postproc_filtros_tipo_mecanica_no_cambia_si_ya_existe():
    """Prueba que NO cambia tipo_mecanica si solo_electricos='no' PERO ya tiene valor."""
    prefs = PerfilUsuario(solo_electricos="no")
    filtros_con_mecanica_existente = FiltrosInferidos(tipo_mecanica=[TipoMecanica.GASOLINA])
    res = aplicar_postprocesamiento_perfil(filtros_con_mecanica_existente, prefs)
    # La regla de mecánicas default no debe activarse
    assert res.tipo_mecanica == [TipoMecanica.GASOLINA]

def test_postproc_filtros_sin_cambios_relevantes():
    """Prueba que si los valores ya son los correctos, no se marcan cambios (si usaras el flag)."""
    prefs = PerfilUsuario(valora_estetica="sí", apasionado_motor="no", prefiere_diseno_exclusivo="no")
    filtros_iniciales = FiltrosInferidos(estetica_min=5.0, premium_min=1.0, singular_min=1.0)
    
    # La función ahora siempre devuelve el objeto actualizado, así que comparamos valores
    res = aplicar_postprocesamiento_perfil(filtros_iniciales, prefs)
    assert res.estetica_min == 5.0
    assert res.premium_min == 1.0
    assert res.singular_min == 1.0
    # Y si pasamos el mismo objeto, debería ser el mismo si cambios_realizados fuera False,
    # pero como siempre devuelve la copia, esta aserción no aplica:
    # assert res is filtros_iniciales # Ya no es válido porque siempre devuelve copia