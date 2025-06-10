# test_explicaciones.py

import pytest
from unittest.mock import MagicMock, patch
from utils.explanation_generator import (generar_explicacion_coche_mejorada , _calcular_contribuciones_y_factores_clave_mejorada)

# --- Asumimos que estas son las funciones que hemos creado y queremos probar ---
# Pega aquí las definiciones de las funciones:
# - _get_clave_feature_scaled
# - _es_preferencia_activa
# - _calcular_contribuciones_y_factores_clave_mejorada
# - generar_explicacion_concisa
#
# --- Y las constantes y mapas ---
# - UMBRAL_PESO_MINIMO, UMBRAL_FEATURE_DESTACADA, etc.
# - MAPA_PESOS_A_INFO_EXPLICACION
# - MAPA_AJUSTES_SCORE_A_TEXTO

# --- SIMULACIÓN DE OBJETOS EXTERNOS ---
# Como no tenemos la definición original, la simulamos para los tests.
class PerfilUsuarioMock:
    def __init__(self, **kwargs):
        # Permite crear un perfil con cualquier atributo que necesitemos para la prueba
        self.rating_tecnologia_conectividad = 8
        self.rating_comodidad = 9
        self.valora_estetica = True
        self.estilo_conduccion = "deportivo"
        self.problema_dimension_garage = ['largo']
        self.necesita_sillas_ninos = True
        # Sobrescribimos con los valores pasados
        self.__dict__.update(kwargs)

def is_yes(value):
    """Función de utilidad simulada."""
    return isinstance(value, str) and value.lower() in ['si', 'yes', 'y']

# --- DATOS DE PRUEBA (FIXTURES) ---

@pytest.fixture
def perfil_familia_tecnologica_zbe():
    """Un perfil de usuario que valora la tecnología, el confort, necesita espacio para niños y vive en ZBE."""
    return PerfilUsuarioMock(
        rating_tecnologia_conectividad=9,
        rating_comodidad=8,
        rating_seguridad=10,
        necesita_sillas_ninos=True # Esto activará la penalización de puertas
    )

@pytest.fixture
def pesos_familia_tecnologica():
    """Pesos que reflejan las prioridades del perfil anterior."""
    return {
        "rating_tecnologia_conectividad": 0.25,
        "rating_comodidad": 0.20,
        "rating_seguridad": 0.20,
        "maletero_minimo_score": 0.15,
        "deportividad_style_score": 0.05, # Baja prioridad
        "fav_menor_largo_garage": 0.01 # Peso muy bajo, debería ser ignorado
    }

@pytest.fixture
def coche_suv_moderno_ideal():
    """Un coche que es una excelente recomendación para el perfil anterior."""
    return {
        "nombre": "Hyundai Tucson Híbrido",
        "tecnologia_conectividad_scaled": 0.9, # Muy bueno
        "comodidad_scaled": 0.85,             # Muy bueno
        "seguridad_scaled": 0.95,             # Excelente
        "maletero_minimo_scaled": 0.8,        # Bueno
        "deportividad_style_scaled": 0.5,     # Normalito
        "distintivo_ambiental": "ECO",
        "puertas": 5,
        "anos_vehiculo": 2,
    }

@pytest.fixture
def coche_deportivo_antiguo_inadecuado():
    """Un coche que es una mala recomendación."""
    return {
        "nombre": "Mazda MX-5 (2010)",
        "tecnologia_conectividad_scaled": 0.3, # Malo, por debajo del umbral 0.4
        "comodidad_scaled": 0.5,              # Normal
        "seguridad_scaled": 0.6,              # Aceptable
        "maletero_minimo_scaled": 0.2,        # Muy malo
        "deportividad_style_scaled": 0.9,     # Lo único bueno, pero poco prioritario
        "distintivo_ambiental": "B",
        "puertas": 2, # Malo para familia
        "anos_vehiculo": 15, # Malo para un amante de la tecnología
    }


# --- TESTS PARA _calcular_contribuciones_y_factores_clave_mejorada ---

def test_calcular_contribuciones_coche_ideal(coche_suv_moderno_ideal, pesos_familia_tecnologica, perfil_familia_tecnologica_zbe):
    """
    Prueba que la función identifique correctamente los puntos fuertes de un coche ideal.
    """
    resultado = _calcular_contribuciones_y_factores_clave_mejorada(
        coche_dict=coche_suv_moderno_ideal,
        pesos_normalizados=pesos_familia_tecnologica,
        preferencias_usuario=perfil_familia_tecnologica_zbe,
        n_top_positivos=2
    )
    
    puntos_fuertes = resultado["puntos_fuertes"]
    
    assert len(puntos_fuertes) == 2
    # El primer punto debería ser tecnología, ya que su contribución (0.9 * 0.25 = 0.225) es la más alta
    assert "tecnología y conectividad" in puntos_fuertes[0]["caracteristica_coche"]
    # El segundo debería ser seguridad (0.95 * 0.20 = 0.19)
    assert "seguridad" in puntos_fuertes[1]["caracteristica_coche"]

def test_calcular_contribuciones_ignora_puntos_debiles(coche_deportivo_antiguo_inadecuado, pesos_familia_tecnologica, perfil_familia_tecnologica_zbe):
    """
    Prueba que la función ignore características del coche que no superan el umbral (ej: tecnología).
    """
    resultado = _calcular_contribuciones_y_factores_clave_mejorada(
        coche_dict=coche_deportivo_antiguo_inadecuado,
        pesos_normalizados=pesos_familia_tecnologica,
        preferencias_usuario=perfil_familia_tecnologica_zbe,
        n_top_positivos=2
    )
    
    puntos_fuertes = resultado["puntos_fuertes"]
    nombres_puntos_fuertes = [p["caracteristica_coche"] for p in puntos_fuertes]
    
    # La tecnología del coche (0.3) está por debajo del umbral (0.4), no debería aparecer
    assert "tecnología y conectividad" not in nombres_puntos_fuertes
    # El único punto que podría aparecer es seguridad (0.6 * 0.20 = 0.12)
    assert len(puntos_fuertes) <= 2


# --- TESTS PARA generar_explicacion_concisa (CON MOCK DEL LLM) ---

@patch('utils.explanation_generator.llm_explicacion_coche') # Asume que el LLM está en el script principal
def test_generar_explicacion_coche_ideal_zbe(
    mock_llm, coche_suv_moderno_ideal, pesos_familia_tecnologica, perfil_familia_tecnologica_zbe
):
    """
    Prueba que el contexto generado para el LLM con un coche ideal sea correcto.
    """
    # Configuramos el mock para que no haga nada, solo registre la llamada
    mock_llm.invoke.return_value = MagicMock(content="Explicación generada.")
    
    # Llamamos a la función principal
    generar_explicacion_coche_mejorada(
        coche_dict_completo=coche_suv_moderno_ideal,
        preferencias_usuario=perfil_familia_tecnologica_zbe,
        pesos_normalizados=pesos_familia_tecnologica,
        flag_es_zbe=True, # El usuario está en ZBE
        flag_penalizar_puertas=True, # La lógica de puertas está activa
        flag_penalizar_ant_tec=True,
        flag_penalizar_lc_comod= False,
        flag_penalizar_dep_comod = False,
        flag_aplicar_dist_gen= False,
    )
    
    # Verificamos que se llamó al LLM
    mock_llm.invoke.assert_called_once()
    
    # Extraemos el contexto que se le pasó al LLM
    call_args = mock_llm.invoke.call_args
    messages = call_args[0][0]
    contexto_llm = messages[1].content # El HumanMessage

    # Verificamos el contenido del contexto
    assert "Hyundai Tucson Híbrido" in contexto_llm
    assert "tecnología y conectividad" in contexto_llm
    assert "seguridad" in contexto_llm
    # Verificamos que se añade el bonus de ZBE
    assert "especialmente positivo dado que te encuentras en una Zona de Bajas Emisiones" in contexto_llm
    # Verificamos que NO se penalizan las puertas (tiene 5)
    assert "se ha tenido en cuenta el número de puertas" not in contexto_llm

@patch('utils.explanation_generator.llm_explicacion_coche')
def test_generar_explicacion_coche_inadecuado_zbe(
    mock_llm, coche_deportivo_antiguo_inadecuado, pesos_familia_tecnologica, perfil_familia_tecnologica_zbe
):
    """
    Prueba que el contexto generado para el LLM con un coche inadecuado contenga las penalizaciones correctas.
    """
    mock_llm.invoke.return_value = MagicMock(content="Explicación generada.")
    
    generar_explicacion_coche_mejorada(
        coche_dict_completo=coche_deportivo_antiguo_inadecuado,
        preferencias_usuario=perfil_familia_tecnologica_zbe,
        pesos_normalizados=pesos_familia_tecnologica,
        flag_es_zbe=True, # El usuario está en ZBE
        flag_penalizar_puertas=True, # Lógica de puertas activa
        flag_penalizar_ant_tec=True, # Lógica de antigüedad activa
        flag_penalizar_lc_comod= False,
        flag_penalizar_dep_comod = False,
        flag_aplicar_dist_gen= False,
    )
    
    mock_llm.invoke.assert_called_once()
    contexto_llm = mock_llm.invoke.call_args[0][0][1].content
    
    assert "Mazda MX-5 (2010)" in contexto_llm
    # Verificamos las penalizaciones en la sección "A tener en cuenta"
    # 1. Penalización por distintivo B en ZBE
    assert "su distintivo ambiental (B o NA) es una consideración importante" in contexto_llm
    # 2. Penalización por antigüedad para un usuario tecnológico
    assert "modelo con más de 10 años, lo que se ha considerado por tu interés en la tecnología" in contexto_llm
    # 3. Penalización por puertas para un usuario con necesidades familiares
    assert "se ha tenido en cuenta el número de puertas" in contexto_llm