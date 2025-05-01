# tests/test_nodes.py
import pytest 
from unittest.mock import patch, MagicMock # Necesitamos patch para mockear
from graph.perfil.nodes import recopilar_preferencias_node ,inferir_filtros_node
from graph.perfil.state import EstadoAnalisisPerfil, PerfilUsuario, ResultadoSoloPerfil, FiltrosInferidos, ResultadoSoloFiltros, EconomiaUsuario, ResultadoEconomia
from utils.enums import Transmision, NivelAventura ,TipoMecanica
from langchain_core.messages import HumanMessage, AIMessage
from graph.perfil.nodes import recopilar_economia_node # Ajusta ruta si cambió


def test_recopilar_preferencias_primer_mensaje_pide_info():
    """
    Prueba que al recibir el primer HumanMessage, el nodo llama al LLM 
    y añade la pregunta de validación del LLM al historial.
    (Usando patch sobre el objeto completo)
    """
    # 1. Estado de ENTRADA (igual que antes)
    estado_inicial = EstadoAnalisisPerfil(
        messages=[HumanMessage(content="Hola")],
        preferencias_usuario=None,
        filtros_inferidos=None,
        economia=None,
        mensaje_validacion=None,
        pesos=None
    )

    # 2. RESPUESTA SIMULADA del LLM (igual que antes)
    respuesta_llm_simulada = ResultadoSoloPerfil(
        preferencias_usuario=PerfilUsuario(), 
        mensaje_validacion="¡Hola! Para empezar, ¿qué tipo de coche buscas y para qué lo usarás?"
    )

    # 3. Mockear TODO el objeto llm_solo_perfil
    #    NOTA: El path ahora es solo hasta el objeto, SIN el '.invoke'
    with patch('graph.perfil.nodes.llm_solo_perfil') as mock_llm_objeto_completo:
        
        # 3a. Ahora, configuramos el método 'invoke' DENTRO de nuestro objeto mockeado
        #     unittest.mock crea automáticamente métodos simulados cuando accedes a ellos.
        mock_llm_objeto_completo.invoke.return_value = respuesta_llm_simulada
        
        # --- Opcional: Mockear post-procesamiento si es necesario ---
        # with patch('graph.perfil.nodes.aplicar_postprocesamiento_perfil', side_effect=lambda x: x) as mock_postproc:

        # 4. Ejecutar la función del nodo (igual que antes)
        estado_salida = recopilar_preferencias_node(estado_inicial)

    # 5. Verificar (Asserts)
    
    # 5.1. ¿Se llamó al método 'invoke' del OBJETO MOCKEADO una vez?
    mock_llm_objeto_completo.invoke.assert_called_once() 
    
    # (Opcional) Verificar los argumentos pasados a invoke
    # print(mock_llm_objeto_completo.invoke.call_args)

    # 5.2 - 5.5: El resto de los asserts deberían seguir funcionando igual
    assert isinstance(estado_salida, dict)
    assert "messages" in estado_salida
    assert "preferencias_usuario" in estado_salida
    assert isinstance(estado_salida["preferencias_usuario"], PerfilUsuario) 
    assert len(estado_salida["messages"]) == 2 
    assert isinstance(estado_salida["messages"][1], AIMessage)
    assert estado_salida["messages"][1].content == respuesta_llm_simulada.mensaje_validacion

# tests/test_nodes.py (continuación)

# ... (imports y la primera prueba 'test_recopilar_preferencias_primer_mensaje_pide_info' ya definida) ...

def test_recopilar_preferencias_llm_extrae_parcial():
    """
    Prueba que si el LLM devuelve algunas preferencias y un mensaje de validación,
    el estado se actualiza correctamente.
    """
    # 1. Estado de ENTRADA: Usuario ya dio alguna info (implícita en la respuesta simulada del LLM)
    #    Para este nodo, usualmente empezamos con el mensaje humano que dispara la lógica.
    #    El historial completo lo maneja LangGraph, pero el nodo recibe el estado actual.
    #    Vamos a simular un estado donde ya hubo una interacción anterior.
    estado_inicial = EstadoAnalisisPerfil(
        messages=[
            HumanMessage(content="Busco coche automático no eléctrico"), 
            AIMessage(content="Ok, ¿y para qué lo usarás principalmente?") # Pregunta previa de la IA
        ],
        preferencias_usuario=PerfilUsuario(solo_electricos="no", transmision_preferida=Transmision.AUTOMATICO), # Estado parcial previo
        filtros_inferidos=None,
        economia=None,
        mensaje_validacion="Ok, ¿y para qué lo usarás principalmente?", # Mensaje anterior
        pesos=None
    )
    # Añadimos la nueva respuesta humana que queremos procesar
    nuevo_mensaje_humano = HumanMessage(content="Solo para uso personal")
    estado_para_invocar = estado_inicial.copy() # Copiar para no modificar el original aquí
    estado_para_invocar["messages"] = estado_inicial["messages"] + [nuevo_mensaje_humano]


    # 2. Definir la RESPUESTA SIMULADA del LLM para esta nueva entrada
    #    Asumimos que el LLM ahora extrae 'uso_profesional' y pregunta por 'estetica'.
    respuesta_llm_simulada = ResultadoSoloPerfil(
        preferencias_usuario=PerfilUsuario(
            solo_electricos="no", # Mantiene lo anterior (o lo re-extrae)
            transmision_preferida=Transmision.AUTOMATICO, # Mantiene lo anterior
            uso_profesional="no", # Extrae lo nuevo
            aventura=NivelAventura.ninguna # Infiere por defecto quizás
            # Los demás campos siguen None por defecto
        ), 
        mensaje_validacion="Entendido, uso personal. ¿Le das importancia a la estética del coche?" # Nueva pregunta
    )

    # 3. Mockear la llamada a invoke (usando la estrategia que funcionó)
    with patch('graph.perfil.nodes.llm_solo_perfil') as mock_llm_objeto_completo:
        mock_llm_objeto_completo.invoke.return_value = respuesta_llm_simulada
        
        # --- Opcional: Mockear post-procesamiento ---
        # with patch('graph.perfil.nodes.aplicar_postprocesamiento_perfil', side_effect=lambda p: p) as mock_postproc:

        # 4. Ejecutar el nodo con el estado que incluye la nueva respuesta humana
        #    NOTA: Pasamos el estado que contiene el historial COMPLETO hasta el nuevo mensaje humano
        estado_salida = recopilar_preferencias_node(estado_para_invocar) 

    # 5. Verificar (Asserts)
    
    # 5.1. ¿Se llamó al método 'invoke' del mock una vez?
    mock_llm_objeto_completo.invoke.assert_called_once() 
    
    # 5.2. Verificar el estado 'preferencias_usuario' actualizado
    prefs_salida = estado_salida.get("preferencias_usuario")
    assert isinstance(prefs_salida, PerfilUsuario)
    # Verificar campos específicos actualizados/mantenidos
    assert prefs_salida.solo_electricos == "no"
    assert prefs_salida.transmision_preferida == Transmision.AUTOMATICO
    assert prefs_salida.uso_profesional == "no" # Se actualizó
    assert prefs_salida.aventura == NivelAventura.ninguna # Se infirió/mantuvo
    assert prefs_salida.valora_estetica is None # Aún no se sabe

    # 5.3. Verificar historial de mensajes
    mensajes_salida = estado_salida.get("messages", [])
    # Esperamos historial inicial + nuevo humano + nuevo AI
    assert len(mensajes_salida) == len(estado_para_invocar["messages"]) + 1 
    assert isinstance(mensajes_salida[-1], AIMessage)
    assert mensajes_salida[-1].content == respuesta_llm_simulada.mensaje_validacion # Es la nueva pregunta


# tests/test_nodes.py (continuación)
from graph.perfil.nodes import validar_preferencias_node 
PATH_CHECK_PERFIL = 'graph.perfil.nodes.check_perfil_usuario_completeness' 

# ---- Pruebas para validar_preferencias_node ----

def test_validar_preferencias_incompleto():
    """
    Prueba que si el perfil está incompleto, el nodo no cambia el estado.
    """
    # Estado con perfil incompleto (algunos None)
    estado_inicial = EstadoAnalisisPerfil(
        messages=[HumanMessage(content="..."), AIMessage(content="Pregunta previa?")],
        preferencias_usuario=PerfilUsuario(solo_electricos="no", aventura=None), # Falta aventura, etc.
        # ... otros campos None ...
    )
    
    # Mockear check_perfil_usuario_completeness para que devuelva False
    with patch(PATH_CHECK_PERFIL, return_value=False) as mock_check:
        estado_salida = validar_preferencias_node(estado_inicial)
        
    mock_check.assert_called_once_with(estado_inicial["preferencias_usuario"]) # Verificar llamada al checker
    # El estado no debe cambiar porque este nodo solo valida
    assert estado_salida == estado_inicial 

def test_validar_preferencias_completo():
    """
    Prueba que si el perfil está completo, el nodo no cambia el estado.
    """
    # Estado con perfil supuestamente completo
    estado_inicial = EstadoAnalisisPerfil(
        messages=[HumanMessage(content="..."), AIMessage(content="...")],
        preferencias_usuario=PerfilUsuario( # Rellenar todos los campos necesarios
             altura_mayor_190="no", peso_mayor_100="no", uso_profesional="no", 
             valora_estetica="sí", solo_electricos="no", transmision_preferida=Transmision.AUTOMATICO, 
             apasionado_motor="no", aventura=NivelAventura.ninguna 
        ), 
        # ... otros campos ...
    )
    
    # Mockear check_perfil_usuario_completeness para que devuelva True
    with patch(PATH_CHECK_PERFIL, return_value=True) as mock_check:
        estado_salida = validar_preferencias_node(estado_inicial)
        
    mock_check.assert_called_once_with(estado_inicial["preferencias_usuario"])
    # El estado tampoco debe cambiar
    assert estado_salida == estado_inicial
    
    
# tests/test_nodes.py (Corrección para la última prueba)

# ... (imports y las otras pruebas que SÍ PASARON) ...

def test_recopilar_preferencias_ignora_ai_message():
    """
    Prueba que si el último mensaje es de la IA, el nodo no llama al LLM.
    (Usando patch sobre el objeto completo) # <-- Estrategia correcta
    """
    # 1. Estado de ENTRADA donde el último mensaje es de la IA
    estado_inicial = EstadoAnalisisPerfil(
        messages=[
            HumanMessage(content="Hola"), 
            AIMessage(content="¿Para qué usarás el coche?") # <-- Último mensaje
            ], 
        preferencias_usuario=PerfilUsuario(), 
        filtros_inferidos=None,
        economia=None,
        mensaje_validacion="¿Para qué usarás el coche?",
        pesos=None
    )
    
    # 2. Mockear TODO el objeto llm_solo_perfil (¡La estrategia que funcionó!)
    #    Path SIN el '.invoke'
    with patch('graph.perfil.nodes.llm_solo_perfil') as mock_llm_objeto_completo:
         
         # No necesitamos configurar un return_value para invoke, 
         # porque la prueba espera que NO se llame.

         # 4. Ejecutar la función del nodo
         estado_salida = recopilar_preferencias_node(estado_inicial)

    # 5. Verificar (Asserts)
    
    # 5.1. ¡Verificar que el método invoke DEL MOCK NO fue llamado!
    # unittest.mock crea el atributo .invoke en el mock automáticamente, 
    # y podemos verificar si se usó.
    mock_llm_objeto_completo.invoke.assert_not_called() 
    
    # 5.2. Verificar que el estado de salida es IDÉNTICO al de entrada
    #    (El nodo no debería haber hecho nada porque el último mensaje era AIMessage)
    assert estado_salida == estado_inicial
    
    
    # tests/test_nodes.py (continuación)
#============================NUEVAS PRUEBAS inferir_filtros_node=========================== 
# Importar nodos y tipos necesarios para Etapa 2
# ¡Ajusta rutas si es necesario!



# ---- Pruebas para inferir_filtros_node ----

@pytest.fixture # Usaremos un fixture para el perfil completo para no repetirlo
def estado_con_perfil_completo() -> EstadoAnalisisPerfil:
    """Devuelve un estado de ejemplo con preferencias_usuario completo."""
    return EstadoAnalisisPerfil(
        messages=[
            HumanMessage(content="..."), 
            AIMessage(content="Pregunta previa..."),
            HumanMessage(content="Última respuesta perfil...") ,
            AIMessage(content="¡Perfecto! Ya tenemos tus preferencias principales...") # Mensaje de confirmación de perfil
        ],
        preferencias_usuario=PerfilUsuario( # Perfil completo
             altura_mayor_190="no", peso_mayor_100="no", uso_profesional="no", 
             valora_estetica="sí", solo_electricos="no", transmision_preferida=Transmision.AUTOMATICO, 
             apasionado_motor="no", aventura=NivelAventura.ninguna 
        ), 
        filtros_inferidos=None, # Aún no hay filtros
        economia=None,
        mensaje_validacion="...", # Último mensaje de la etapa anterior
        pesos=None
    )


def test_inferir_filtros_ok_con_perfil_completo(estado_con_perfil_completo):
    """
    Prueba el caso feliz de inferir_filtros_node: perfil completo, 
    LLM devuelve filtros válidos y mensaje de confirmación.
    """
    # 1. Estado de ENTRADA (usamos el fixture)
    estado_inicial = estado_con_perfil_completo

    # 2. Definir la RESPUESTA SIMULADA de llm_solo_filtros
    respuesta_llm_simulada = ResultadoSoloFiltros(
        filtros_inferidos=FiltrosInferidos(
            # Valores plausibles basados en el perfil del fixture
            batalla_min=None, 
            indice_altura_interior_min=None,
            estetica_min=5.0, # Porque valora_estetica='sí'
             tipo_mecanica=[TipoMecanica.GASOLINA, TipoMecanica.HEVG], # <--- CORREGIDO (ejemplo) # Porque solo_electricos='no'
            premium_min=1.0, # Porque apasionado_motor='no'
            singular_min=1.0  # Porque apasionado_motor='no'
        ),
        mensaje_validacion="Ok, he definido los filtros técnicos." # Mensaje de confirmación
    )

    # 3. Mockear dependencias: LLM y (opcionalmente) post-procesamiento y prompt
    #    Path donde se USA llm_solo_filtros dentro de nodes.py
    with patch('graph.perfil.nodes.llm_solo_filtros') as mock_llm_filtros, \
         patch('graph.perfil.nodes.system_prompt_filtros_template', "Prompt simulado con {preferencias_contexto}") as mock_prompt_template, \
         patch('graph.perfil.nodes.aplicar_postprocesamiento_filtros', side_effect=lambda f, p: f) as mock_postproc_filtros: 
            # side_effect=lambda f, p: f hace que el mock devuelva el primer argumento que recibe (los filtros) sin cambios.

            # Configurar el mock del LLM (estrategia que funcionó antes)
            mock_llm_filtros.invoke.return_value = respuesta_llm_simulada

            # 4. Ejecutar el nodo
            estado_salida = inferir_filtros_node(estado_inicial)

    # 5. Verificar (Asserts)
    mock_llm_filtros.invoke.assert_called_once() # Verificar llamada al LLM
    mock_postproc_filtros.assert_called_once() # Verificar llamada a post-proc (si lo incluyes)

    filtros_salida = estado_salida.get("filtros_inferidos")
    assert isinstance(filtros_salida, FiltrosInferidos)
    # Verificar algunos campos clave
    assert filtros_salida.estetica_min == 5.0
    assert filtros_salida.tipo_mecanica == [TipoMecanica.GASOLINA, TipoMecanica.HEVG]
    assert filtros_salida.premium_min == 1.0

    mensajes_salida = estado_salida.get("messages", [])
    assert len(mensajes_salida) == len(estado_inicial["messages"]) + 1
    assert isinstance(mensajes_salida[-1], AIMessage)
    assert mensajes_salida[-1].content == respuesta_llm_simulada.mensaje_validacion
    
 #==========================NUEVAS PRUEBAS check_filtros_completos===========================   
# tests/test_nodes.py (continuación)

# Importar el nodo y la función a mockear
from graph.perfil.nodes import validar_filtros_node
# ¡OJO! Path donde se USA check_filtros_completos dentro de nodes.py
PATH_CHECK_FILTROS = 'graph.perfil.nodes.check_filtros_completos' 

# ---- Pruebas para validar_filtros_node ----

def test_validar_filtros_incompleto(estado_con_perfil_completo): # Reutiliza el fixture si quieres
    """
    Prueba que si los filtros están incompletos, el nodo no cambia el estado.
    """
    # Estado con filtros incompletos (ej: tipo_mecanica es None o [])
    estado_inicial = estado_con_perfil_completo.copy() 
    estado_inicial['filtros_inferidos'] = FiltrosInferidos(tipo_mecanica=None) # Forzar filtro incompleto
    estado_inicial['messages'] = estado_inicial['messages'] + [AIMessage(content="Pregunta sobre filtros...")] # Añadir pregunta simulada

    # Mockear check_filtros_completos para que devuelva False
    with patch(PATH_CHECK_FILTROS, return_value=False) as mock_check:
        estado_salida = validar_filtros_node(estado_inicial)
        
    mock_check.assert_called_once_with(estado_inicial["filtros_inferidos"]) 
    # El estado no debe cambiar
    assert estado_salida == estado_inicial 

def test_validar_filtros_completo(estado_con_perfil_completo): # Reutiliza el fixture
    """
    Prueba que si los filtros están completos, el nodo no cambia el estado.
    """
    # Estado con filtros completos
    estado_inicial = estado_con_perfil_completo.copy()
    estado_inicial['filtros_inferidos'] = FiltrosInferidos( # Rellenar campos obligatorios
        tipo_mecanica=[TipoMecanica.GASOLINA] 
        # ... otros filtros ...
    ) 
    estado_inicial['messages'] = estado_inicial['messages'] + [AIMessage(content="Confirmación filtros.")]
    
    # Mockear check_filtros_completos para que devuelva True
    with patch(PATH_CHECK_FILTROS, return_value=True) as mock_check:
        estado_salida = validar_filtros_node(estado_inicial)
        
    mock_check.assert_called_once_with(estado_inicial["filtros_inferidos"])
    # El estado tampoco debe cambiar
    assert estado_salida == estado_inicial
    
    
    
    # tests/test_nodes.py (continuación)

# Importar nodo y función a mockear
from graph.perfil.nodes import validar_economia_node 

# ---- Pruebas para recopilar_economia_node ----

# Usamos el fixture anterior si es útil, o creamos uno nuevo
@pytest.fixture
def estado_listo_para_economia() -> EstadoAnalisisPerfil:
    """Devuelve estado con perfil y filtros completos, listo para economía."""
    # Copia y adapta el fixture 'estado_con_perfil_completo'
    # Asegúrate que PerfilUsuario y FiltrosInferidos estén completos aquí
    return EstadoAnalisisPerfil(
        messages=[AIMessage(content="Confirmación filtros.")], # Último msg de etapa anterior
        preferencias_usuario=PerfilUsuario( # Completo
             altura_mayor_190="no", peso_mayor_100="no", uso_profesional="no", 
             valora_estetica="sí", solo_electricos="no", transmision_preferida=Transmision.AUTOMATICO, 
             apasionado_motor="no", aventura=NivelAventura.ninguna 
        ), 
        filtros_inferidos=FiltrosInferidos( # Completo (al menos tipo_mecanica)
             tipo_mecanica=[TipoMecanica.GASOLINA, TipoMecanica.HEVG], 
             estetica_min=5.0, premium_min=1.0, singular_min=1.0
        ),
        economia=None, # Empezamos sin datos de economía
        mensaje_validacion=None,
        pesos=None
    )

def test_recopilar_economia_primera_pregunta(estado_listo_para_economia):
    """Prueba que pide el modo si no hay datos económicos."""
    estado_inicial = estado_listo_para_economia
    # Añadir el mensaje humano que inicia esta etapa (podría ser implícito)
    estado_para_invocar = estado_inicial.copy()
    estado_para_invocar["messages"] = estado_inicial["messages"] + [HumanMessage(content="Sí, ayúdame con el presupuesto")]

    # Respuesta simulada del LLM pidiendo el modo
    respuesta_llm_simulada = ResultadoEconomia(
        economia=EconomiaUsuario(), # Devuelve objeto vacío
        mensaje_validacion="Para el presupuesto, ¿prefieres 1) Asesoramiento o 2) Definirlo tú?" # Pregunta por modo
    )

    # Mockear
    with patch('graph.perfil.nodes.llm_economia') as mock_llm_econ:
        mock_llm_econ.invoke.return_value = respuesta_llm_simulada
        
        estado_salida = recopilar_economia_node(estado_para_invocar)

    # Asserts
    mock_llm_econ.invoke.assert_called_once()
    assert estado_salida["economia"] is not None # Se inicializó
    assert estado_salida["economia"].modo is None # Aún no se ha establecido
    assert isinstance(estado_salida["messages"][-1], AIMessage)
    assert "¿prefieres 1) Asesoramiento o 2) Definirlo tú?" in estado_salida["messages"][-1].content

def test_recopilar_economia_procesa_respuesta_actualiza_estado(estado_listo_para_economia):
    """Prueba que procesa una respuesta, actualiza estado y pide siguiente dato."""
    # Estado inicial: ya se preguntó por el modo, usuario responde modo 1
    estado_inicial = estado_listo_para_economia.copy()
    estado_inicial["messages"] = estado_inicial["messages"] + [
        AIMessage(content="Para el presupuesto, ¿prefieres 1) Asesoramiento o 2) Definirlo tú?"),
        HumanMessage(content="Prefiero la opción 1")
    ]
    estado_inicial["economia"] = EconomiaUsuario() # Economía vacía inicialmente

    # Respuesta simulada del LLM: extrae modo=1 y pregunta por ingresos
    respuesta_llm_simulada = ResultadoEconomia(
        economia=EconomiaUsuario.model_construct(modo=1), 
        mensaje_validacion="Ok, modo asesor. ¿Cuáles son tus ingresos mensuales netos aprox?" # Pide ingresos
    )

    # Mockear
    with patch('graph.perfil.nodes.llm_economia') as mock_llm_econ:
        mock_llm_econ.invoke.return_value = respuesta_llm_simulada
        estado_salida = recopilar_economia_node(estado_inicial)

    # Asserts
    mock_llm_econ.invoke.assert_called_once()
    econ_salida = estado_salida["economia"]
    assert isinstance(econ_salida, EconomiaUsuario)
    assert econ_salida.modo == 1 # ¡Se actualizó el modo!
    assert econ_salida.ingresos is None # Aún falta
    assert isinstance(estado_salida["messages"][-1], AIMessage)
    assert "¿Cuáles son tus ingresos mensuales netos aprox?" in estado_salida["messages"][-1].content


def test_recopilar_economia_ignora_ai_message(estado_listo_para_economia):
    """Prueba que ignora la llamada al LLM si el último mensaje es AI.
       (Usando patch sobre el objeto completo) # <-- Estrategia correcta
    """
    estado_inicial = estado_listo_para_economia.copy()
    estado_inicial["messages"] = estado_inicial["messages"] + [AIMessage(content="Pregunta de economía...")]
    # Crear estado parcial sin validación para la prueba
    estado_inicial["economia"] = EconomiaUsuario.model_construct(modo=1) 

    # Mockear TODO el objeto llm_economia (¡La estrategia que funciona!)
    # Path SIN el '.invoke'
    with patch('graph.perfil.nodes.llm_economia') as mock_llm_econ_objeto_completo:
         
         # No configuramos return_value para invoke porque no esperamos que se llame

         # Ejecutar la función del nodo
         estado_salida = recopilar_economia_node(estado_inicial)

    # Verificar (Asserts)
    
    # ¡Verificar que el método invoke DEL OBJETO MOCKEADO NO fue llamado!
    mock_llm_econ_objeto_completo.invoke.assert_not_called() 
    
    # Verificar que el estado de salida es IDÉNTICO al de entrada
    # (El nodo no debería haber hecho nada porque el último mensaje era AIMessage)
    assert estado_salida == estado_inicial


# Podrías añadir prueba para el caso de ValidationError capturado si quieres

from graph.perfil.nodes import validar_economia_node 
# Path donde se USA check_economia_completa dentro de nodes.py
PATH_CHECK_ECONOMIA = 'graph.perfil.nodes.check_economia_completa' 
# ---- Pruebas para validar_economia_node ----


def test_validar_economia_incompleta(estado_listo_para_economia):
    """Prueba que si economía está incompleta, el nodo no cambia estado."""
    estado_inicial = estado_listo_para_economia.copy()
    estado_inicial["economia"] = EconomiaUsuario.model_construct(modo=1) 

    # Mockear check_economia_completa -> False
    with patch(PATH_CHECK_ECONOMIA, return_value=False) as mock_check:
        estado_salida = validar_economia_node(estado_inicial)
        
    mock_check.assert_called_once_with(estado_inicial["economia"]) 
    assert estado_salida == estado_inicial # Estado sin cambios

def test_validar_economia_completa(estado_listo_para_economia):
    """Prueba que si economía está completa, el nodo no cambia estado."""
    estado_inicial = estado_listo_para_economia.copy()
    estado_inicial["economia"] = EconomiaUsuario(modo=1, ingresos=50000, ahorro=10000) # Completo

    # Mockear check_economia_completa -> True
    with patch(PATH_CHECK_ECONOMIA, return_value=True) as mock_check:
        estado_salida = validar_economia_node(estado_inicial)
        
    mock_check.assert_called_once_with(estado_inicial["economia"])
    assert estado_salida == estado_inicial # Estado sin cambios
    
    
    
    

import pytest
from unittest.mock import patch, MagicMock 

# Importar el nodo final y las funciones/tipos necesarios
from graph.perfil.nodes import finalizar_y_presentar_node 
from graph.perfil.state import EstadoAnalisisPerfil, PerfilUsuario, FiltrosInferidos, EconomiaUsuario
from utils.enums import Transmision, NivelAventura, TipoMecanica # Importar todos los Enums usados
from langchain_core.messages import HumanMessage, AIMessage

# ---- Fixture para Estado Completo ----
@pytest.fixture
def estado_todo_completo() -> EstadoAnalisisPerfil:
    """Devuelve un estado con perfil, filtros (sin carrocería) y economía completos."""
    prefs = PerfilUsuario( 
             altura_mayor_190="no", peso_mayor_100="no", uso_profesional="no", 
             valora_estetica="sí", solo_electricos="no", transmision_preferida=Transmision.AUTOMATICO, 
             apasionado_motor="no", aventura=NivelAventura.ninguna 
    )
    filts = FiltrosInferidos( 
             tipo_mecanica=[TipoMecanica.GASOLINA, TipoMecanica.HEVG], 
             estetica_min=5.0, premium_min=1.0, singular_min=1.0,
             tipo_carroceria=None # Importante: empieza vacío para probar el RAG
    )
    econ = EconomiaUsuario(modo=1, ingresos=50000, ahorro=10000) # Ejemplo modo 1 completo

    return EstadoAnalisisPerfil(
        messages=[
            HumanMessage(content="..."), 
            AIMessage(content="Pregunta economía..."),
            HumanMessage(content="Respuesta economía...") ,
            AIMessage(content="Confirmación economía.") # Último mensaje etapa anterior
            ],
        preferencias_usuario=prefs, 
        filtros_inferidos=filts,
        economia=econ, 
        mensaje_validacion=None, # Ya no debería haber mensaje de validación
        pesos=None # Aún no se han calculado
    )

# ---- Prueba para finalizar_y_presentar_node ----

# Definir los paths a las funciones que están DENTRO de nodes.py (o donde las importe)
PATH_RAG = 'graph.perfil.nodes.get_recommended_carrocerias'
PATH_RAW_WEIGHTS = 'graph.perfil.nodes.compute_raw_weights'
PATH_NORM_WEIGHTS = 'graph.perfil.nodes.normalize_weights'
PATH_FORMATTER = 'graph.perfil.nodes.formatear_preferencias_en_tabla'

def test_finalizar_y_presentar_nodo_happy_path(estado_todo_completo):
    """
    Prueba el camino feliz del nodo final: llama a RAG, pesos, formato 
    y actualiza el estado correctamente.
    """
    # 1. Estado de ENTRADA (fixture)
    estado_inicial = estado_todo_completo

    # 2. Definir las RESPUESTAS SIMULADAS de las utilidades
    rag_simulado = ['SUV_TEST', 'SEDAN_TEST']
    raw_weights_simulado = {'estetica': 5.0, 'premium': 1.0, 'singular': 1.0, 'altura_libre_suelo': 0.0, 'traccion': 0.0, 'reductoras': 0.0} # Ejemplo
    norm_weights_simulado = {'estetica': 0.71, 'premium': 0.14, 'singular': 0.14, 'altura_libre_suelo': 0.0, 'traccion': 0.0, 'reductoras': 0.0} # Ejemplo
    tabla_simulada = "### Resumen Final Simulado Markdown ###"

    # 3. Mockear TODAS las llamadas a utilidades externas
    with patch(PATH_RAG, return_value=rag_simulado) as mock_rag, \
         patch(PATH_RAW_WEIGHTS, return_value=raw_weights_simulado) as mock_raw_weights, \
         patch(PATH_NORM_WEIGHTS, return_value=norm_weights_simulado) as mock_norm_weights, \
         patch(PATH_FORMATTER, return_value=tabla_simulada) as mock_formatter:

            # 4. Ejecutar el nodo final
            estado_salida = finalizar_y_presentar_node(estado_inicial)

    # 5. Verificar (Asserts)
    
    # 5.1 Verificar llamadas a mocks
    mock_rag.assert_called_once()
    # Verificar que se llamó a RAG con los dicts correctos (o Pydantic si la función los acepta)
    # mock_rag.assert_called_once_with(estado_inicial['preferencias_usuario'].model_dump(mode='json'), estado_inicial['filtros_inferidos'].model_dump(mode='json'), k=4)
    
    mock_raw_weights.assert_called_once()
    # Verificar args de pesos (ej: que aventura_level se pase correctamente)
   # --- CORRECCIÓN AQUÍ: Verificar kwargs ---
    # Accedemos directamente a call_args.kwargs que es un diccionario
    kwargs_raw_weights = mock_raw_weights.call_args.kwargs
    assert kwargs_raw_weights.get("estetica") == estado_inicial['filtros_inferidos'].estetica_min
    assert kwargs_raw_weights.get("aventura_level") == estado_inicial['preferencias_usuario'].aventura
    # Verificar otros kwargs si quieres: premium, singular

    mock_norm_weights.assert_called_once_with(raw_weights_simulado) # Se le pasa el resultado del mock anterior

    mock_formatter.assert_called_once()
    kwargs_formatter = mock_formatter.call_args.kwargs
    # Verificar que los objetos correctos se pasaron por nombre
    assert kwargs_formatter.get("preferencias") == estado_inicial['preferencias_usuario']
    # Importante: verificar que el filtro pasado incluye la carrocería del RAG simulado
    assert kwargs_formatter.get("filtros").tipo_carroceria == rag_simulado 
    assert kwargs_formatter.get("economia") == estado_inicial['economia']

    # 5.2 Verificar estado de salida (esto estaba bien)
    assert estado_salida["filtros_inferidos"].tipo_carroceria == rag_simulado
    assert estado_salida["pesos"] == norm_weights_simulado
    assert len(estado_salida["messages"]) == len(estado_inicial["messages"]) + 1
    assert isinstance(estado_salida["messages"][-1], AIMessage)
    assert estado_salida["messages"][-1].content == tabla_simulada