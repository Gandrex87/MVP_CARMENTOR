# En graph/condition.py
from .state import EstadoAnalisisPerfil # o donde esté tu TypedDict
from utils.validation import check_perfil_usuario_completeness, check_filtros_completos, check_economia_completa
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
        return "pasar_a_filtros" 
    else:
        print("DEBUG (Condición Perfil) ► Perfil INCOMPLETO. Se necesita pregunta.")
        # String que mapearemos al nuevo nodo preguntar_preferencias_node
        return "necesita_pregunta_perfil"

def ruta_decision_filtros(state: EstadoAnalisisPerfil) -> str:
    """Decide si los filtros están completos para pasar a economía o si necesita más información."""
    print("--- Evaluando Condición: ruta_decision_filtros ---")
    filtros = state.get("filtros_inferidos")
    if check_filtros_completos(filtros):
        print("DEBUG (Condición Filtros) ► Filtros COMPLETOS. Avanzando a economía.")
        return "pasar_a_economia" # Ruta hacia la siguiente etapa
    else:
        print("DEBUG (Condición Filtros) ► Filtros INCOMPLETOS. Volviendo a inferir filtros.")
        # Volvemos al nodo que procesa/pregunta por filtros
        return "necesita_pregunta_filtro"

# En builder.py o condition.py

def ruta_decision_economia(state: EstadoAnalisisPerfil) -> str:
    """Decide si la economía está completa para finalizar o si necesita preguntar."""
    print("--- Evaluando Condición: ruta_decision_economia ---")
    economia = state.get("economia")
    # Llama a la utilidad que verifica la completitud
    if check_economia_completa(economia):
        print("DEBUG (Condición Economía) ► Economía COMPLETA. Avanzando a finalizar.")
        # Clave para ir al nodo final
        return "pasar_a_finalizar" 
    else:
        print("DEBUG (Condición Economía) ► Economía INCOMPLETA. Se necesita pregunta.")
        # Clave para ir al nuevo nodo que pregunta
        return "necesita_pregunta_economia"
