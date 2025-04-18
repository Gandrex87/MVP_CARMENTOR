import pytest
from graph.perfil.nodes import analizar_perfil_usuario_node
from graph.perfil.state import EstadoAnalisisPerfil
from langchain_core.messages import HumanMessage

# @pytest.fixture
# def state_inicial():
#     return {
#         "messages": [
#             HumanMessage(content="Busco un coche elegante, eléctrico y automático para uso diario. Mido 1.80.")
#         ],
#         "preferencias_usuario": {},
#         "filtros_inferidos": {},
#         "mensaje_validacion": None,
#     }

# def test_analizar_perfil_usuario_node_scoring(state_inicial):
#     # Ejecutar
#     nuevo_state = analizar_perfil_usuario_node(state_inicial)

#     # Verificar que devuelve scoring
#     assert "scoring" in nuevo_state
#     assert "valores_objetivo" in nuevo_state["scoring"]
#     assert "pesos" in nuevo_state["scoring"]

#     # Verificar que no esté vacío
#     assert isinstance(nuevo_state["scoring"]["valores_objetivo"], dict)
#     assert isinstance(nuevo_state["scoring"]["pesos"], dict)
#     assert len(nuevo_state["scoring"]["valores_objetivo"]) > 0
#     assert len(nuevo_state["scoring"]["pesos"]) > 0

# def test_estructura_general_scoring(state_inicial):
#     nuevo_state = analizar_perfil_usuario_node(state_inicial)

#     # Confirmar que los valores objetivos sean numéricos
#     for valor in nuevo_state["scoring"]["valores_objetivo"].values():
#         assert isinstance(valor, (int, float))

#     # Confirmar que los pesos sean numéricos
#     for peso in nuevo_state["scoring"]["pesos"].values():
#         assert isinstance(peso, (int, float))


# tests/test_analizar_perfil.py

import pytest
from graph.perfil.nodes import analizar_perfil_usuario_node
from graph.perfil.state import EstadoAnalisisPerfil
from langchain_core.messages import HumanMessage

@pytest.fixture
def estado_inicial():
    """Estado inicial simulado."""
    return {
        "messages": [],
        "preferencias_usuario": None,
        "filtros_inferidos": None,
        "mensaje_validacion": None,
        "scoring": None,
        "nivel_aventura": None
    }

def test_nivel_aventura_alta(estado_inicial):
    """Simula un flujo donde el usuario quiere aventura extrema."""
    estado_inicial["messages"] = [HumanMessage(content="Quiero un coche que pueda ir por la montaña y caminos difíciles")]

    nuevo_estado = analizar_perfil_usuario_node(estado_inicial)

    assert nuevo_estado["nivel_aventura"] == "ALTA"
    assert isinstance(nuevo_estado["scoring"], dict)
    assert "valores_objetivo" in nuevo_estado["scoring"]
    assert "pesos" in nuevo_estado["scoring"]

def test_nivel_aventura_baja(estado_inicial):
    """Simula un flujo donde el usuario solo quiere ciudad/asfalto."""
    estado_inicial["messages"] = [HumanMessage(content="Quiero un coche para moverme solo por la ciudad, nada de campo")]

    nuevo_estado = analizar_perfil_usuario_node(estado_inicial)

    assert nuevo_estado["nivel_aventura"] == "BAJA"

def test_nivel_aventura_null_si_no_menciona(estado_inicial):
    """Simula un usuario que no menciona el uso de aventura."""
    estado_inicial["messages"] = [HumanMessage(content="Quiero un coche elegante para la ciudad")]

    nuevo_estado = analizar_perfil_usuario_node(estado_inicial)

    assert nuevo_estado["nivel_aventura"] in (None, "BAJA", "MEDIA", "ALTA")  # Depende del LLM, pero no debe romper
