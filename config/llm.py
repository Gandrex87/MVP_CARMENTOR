# instanciación del modelo, init_chat_model, y configuración de structured_llm.
from langchain.chat_models import init_chat_model
from graph.perfil.state import ResultadoSoloPerfil, ResultadoSoloFiltros, ResultadoEconomia, ResultadoPasajeros, ResultadoCP# Ajusta la ruta de importación
from dotenv import load_dotenv
import logging

load_dotenv()

# # --- LLMs Base ---
# llm = init_chat_model("openai:gpt-4o-mini", temperature=0.2) 

# # LLM para generar preguntas de seguimiento más naturales (si es necesario)
# llm_validacion = init_chat_model("openai:gpt-4o-mini", temperature=0.4) 

# # --- LLMs con Salida Estructurada por Etapa ---

# # 1. LLM para la Etapa de Perfil del Usuario
# # Usará un prompt específico para perfil y devolverá solo PerfilUsuario + mensaje_validacion
# llm_solo_perfil = llm.with_structured_output(ResultadoSoloPerfil , method="function_calling")

  
# # 2. LLM para la Etapa de Inferencia de Filtros
# #    Usará un prompt específico para filtros (recibiendo el perfil como contexto)
# #    y devolverá solo FiltrosInferidos + mensaje_validacion
# llm_solo_filtros = llm.with_structured_output(ResultadoSoloFiltros)

# # 3. LLM para la Etapa de Economía (Sin cambios)
# # --- USA UN MODELO MÁS POTENTE PARA ECONOMÍA ---
# llm_potente = init_chat_model("openai:gpt-4o-mini", temperature=0.1) # O el ID correcto para gpt-4o
# llm_economia = llm_potente.with_structured_output(ResultadoEconomia, method="function_calling")

# # --- NUEVA CONFIGURACIÓN LLM PARA PASAJEROS ---
# # 4. LLM para la Etapa de Información de Pasajeros
# #    Usará el prompt system_prompt_pasajeros.txt y devolverá ResultadoPasajeros
# llm_pasajeros = llm.with_structured_output(ResultadoPasajeros)

# # --- NUEVA CONFIGURACIÓN LLM PARA CÓDIGO POSTAL ---
# # Usará el prompt system_prompt_cp.txt y devolverá ResultadoCP
# llm_cp_extractor = llm.with_structured_output(ResultadoCP,  method="function_calling")


# # --- NUEVA CONFIGURACIÓN LLM RESUMEN COCHE ---
# llm_res = init_chat_model("openai:gpt-3.5-turbo", temperature=0.4,   max_tokens=80,) 
# llm_explicacion_coche = llm_res # 



MODEL_NAME_OPENAI = "gpt-4o-mini" # O el modelo OpenAI que prefieras
MODEL_NAME_OPENAI_2 = "gpt-3.5-turbo" # mas barato
TEMPERATURE_AGENT = 0.1 # Puedes ajustar la temperatura
TEMPERATURE_AGENT_2 = 0.4


llm = None
llm_potente = None
llm_res = None   # Por si falla la inicialización y no se asigna dentro del try

logging.info(f"Intentando inicializar el modelo '{MODEL_NAME_OPENAI}' de OpenAI...")

try:
    llm = init_chat_model(
        model=MODEL_NAME_OPENAI,
        model_provider="openai", # 
        temperature=TEMPERATURE_AGENT,
    )
    logging.info(f"¡Modelo LLM base '{getattr(llm, 'model_name', MODEL_NAME_OPENAI)}' inicializado exitosamente!")
    llm_res = init_chat_model(
        model=MODEL_NAME_OPENAI_2,
        model_provider="openai", # 
        max_tokens=250,
        temperature=TEMPERATURE_AGENT_2,
    )
    logging.info(f"¡Modelo LLM secundario '{getattr(llm_res, 'model_name', MODEL_NAME_OPENAI_2)}' inicializado exitosamente!")
    # Si usas llm_potente y quieres que sea el mismo o diferente:
    # Por ahora, usaremos el mismo para simplificar.
    llm_potente = llm 
    logging.info(f"¡Modelo LLM potente configurado para usar la misma instancia que el LLM base!")

except ImportError as e:
    logging.error(f"Error de importación para OpenAI: {e}. Asegúrate de tener 'langchain-openai' instalado.")
    raise
except Exception as e:
    logging.error(f"Ocurrió un error al inicializar el modelo OpenAI '{MODEL_NAME_OPENAI}': {e}")
    logging.error("Por favor, verifica que tu OPENAI_API_KEY esté configurada correctamente en tus variables de entorno.")
    raise

# --- LLMs Estructurados (manteniendo method="function_calling") ---
if llm and llm_potente and llm_res:
    llm_cp_extractor = llm.with_structured_output(
        ResultadoCP, method="function_calling"
    )
    llm_solo_perfil = llm.with_structured_output(
        ResultadoSoloPerfil, method="function_calling"
    )
    llm_pasajeros = llm.with_structured_output(
        ResultadoPasajeros, method="function_calling"
    )
    llm_solo_filtros = llm.with_structured_output(
        ResultadoSoloFiltros, method="function_calling"
    )
    llm_economia = llm_potente.with_structured_output(
        ResultadoEconomia, method="function_calling"
    )
    # LLM para explicaciones
    llm_explicacion_coche = llm_res 
    
    logging.info("INFO: LLMs estructurados para el agente configurados con OpenAI y method='function_calling'.")
else:
    logging.error("ERROR: Los LLMs base no se inicializaron correctamente. No se pueden crear los LLMs estructurados.")
    # Asignar None para evitar errores si se intentan usar
    llm_cp_extractor = None
    llm_solo_perfil = None
    llm_pasajeros = None
    llm_solo_filtros = None
    llm_economia = None
    llm_explicacion_coche = None





