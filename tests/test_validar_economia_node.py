# tests/test_validar_economia_node.py
## tests/test_validar_economia_node.py
# tests/test_validar_economia_node_simple.py
import pytest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage, HumanMessage
import graph.perfil.nodes as nodes
from graph.perfil.nodes import validar_economia_node
from graph.perfil.nodes import finalizar_y_presentar_node
from graph.perfil.state import EstadoAnalisisPerfil, ResultadoEconomia, EconomiaUsuario, PerfilUsuario, FiltrosInferidos
from utils.enums import Transmision, NivelAventura, TipoMecanica
from graph.perfil.nodes import recopilar_economia_node # <-- Llamar al nodo correcto
# Necesitamos ResultadoEconomia para el mock
 


@pytest.fixture(autouse=True) # Usar autouse=True es potente, pero asegúrate que no interfiera con otros tests
def stub_llm_economia(monkeypatch):
    fake_llm = MagicMock() # Usar MagicMock es más estándar que SimpleNamespace para mocks
    
    # Configurar lo que devuelve invoke
    respuesta_simulada = ResultadoEconomia(
        economia=EconomiaUsuario.model_construct(modo=1), # Puede devolver modo si lo infiere
        mensaje_validacion="¿PREGUNTA ECON simulada?" # Pregunta esperada
    )
    fake_llm.invoke.return_value = respuesta_simulada
    
    # Usar monkeypatch para sustituir la instancia LLM usada en el nodo
    # ¡Asegúrate que 'graph.perfil.nodes.llm_economia' es el path correcto!
    monkeypatch.setattr('graph.perfil.nodes.llm_economia', fake_llm) 
    return fake_llm # Devolver el mock por si quieres hacer asserts sobre él

@pytest.fixture 
def estado_listo_para_economia() -> EstadoAnalisisPerfil:
    """Devuelve estado con perfil y filtros completos, listo para economía."""
    prefs = PerfilUsuario( 
             altura_mayor_190="no", peso_mayor_100="no", uso_profesional="no", 
             valora_estetica="sí", solo_electricos="no", transmision_preferida=Transmision.AUTOMATICO, 
             apasionado_motor="no", aventura=NivelAventura.ninguna 
    )
    filts = FiltrosInferidos( 
             tipo_mecanica=[TipoMecanica.GASOLINA, TipoMecanica.HEVG], 
             estetica_min=5.0, premium_min=1.0, singular_min=1.0,
             tipo_carroceria=None
    )
    return EstadoAnalisisPerfil(
        messages=[AIMessage(content="Confirmación filtros.")],
        preferencias_usuario=prefs, 
        filtros_inferidos=filts,
        economia=None, 
        mensaje_validacion=None,
        pregunta_pendiente=None, # Asegúrate que todos los campos del TypedDict estén
        pesos=None
    )
    
def test_recopilar_economia_pide_pregunta(estado_listo_para_economia, stub_llm_economia): # Renombrado y usa fixture LLM
    """
    Prueba que recopilar_economia_node llama al LLM, actualiza estado parcial 
    y guarda la pregunta pendiente.
    """
    estado_inicial = estado_listo_para_economia # Estado listo sin economía
    # Añadir mensaje humano que dispara la etapa económica
    estado_para_invocar = estado_inicial.copy()
    estado_para_invocar["messages"] = estado_inicial["messages"] + [HumanMessage(content="Sí, quiero ayuda con el presupuesto")]

    # Ejecutar el NODO CORRECTO
    out = recopilar_economia_node(estado_para_invocar)

    # Verificar llamada al LLM mockeado por el fixture
    stub_llm_economia.invoke.assert_called_once()

    # Verificar que el estado económico se actualizó (parcialmente, con modo=1)
    assert out["economia"] is not None
    assert isinstance(out["economia"], EconomiaUsuario)
    assert out["economia"].modo == 1 
    assert out["economia"].ingresos is None # Aún no lo tiene

    # Verificar que la pregunta se guardó en pregunta_pendiente
    assert out["pregunta_pendiente"] == "¿PREGUNTA ECON simulada?"
    
    # Verificar que NO se añadió la pregunta directamente a messages
    assert len(out["messages"]) == len(estado_para_invocar["messages"]) # No debe añadir AIMessage aquí



@pytest.fixture
def estado_todo_completo() -> EstadoAnalisisPerfil:
    # ... (Definición como la teníamos antes, asegurando usar Pydantic objects) ...
    prefs = PerfilUsuario( 
         altura_mayor_190="no", # ¿Está bien escrito?
         peso_mayor_100="no",   # ¿Está bien escrito?
         uso_profesional="no",  # ¿Está bien escrito?
         valora_estetica="sí",  # ¿Está bien escrito?
         solo_electricos="no",  # ¿Está bien escrito?
         transmision_preferida=Transmision.AUTOMATICO, # ¿Está bien escrito?
         apasionado_motor="no", # ¿Está bien escrito?
         aventura=NivelAventura.ninguna # ¿Está bien escrito?
    )
    filts = FiltrosInferidos( 
             tipo_mecanica=[TipoMecanica.GASOLINA, TipoMecanica.HEVG], 
             estetica_min=5.0, premium_min=1.0, singular_min=1.0,
             tipo_carroceria=None
    ) 
    econ = EconomiaUsuario(modo=1, ingresos=50000, ahorro=10000) # Completo
     # --- ¡REVISA ESTA LISTA DETENIDAMENTE! ---
    mensajes_historial = [
        # Asegúrate de que CADA elemento aquí sea HumanMessage(...) o AIMessage(...)
        HumanMessage(content="Mensaje humano 1..."), 
        AIMessage(content="Respuesta AI 1..."),
        HumanMessage(content="Mensaje humano 2..."),
        AIMessage(content="Confirmación economía."), # ¿Es este realmente el último?
        # ¿Hay algún '...' (Ellipsis) suelto por aquí accidentalmente? 
        # Ejemplo de error: HumanMessage(content="Algo"), ... , AIMessage(content="Final") <--- MAL
    ]
    # --- FIN REVISIÓN ---

    return EstadoAnalisisPerfil(
        messages=mensajes_historial, # Usa la lista revisada
        preferencias_usuario=prefs, 
        filtros_inferidos=filts,
        economia=econ, 
        mensaje_validacion=None,
        pregunta_pendiente=None, 
        pesos=None
    )

# Definir los paths a las funciones que usa finalizar_y_presentar_node
PATH_RAG_FINAL = 'graph.perfil.nodes.get_recommended_carrocerias'
PATH_RAW_WEIGHTS_FINAL = 'graph.perfil.nodes.compute_raw_weights'
PATH_NORM_WEIGHTS_FINAL = 'graph.perfil.nodes.normalize_weights'
PATH_FORMATTER_FINAL = 'graph.perfil.nodes.formatear_preferencias_en_tabla'

def test_finalizar_presentar_ok(estado_todo_completo): # Renombrado
    """
    Prueba que finalizar_y_presentar_node llama a RAG, pesos, formato
    y devuelve el estado final correcto.
    """
    estado_inicial = estado_todo_completo

    # Respuestas simuladas
    rag_simulado = ['CARRO_RAG_1', 'CARRO_RAG_2']
    raw_weights_simulado = {'a': 1, 'b': 3} # Ejemplo
    norm_weights_simulado = {'a': 0.25, 'b': 0.75} # Ejemplo
    tabla_simulada = "### TABLA RESUMEN FINAL ###"

    # Mockear todas las dependencias
    with patch(PATH_RAG_FINAL, return_value=rag_simulado) as mock_rag, \
         patch(PATH_RAW_WEIGHTS_FINAL, return_value=raw_weights_simulado) as mock_raw, \
         patch(PATH_NORM_WEIGHTS_FINAL, return_value=norm_weights_simulado) as mock_norm, \
         patch(PATH_FORMATTER_FINAL, return_value=tabla_simulada) as mock_format:

            # Ejecutar el NODO CORRECTO
            estado_salida = finalizar_y_presentar_node(estado_inicial)

    # Verificar llamadas
    mock_rag.assert_called_once()
    mock_raw.assert_called_once()
    mock_norm.assert_called_once_with(raw_weights_simulado)
    mock_format.assert_called_once()
    # Verificar que a format le llegó filtros con carrocería actualizada
    args_format, kwargs_format = mock_format.call_args
    assert kwargs_format.get('filtros').tipo_carroceria == rag_simulado

    # Verificar estado final
    assert estado_salida['filtros_inferidos'].tipo_carroceria == rag_simulado
    assert estado_salida['pesos'] == norm_weights_simulado
    assert len(estado_salida['messages']) == len(estado_inicial['messages']) + 1
    assert isinstance(estado_salida['messages'][-1], AIMessage)
    assert estado_salida['messages'][-1].content == tabla_simulada



