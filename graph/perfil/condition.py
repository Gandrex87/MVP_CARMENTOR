from .state import EstadoAnalisisPerfil

# actúa como una función de control de flujo del grafo.
# Ayuda a que el grafo sea más modular y mantenible: condiciones, nodos y estado en archivos bien diferenciados.

# graph/perfil/condition.py
def necesita_mas_info(state: EstadoAnalisisPerfil) -> str:
    # Preferencias
    preferencias = state.get("preferencias_usuario", {})
    if hasattr(preferencias, "model_dump"):
        preferencias = preferencias.model_dump()

    campos_preferencias = [
        "solo_electricos", "uso_profesional", "altura_mayor_190", "peso_mayor_100", 
        "valora_estetica", "cambio_automatico","apasionado_motor"
        ]
    prefs_completas = all(preferencias.get(c) not in [None, "null", ""] for c in campos_preferencias)

    # Filtros inferidos
    filtros = state.get("filtros_inferidos", {})
    if hasattr(filtros, "model_dump"):
        filtros = filtros.model_dump()

    filtros_criticos = ["tipo_mecanica", "tipo_carroceria","premium_min", "singular_min"]
    filtros_completos = all(filtros.get(f) not in [None, [], "null", ""] for f in filtros_criticos)

    if prefs_completas and filtros_completos:
        return "END"
    return "repetir"