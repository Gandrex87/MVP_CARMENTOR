from utils.generadores import generar_mensaje_validacion_dinamico
from langchain_core.messages import HumanMessage
from config.llm import llm_validacion
from utils.generadores import generar_mensaje_validacion_dinamico


# Simulación de conversación (historial de mensajes)
historial = [
    HumanMessage(content="Busco un coche elegante y automático para ciudad, mido 1.80")
]

# Casos de prueba para preferencias y filtros
preferencias_simples = {
    "altura_mayor_190": "no",
    "peso_mayor_100": "no",
    "uso_profesional": "sí",
    "valora_estetica": "sí",
    "solo_electricos": "sí",
    "cambio_automatico": "sí",
    "apasionado_motor": None
}

filtros_incompletos = {
    "tipo_carroceria": [],
    "tipo_mecanica": [],
    "premium_min": None,
    "singular_min": None
}

def test_generar_mensaje_validacion_dinamico():
    respuesta = generar_mensaje_validacion_dinamico(
        preferencias_simples,
        filtros_incompletos,
        historial,
        llm_validacion
    )
    print("✅ Respuesta generada:\n", respuesta.content)
    assert respuesta.content != ""

def test_generar_mensaje_solo_una_preferencia():
    preferencias = {
        "altura_mayor_190": "no",
        "peso_mayor_100": "no",
        "uso_profesional": "sí",
        "valora_estetica": "sí",
        "solo_electricos": "sí",
        "cambio_automatico": "sí",
        "apasionado_motor": "sí"
    }
    filtros = {
        "tipo_carroceria": ["SUV"],
        "tipo_mecanica": ["BEV"],
        "premium_min": 7.0,
        "singular_min": 7.0
    }
    respuesta = generar_mensaje_validacion_dinamico(preferencias, filtros, historial, llm_validacion)
    print("🔹Respuesta con 1 campo faltante:\n", respuesta.content)
    assert "" != respuesta.content

def test_generar_mensaje_filtros_faltantes():
    preferencias = {
        "altura_mayor_190": "no",
        "peso_mayor_100": "no",
        "uso_profesional": "no",
        "valora_estetica": "sí",
        "solo_electricos": "sí",
        "cambio_automatico": "sí",
        "apasionado_motor": "no"
    }
    filtros = {
        "tipo_carroceria": [],
        "tipo_mecanica": [],
        "premium_min": None,
        "singular_min": None
    }
    respuesta = generar_mensaje_validacion_dinamico(preferencias, filtros, historial, llm_validacion)
    print("🔸Respuesta con filtros faltantes:\n", respuesta.content)
    assert "" != respuesta.content
