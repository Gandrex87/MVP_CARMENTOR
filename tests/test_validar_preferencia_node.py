import pytest
from types import SimpleNamespace
from langchain_core.messages import AIMessage
from graph.perfil.nodes import validar_economia_node

@pytest.fixture(autouse=True)
def stub_llm(monkeypatch):
    # Simula llm_economia.invoke
    def fake_invoke(prompts, **kwargs):
        # devuelve SimpleNamespace para economia + mensaje
        econ = SimpleNamespace(modo=1, submodo=None, ingresos=None, ahorro=None,
                               pago_contado=None, cuota_max=None, entrada=None)
        return SimpleNamespace(economia=econ, mensaje_validacion="PREGUNTA_ECONOMIA")
    monkeypatch.setattr("graph.perfil.nodes.llm_economia.invoke", fake_invoke)

def base_state(econ=None, prefs=None, filtros=None, messages=None):
    return {
        "economia": econ or {},
        "preferencias_usuario": prefs or {},
        "filtros_inferidos": filtros or {},
        "messages": messages or []
    }

def test_incomplete_asks_llm_and_updates_state():
    state = base_state(econ={})
    out = validar_economia_node(state)

    # 1 pregunta LLM añadida
    assert len(out["messages"]) == 1
    assert isinstance(out["messages"][-1], AIMessage)
    assert out["messages"][-1].content == "PREGUNTA_ECONOMIA"

    # economía actualizada a dict
    assert isinstance(out["economia"], dict)
    assert out["economia"]["modo"] == 1

def test_complete_generates_table_and_pesos(monkeypatch):
    # Stubeo formateo y pesos
    monkeypatch.setattr("graph.perfil.nodes.get_recommended_carrocerias", lambda p,f,k: ["MOCK"])
    monkeypatch.setattr("graph.perfil.nodes.formatear_preferencias_en_tabla", lambda p,f,e: "TABLA_FINAL")
    monkeypatch.setattr("graph.perfil.nodes.compute_raw_weights", lambda **kw: {"a":1,"b":3})
    monkeypatch.setattr("graph.perfil.nodes.normalize_weights", lambda raw: {"a":0.25,"b":0.75})

    econ = {"modo":1, "submodo":None, "ingresos":50000, "ahorro":15000,
            "pago_contado":None, "cuota_max":None, "entrada":None}
    prefs = {"altura_mayor_190":"sí","peso_mayor_100":"no","uso_profesional":"no",
             "valora_estetica":"sí","solo_electricos":"no","transmision_preferida":None,
             "apasionado_motor":"no","aventura":"ninguna"}
    filtros = {"tipo_mecanica":["GASOLINA"], "estetica_min":5.0,
               "premium_min":1.0, "singular_min":1.0}

    state = base_state(econ=econ, prefs=prefs, filtros=filtros, messages=[])
    out = validar_economia_node(state)

    # la última es nuestra tabla mock
    assert out["messages"][-1].content == "TABLA_FINAL"
    # se añaden pesos
    assert out["pesos"] == {"a":0.25,"b":0.75}
    # no repite tabla si se llama dos veces
    second = validar_economia_node(out)
    assert len(second["messages"]) == len(out["messages"])
