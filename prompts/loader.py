from langchain_core.messages import SystemMessage
from langchain_core.runnables import Runnable
from pathlib import Path

def load_prompt(filename: str) -> SystemMessage:
    path = Path(__file__).resolve().parent.parent / "prompts" / filename
    with open(path, "r", encoding="utf-8") as f:
        return SystemMessage(content=f.read())

# Ejemplo de uso:
# perfil_structured_sys_msg = load_prompt("perfil_structured_prompt.txt")


# # Cargar un prompt desde un archivo   
# def cargar_prompt(nombre_archivo: str) -> str:
#     prompt_path = Path(__file__).parent / nombre_archivo
#     if not prompt_path.exists():
#         raise FileNotFoundError(f"❌ El prompt '{nombre_archivo}' no fue encontrado en {prompt_path}")
#     with open(prompt_path, "r", encoding="utf-8") as f:
#         return f.read()

# prompt_base = cargar_prompt("validacion_dinamica.txt")



#==================#==================#==================new==================#==================#
# Cargar un prompt desde un archivo   
def cargar_prompt(nombre_archivo: str) -> str:
    prompt_path = Path(__file__).parent / nombre_archivo
    if not prompt_path.exists():
        raise FileNotFoundError(f"❌ El prompt '{nombre_archivo}' no fue encontrado en {prompt_path}")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()
    
system_prompt_filtros_template = cargar_prompt("system_prompt_filtros_template.txt")

system_prompt_perfil= cargar_prompt("system_prompt_perfil.txt")

prompt_economia_structured_sys_msg = cargar_prompt("prompt_economia_structured.txt")

system_prompt_pasajeros = cargar_prompt("system_prompt_pasajeros.txt")

system_prompt_cp = cargar_prompt("system_prompt_cp.txt")

system_prompt_explicacion_coche = cargar_prompt("system_prompt_explicacion_coche.txt")

system_prompt_explicacion_coche_mejorado = cargar_prompt("system_prompt_explicacion_coche_mejorado.txt")

