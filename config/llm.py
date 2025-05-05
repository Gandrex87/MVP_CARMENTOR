# instanciación del modelo, init_chat_model, y configuración de structured_llm.
from langchain.chat_models import init_chat_model
from graph.perfil.state import ResultadoSoloPerfil, ResultadoSoloFiltros, ResultadoEconomia # Ajusta la ruta de importación
from dotenv import load_dotenv


load_dotenv()

# --- LLMs Base ---
llm = init_chat_model("openai:gpt-4o-mini", temperature=0.2) 

# LLM para generar preguntas de seguimiento más naturales (si es necesario)
llm_validacion = init_chat_model("openai:gpt-4o-mini", temperature=0.4) 

# --- LLMs con Salida Estructurada por Etapa ---

# 1. LLM para la Etapa de Perfil del Usuario
# Usará un prompt específico para perfil y devolverá solo PerfilUsuario + mensaje_validacion
llm_solo_perfil = llm.with_structured_output(ResultadoSoloPerfil)

  
# 2. LLM para la Etapa de Inferencia de Filtros
#    Usará un prompt específico para filtros (recibiendo el perfil como contexto)
#    y devolverá solo FiltrosInferidos + mensaje_validacion
llm_solo_filtros = llm.with_structured_output(ResultadoSoloFiltros)

# 3. LLM para la Etapa de Economía (Sin cambios)
# --- USA UN MODELO MÁS POTENTE PARA ECONOMÍA ---
#print("INFO: Inicializando llm_economia_potente (gpt-4o)...")
#llm_potente = init_chat_model("openai:gpt-4o", temperature=0.2) # O el ID correcto para gpt-4o
llm_potente = init_chat_model("openai:gpt-4o-mini", temperature=0.1) # O el ID correcto para gpt-4o
llm_economia = llm_potente.with_structured_output(ResultadoEconomia)

# Usará un prompt específico para economía y devolverá EconomiaUsuario + mensaje_validacion
#llm_economia = llm.with_structured_output(ResultadoEconomia)





