# Separar responsabilidades: dejar al LLM lo fácil y completar lo crítico
# En lugar de depender de que el LLM devuelva la lista completa, se definen reglas de negocio fija:
# Este enfoque más robusto y estándar en producción:
# Combinar inferencia + reglas determinísticas para asegurar integridad del estado.

# utils/postprocessing.py
from utils.rag_carroceria import get_recommended_carrocerias, AVENTURA_SYNONYMS

def aplicar_postprocesamiento(preferencias, filtros):
    # ─── 0. Inicialización segura ───
    if preferencias is None:
        preferencias = {}
    elif hasattr(preferencias, "model_dump"):
        preferencias = preferencias.model_dump()

    if filtros is None:
        filtros = {}
    elif hasattr(filtros, "model_dump"):
        filtros = filtros.model_dump()

    def es_nulo(valor):
        return valor in [None, "", "null", "0.0"]

    # ─── 1. Regla eléctrico → automático ───
    solo_elec_raw = preferencias.get("solo_electricos") or ""
    solo_elec = str(solo_elec_raw).strip().lower()
    if solo_elec in ["sí", "si"]:
        cambio_raw = preferencias.get("cambio_automatico")
        if es_nulo(cambio_raw):
            preferencias["cambio_automatico"] = "si"

    # ─── 2. Tipo de mecánica si no quiere eléctricos ───
    if solo_elec == "no" and not filtros.get("tipo_mecanica"):
        filtros["tipo_mecanica"] = [
            "GASOLINA", "DIESEL", "FCEV", "GLP", "GNV",
            "HEVD", "HEVG", "MHEVD", "MHEVG", "PHEVD", "PHEVG", "REEV"
        ]

    # ─── 3. Estética mínima ───
    val_est_raw = preferencias.get("valora_estetica") or ""
    val_est = str(val_est_raw).strip().lower()
    if val_est in ["sí", "si"]:
        filtros["estetica_min"] = 5.0
    else:
        filtros["estetica_min"] = 1.0

    # ─── 4. Premium y singularidad ───
    apasionado_raw = preferencias.get("apasionado_motor") or ""
    apasionado = str(apasionado_raw).strip().lower()
    if apasionado in ["sí", "si"]:
        filtros["premium_min"]  = 5.0
        filtros["singular_min"] = 5.0
    else:
        filtros["premium_min"]  = 1.0
        filtros["singular_min"] = 1.0

    # ─── 5. Tipo de carrocería via RAG (sólo si ya sabemos algo de aventura o de uso profesional) ───
    tiene_uso   = preferencias.get("uso_profesional") not in (None, "", "null")
    tiene_av   =  preferencias.get("aventura") in AVENTURA_SYNONYMS.keys()
    if not filtros.get("tipo_carroceria") and tiene_uso and tiene_av:
        filtros["tipo_carroceria"] = get_recommended_carrocerias(preferencias, filtros)

    return preferencias, filtros






