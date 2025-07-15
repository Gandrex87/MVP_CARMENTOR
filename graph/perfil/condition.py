# En graph/condition.py
from .state import EstadoAnalisisPerfil # o donde esté tu TypedDict
from utils.validation import check_perfil_usuario_completeness, check_economia_completa, check_pasajeros_completo
from typing import Literal


# --- NUEVA Función Condicional para la Etapa - 0 de Codigo Postal ---
def ruta_decision_cp(state: EstadoAnalisisPerfil) -> Literal["buscar_clima", "repreguntar_cp"]:
    """Decide si el CP es válido para buscar clima o si hay que repreguntar."""
    print("--- Evaluando Condición: ruta_decision_cp ---")
    decision = state.get("_decision_cp_validation") # Clave puesta por validar_cp_node
    if decision == "cp_valido_listo_para_clima":
        print("DEBUG (Condición CP) ► CP válido/omitido. Procediendo a buscar clima.")
        return "buscar_clima"
    else: # "repreguntar_cp" o cualquier otro caso
        print("DEBUG (Condición CP) ► CP inválido o aclaración necesaria. Repreguntando.")
        return "repreguntar_cp"


def ruta_decision_pasajeros(state: EstadoAnalisisPerfil) -> Literal["aplicar_filtros", "necesita_pregunta_pasajero"]:
    """Decide si la info de pasajeros está completa."""
    print("--- Evaluando Condición: ruta_decision_pasajeros ---")
    info = state.get("info_pasajeros")
    if check_pasajeros_completo(info):
        print("DEBUG (Condición Pasajeros) ► COMPLETO. Aplicando filtros derivados.")
        return "aplicar_filtros"
    else:
        print("DEBUG (Condición Pasajeros) ► INCOMPLETO. Se necesita pregunta.")
        return "necesita_pregunta_pasajero"


def ruta_post_preferencias(state: EstadoAnalisisPerfil) -> str:
    """Decide la ruta después de validar las preferencias."""

    # Obtén los diccionarios (o Pydantic models si prefieres pasar esos)
    prefs = state.get("preferencias_usuario")
    filts = state.get("filtros_inferidos")

    # Convierte a dict si son Pydantic models antes de pasar a la utilidad
    # (O modifica la utilidad para que acepte Pydantic models)
    prefs_dict = prefs.model_dump() if hasattr(prefs, "model_dump") else prefs
    filts_dict = filts.model_dump() if hasattr(filts, "model_dump") else filts

    if not check_perfil_usuario_completeness(prefs_dict, filts_dict):
        # Si NO está completo, volvemos a analizar la siguiente entrada del usuario
        # (que debería ser la respuesta a la pregunta que hizo validar_preferencias)
        # El flujo correcto es volver a 'analizar_perfil_usuario' para procesar la nueva respuesta.
        # Sin embargo, el problema suele estar en el bucle externo. 
        # La ruta en sí misma puede estar bien, pero asegúrate que tras la pregunta de la IA,
        # esperas la respuesta del usuario. 
        # Por ahora, mantenemos la lógica de ruta:
        return "analizar_perfil_usuario" 
    else:
        # Si SÍ está completo, avanzamos a economía
        return "validar_economia"


# --- Funciones Condicionales para Enrutamiento ---

def ruta_decision_perfil(state: EstadoAnalisisPerfil) -> str:
    """Decide si el perfil está completo para pasar a filtros o si necesita preguntar."""
    print("--- Evaluando Condición: ruta_decision_perfil ---")
    preferencias = state.get("preferencias_usuario")
    print(f"DEBUG (Condición Perfil) ► Estado 'preferencias_usuario' recibido: {preferencias}") # <-- Nuevo Print
    print(f"DEBUG (Condición Perfil) ► Tipo de 'preferencias_usuario': {type(preferencias)}") # <-- Nuevo Print
    # Llama a la función de utilidad que ya teníamos
    if check_perfil_usuario_completeness(preferencias):
        print("DEBUG (Condición Perfil) ► Perfil COMPLETO. Avanzando a filtros.")
        # String que mapearemos a inferir_filtros_node
        return "pasar_a_pasajeros" # <-- Nueva clave de salida
    else:
        print("DEBUG (Condición Perfil) ► Perfil INCOMPLETO. Se necesita pregunta.")
        # String que mapearemos al nuevo nodo preguntar_preferencias_node
        return "necesita_pregunta_perfil"

# En builder.py o condition.py

def ruta_decision_economia(state: EstadoAnalisisPerfil) -> str:
    """Decide si la economía está completa para finalizar o si necesita preguntar."""
    print("--- Evaluando Condición: ruta_decision_economia ---")
    economia = state.get("economia")
    # Llama a la utilidad que verifica la completitud
    if check_economia_completa(economia):
        print("DEBUG (Condición Economía) ► Economía COMPLETA. Avanzando a finalizar.")
        # Clave para ir al nodo final
        return "iniciar_finalizacion"
    else:
        print("DEBUG (Condición Economía) ► Economía INCOMPLETA. Se necesita pregunta.")
        # Clave para ir al nuevo nodo que pregunta
        return "necesita_pregunta_economia"


# --- NUEVO NODO ROUTER (Muy simple) ---
def route_based_on_state_node(state: EstadoAnalisisPerfil) -> dict:
    """Nodo intermedio que no hace nada, solo permite la bifurcación inicial."""
    print("--- Ejecutando Nodo: route_based_on_state_node ---")
    # No modifica el estado, solo lo pasa
    return {**state}


def decidir_ruta_inicial(state: EstadoAnalisisPerfil) -> str:
    """Decide a qué etapa saltar al inicio de una invocación."""
    print("\n--- DEBUG: Evaluating Routing Decision ---")
    info_clima = state.get("info_clima_usuario") 
    preferencias = state.get("preferencias_usuario")
    info_pasajeros = state.get("info_pasajeros")
    filtros = state.get("filtros_inferidos")
    economia = state.get("economia")
    pesos = state.get("pesos")
    coches = state.get("coches_recomendados")
    
    # Prints de depuración (opcional mantenerlos)
    print(f"DEBUG Router: Codigo Postal OK? {info_clima is not None}")
    print(f"DEBUG Router: Prefs OK? {check_perfil_usuario_completeness(preferencias)}")
    print(f"DEBUG Router: Pasajeros OK? {check_pasajeros_completo(info_pasajeros)}")
    print(f"DEBUG Router: Economía OK? {check_economia_completa(economia)}")
    print(f"DEBUG Router: Pesos Calculados? {pesos is not None}")
    print(f"DEBUG Router: Coches Buscados? {coches is not None}")

    # Lógica de enrutamiento en orden
    if info_clima is None: # Si nunca hemos intentado obtener info_clima
        print("DEBUG Router: Decisión -> recopilar_cp (Etapa CP no completada)")
        return "recopilar_cp" 
    # Si info_clima existe (incluso si cp_valido_encontrado es False), la etapa de CP/Clima se considera "pasada".
    # Continuar con la lógica de las siguientes etapas: Perfil -> Pasajeros -> Filtros ...   
    elif not check_perfil_usuario_completeness(preferencias):
        print("DEBUG Router: Decisión -> recopilar_preferencias")
        return "recopilar_preferencias" 
    elif not check_pasajeros_completo(info_pasajeros):
        print("DEBUG Router: Decisión -> recopilar_info_pasajeros")
        return "recopilar_info_pasajeros"
    elif not check_economia_completa(economia):
         print("DEBUG Router: Decisión -> recopilar_economia")
         return "recopilar_economia" 
    elif pesos is None: 
        # Si falta algún paso de la secuencia de finalización (cálculo de econ modo1, rag, flags, pesos)
        print("DEBUG Router: Decisión -> iniciar_finalizacion (va a calcular_recomendacion_economia_modo1)")
        return "iniciar_finalizacion"
    elif coches is None: # Si todo lo anterior está completo y los pesos están, pero no hay coches
        print("DEBUG Router: Decisión -> buscar_coches_finales")
        return "buscar_coches_finales"
    else: # Conversación completa y coches ya buscados, reiniciar para una nueva consulta
        print("DEBUG Router: Decisión -> Conversación Completa con coches. Reiniciando (recopilar_cp).")
        return "recopilar_cp"