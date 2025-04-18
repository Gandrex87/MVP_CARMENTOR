# instanciación del modelo, init_chat_model, y configuración de structured_llm.
from langchain.chat_models import init_chat_model
from graph.perfil.state import ResultadoPerfil
from dotenv import load_dotenv
from prompts.loader import prompt_base
from utils.enums import TipoCarroceria, TipoMecanica
from pydantic import BaseModel, Field
from utils.conversion import get_enum_names  # si no estaba antes en utils, usa el correcto

load_dotenv()

# LLM base
llm = init_chat_model("openai:gpt-4o-mini", temperature=0.2)
# LLM con output estructurado /  agente principal, que infiere preferencias y filtros usando el esquema ResultadoPerfil.
structured_llm = llm.with_structured_output(ResultadoPerfil)


# LLM usado con prompt especifico para realiar preguntas de validación. #temp04 va bien
llm_validacion = init_chat_model("openai:gpt-4o-mini" , temperature=0.3 , verbose=True)


# 🧠 Prompt dinámico para validación natural
# Convertir Enums a strings para pasar al prompt
#carrocerias_str = ", ".join([e.value for e in TipoCarroceria])
mecanicas_str = ", ".join([e.value for e in TipoMecanica])

# Rellenar placeholders del prompt
prompt_validacion = prompt_base.format(
    #tipo_carroceria=carrocerias_str,
    tipo_mecanica=mecanicas_str
)






