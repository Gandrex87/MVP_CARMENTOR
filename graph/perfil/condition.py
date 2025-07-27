# En graph/condition.py
from .state import EstadoAnalisisPerfil # o donde esté tu TypedDict
from utils.validation import check_perfil_usuario_completeness, check_economia_completa, check_pasajeros_completo
from typing import Literal
import logging


def ruta_decision_cp_refactorizada(state: EstadoAnalisisPerfil) -> str:
    """Función simple que lee la decisión tomada en el nodo anterior."""
    return state.get("_decision_cp_validation")




def decidir_siguiente_paso_pasajeros(state: EstadoAnalisisPerfil) -> str:
    """
    Esta función actúa como una ARISTA CONDICIONAL para el módulo de pasajeros.
    Revisa si la información está completa para decidir si seguir preguntando
    o si es momento de mostrar el mensaje de transición.
    """
    print("--- [Edge/Pasajeros] Decidiendo siguiente paso de pasajeros ---")
    
    info_pasajeros = state.get("info_pasajeros")
    
    # ▼▼▼ CAMBIO AQUÍ ▼▼▼
    if check_pasajeros_completo(info_pasajeros):
        # Si la info está completa, el siguiente paso es generar el mensaje de transición.
        print("✅ Info Pasajeros completa. Pasando a 'generar_mensaje_transicion_pasajeros'.")
        return "generar_mensaje_transicion_pasajeros" # <-- ¡ESTE ES EL CAMBIO!
    else:
        # Si está incompleta, formulamos la siguiente pregunta como antes.
        print("❌ Info Pasajeros incompleta. Transición a 'preguntar_info_pasajeros'.")
        return "preguntar_info_pasajeros"


def decidir_siguiente_paso_perfil(state: EstadoAnalisisPerfil) -> str:
    """
    Esta función actúa como una ARISTA CONDICIONAL.
    Revisa si el perfil está completo para decidir si seguir preguntando
    o si es momento de mostrar el mensaje de transición.
    """
    print("--- [Edge/Perfil] Decidiendo siguiente paso del perfil ---")
    
    preferencias = state.get("preferencias_usuario")
    
    # ▼▼▼ CAMBIO AQUÍ ▼▼▼
    if check_perfil_usuario_completeness(preferencias):
        # Si el perfil está completo, vamos al nodo que genera el mensaje de transición.
        print("✅ Perfil completo. Pasando a 'generar_mensaje_transicion'.")
        return "generar_mensaje_transicion" # <-- ¡ESTE ES EL CAMBIO!
    else:
        # Si está incompleto, seguimos preguntando como antes.
        print("-> Perfil incompleto. Transición a 'preguntar_preferencias'.")
        return "preguntar_preferencias"



#
def decidir_siguiente_paso_economia(state: EstadoAnalisisPerfil) -> str:
    """
    Decide si la información económica está completa para finalizar la etapa
    o si se necesita formular otra pregunta.
    """
    logging.info("--- [Edge/Economía] Decidiendo siguiente paso de economía ---")
    
    economia = state.get("economia")
    
    if check_economia_completa(economia):
        # Si la información está completa, hemos terminado esta etapa.
        # Devolvemos la clave para iniciar la finalización.
        logging.info("✅ Info Economía completa. Avanzando a la finalización.")
        
        # ▼▼▼ ESTA ES LA LÍNEA CORREGIDA ▼▼▼
        # Devolvemos "iniciar_finalizacion" para que coincida con la clave
        # que tu builder.py está esperando.
        return "iniciar_finalizacion"
    else:
        # Si falta información, volvemos a preguntar.
        logging.info("❌ Info Economía incompleta. Transición a 'preguntar_economia'.")
        return "preguntar_economia"

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
    #filtros = state.get("filtros_inferidos")
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

    messages = state.get("messages", [])
    if not messages:
        # Si no hay mensajes, es el inicio. Vamos al nodo de bienvenida.
        print("DEBUG Router: Decisión -> Conversación nueva. Ir a 'saludo_y_pregunta_inicial'.")
        return "iniciar_conversacion"
    
    # Lógica de enrutamiento en orden
    if info_clima is None:
        print("DEBUG Router: Decisión -> recopilar_cp (Etapa CP no completada)")
        return "recopilar_cp" 
    elif not check_perfil_usuario_completeness(preferencias):
        print("DEBUG Router: Decisión -> recopilar_preferencias")
        return "recopilar_preferencias" 
    # Si info_clima existe (incluso si cp_valido_encontrado es False), la etapa de CP/Clima se considera "pasada".
    # Continuar con la lógica de las siguientes etapas: Perfil -> Pasajeros -> Filtros ...   
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
        print("DEBUG Router: Decisión -> Conversación Completa con coches. Reiniciando con saludo.")
        # APUNTAMOS A LA NUEVA RUTA DE INICIO
        return "iniciar_conversacion"
    


