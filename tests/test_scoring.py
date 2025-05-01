# tests/test_scoring.py
from utils.conversion import asignar_valores_filtros

def test_valores_filtros_usuario_exigente():
    preferencias = {
        "valora_estetica": "sí",
        "apasionado_motor": "sí"
    }
    valores = asignar_valores_filtros(preferencias)

    assert valores["estetica_min"] == 5.0
    assert valores["premium_min"] == 5.0
    assert valores["singular_min"] == 5.0

def test_valores_filtros_usuario_relajado():
    preferencias = {
        "valora_estetica": "no",
        "apasionado_motor": "no"
    }
    valores = asignar_valores_filtros(preferencias)

    assert valores["estetica_min"] == 1.0
    assert valores["premium_min"] == 1.0
    assert valores["singular_min"] == 1.0

def test_valores_filtros_usuario_incompleto():
    preferencias = {
        "valora_estetica": "sí",
        # No da información sobre apasionado_motor
    }
    valores = asignar_valores_filtros(preferencias)

    assert valores["estetica_min"] == 5.0
    assert valores["premium_min"] == 1.0  # Si falta, lo tratamos como "no"
    assert valores["singular_min"] == 1.0

def test_valores_filtros_tildes_y_mayusculas():
    preferencias = {
        "valora_estetica": "Sí",
        "apasionado_motor": "SI"
    }
    valores = asignar_valores_filtros(preferencias)

    assert valores["estetica_min"] == 5.0
    assert valores["premium_min"] == 5.0
    assert valores["singular_min"] == 5.0

# tests/test_state_scoring.py
from graph.perfil.state import EstadoAnalisisPerfil
from langchain_core.messages import HumanMessage

def test_estado_analisis_perfil_scoring():
    # Simular un estado inicial
    estado = EstadoAnalisisPerfil(
        messages=[HumanMessage(content="Quiero un coche elegante para ciudad.")],
        preferencias_usuario={"valora_estetica": "sí"},
        filtros_inferidos={"estetica_min": 7.0},
        mensaje_validacion="¿Prefieres automático o manual?",
        scoring={
            "valores_objetivo": {"estetica_min": 7.0},
            "pesos": {"estetica_min": 30}
        }
    )

    # Validar que se creó correctamente
    assert estado["scoring"] is not None
    assert "valores_objetivo" in estado["scoring"]
    assert "pesos" in estado["scoring"]
    assert estado["scoring"]["valores_objetivo"]["estetica_min"] == 7.0
    assert estado["scoring"]["pesos"]["estetica_min"] == 30



# tests/test_scoring.py
import pytest
from utils.conversion import calcular_pesos


@pytest.mark.parametrize("preferencias, esperado", [
    # Caso 1: Valora estética
    ( {"valora_estetica": "sí"}, {"estetica_min": 0.30} ),

    # Caso 2: Apasionado del motor
    ( {"apasionado_motor": "sí"}, {"premium_min": 0.25, "singular_min": 0.20} ),

    # Caso 3: Altura mayor a 1.90
    ( {"altura_mayor_190": "sí"}, {"batalla_min": 0.15, "indice_altura_interior_min": 0.10} ),

    # Caso 4: Valora estética + apasionado del motor
    ( {"valora_estetica": "sí", "apasionado_motor": "sí"}, {"estetica_min": 0.30, "premium_min": 0.25, "singular_min": 0.20} ),

    # Caso 5: Todas las preferencias
    ( {"valora_estetica": "sí", "apasionado_motor": "sí", "altura_mayor_190": "sí"}, {
        "estetica_min": 0.30,
        "premium_min": 0.25,
        "singular_min": 0.20,
        "batalla_min": 0.15,
        "indice_altura_interior_min": 0.10
    }),

    # Caso 6: No activa ningún peso
    ( {"uso_profesional": "sí", "peso_mayor_100": "sí"}, {} )
])
def test_calcular_pesos(preferencias, esperado):
    pesos = calcular_pesos(preferencias)
    assert pesos == esperado
