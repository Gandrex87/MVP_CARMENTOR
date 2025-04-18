# Separar responsabilidades: dejar al LLM lo fácil y completar lo crítico
# En lugar de depender de que el LLM devuelva la lista completa, se definen reglas de negocio fija:
# 🧠 Este es el enfoque más robusto y estándar en producción:
# Combinar inferencia + reglas determinísticas para asegurar integridad del estado.

def aplicar_postprocesamiento(preferencias, filtros):
    if hasattr(preferencias, "model_dump"):
        preferencias = preferencias.model_dump()
    if hasattr(filtros, "model_dump"):
        filtros = filtros.model_dump()

    def es_nulo(valor):
        return valor in [None, "", "null", "0.0"]
    
      # ────────────── REGLA ELÉCTRICO → AUTOMÁTICO ──────────────
    solo_elec = preferencias.get("solo_electricos", "").strip().lower()
    if solo_elec in ["sí", "si"] and es_nulo(preferencias.get("cambio_automatico")):
        preferencias["cambio_automatico"] = "si"
    # ────────────────────────────────────────────────────────────

    # 1. Tipo de mecánica si no quiere eléctricos
    if preferencias.get("solo_electricos", "").strip().lower() == "no" and not filtros.get("tipo_mecanica"):
        filtros["tipo_mecanica"] = [
            "GASOLINA", "DIESEL", "FCEV", "GLP", "GNV",
            "HEVD", "HEVG", "MHEVD", "MHEVG", "PHEVD", "PHEVG", "REEV"
        ]

    # 2. Estética mínima según preferencia
    valora_estetica = preferencias.get("valora_estetica", "").strip().lower()
    if valora_estetica in ["sí", "si"] and es_nulo(filtros.get("estetica_min")):
        filtros["estetica_min"] = 7.0
    elif valora_estetica == "no" and es_nulo(filtros.get("estetica_min")):
        filtros["estetica_min"] = 1.0

    # 3. Premium y singularidad según pasión por el motor
    apasionado = preferencias.get("apasionado_motor", "").strip().lower()
    if apasionado in ["sí", "si"]:
        if es_nulo(filtros.get("premium_min")):
            filtros["premium_min"] = 7.0
        if es_nulo(filtros.get("singular_min")):
            filtros["singular_min"] = 7.0
    elif apasionado == "no":
        if es_nulo(filtros.get("premium_min")):
            filtros["premium_min"] = 1.0
        if es_nulo(filtros.get("singular_min")):
            filtros["singular_min"] = 1.0

    return preferencias, filtros



##por ahora no va XX
def tiene_preferencias_completas(preferencias: dict) -> bool:
    if hasattr(preferencias, "model_dump"):
        preferencias = preferencias.model_dump()
    return all(value not in [None, "", "null"] for value in preferencias.values())

# --- Nueva función para detectar fuera de dominio ---
def es_fuera_de_dominio(texto: str) -> bool:
    fuera = [
        "moto", "motocicleta", "bicicleta", "barco", "avión", "camión", "camioneta",
        "perro", "gato", "mascota", "ropa", "restaurante", "comida", "celular", "teléfono"
    ]
    return any(palabra in texto.lower() for palabra in fuera)





