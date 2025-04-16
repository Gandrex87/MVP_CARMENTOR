from utils.conversion import normalizar_texto
from utils.conversion import get_enum_names 
import unicodedata
import re



def formatear_preferencias_en_tabla(preferencias, filtros=None) -> str:
    if hasattr(preferencias, "model_dump"):
        preferencias = preferencias.model_dump()
    if filtros and hasattr(filtros, "model_dump"):
        filtros = filtros.model_dump()

    texto = "✅ He entendido lo siguiente sobre tus preferencias:\n\n"
    texto +=  "| Preferencia         | Valor                      |\n"
    texto +=  "|---------------------|----------------------------|\n"
    texto += f"| Tipo de coche       | {'Eléctrico' if normalizar_texto(preferencias.get('solo_electricos', '')) == 'si' else 'No necesariamente eléctrico'} |\n"
    texto += f"| Uso                 | {'Uso profesional' if normalizar_texto(preferencias.get('uso_profesional', '')) == 'si' else 'Particular'}           |\n"
    texto += f"| Altura              | {'Mayor a 1.90 m' if normalizar_texto(preferencias.get('altura_mayor_190', '')) == 'si' else 'Menor a 1.90 m'}       |\n"
    texto += f"| Peso                | {'Mayor a 100 kg' if normalizar_texto(preferencias.get('peso_mayor_100', '')) == 'si' else 'Menor a 100 kg'}         |\n"
    texto += f"| Estética            | {'Importante' if normalizar_texto(preferencias.get('valora_estetica', '')) == 'si' else 'No prioritaria'}            |\n"
    texto += f"| Cambio              | {'Automático' if normalizar_texto(preferencias.get('cambio_automatico', '')) == 'si' else 'Manual'}                  |\n"
    texto += f"| Apasionado del motor| {'Sí' if normalizar_texto(preferencias.get('apasionado_motor', '')) == 'si' else 'No'}                               |\n"

    if filtros: 
        tipo_mecanica = ", ".join(get_enum_names(filtros.get("tipo_mecanica", [])))
        tipo_carroceria = ", ".join(get_enum_names(filtros.get("tipo_carroceria", [])))
        estetica_min = filtros.get("estetica_min")
        premium_min = filtros.get("premium_min")
        singular_min = filtros.get("singular_min")

        texto += "\n\n🎯 Filtros técnicos inferidos:\n\n"
        texto += "| Filtro técnico       | Valor                           |\n"
        texto += "|----------------------|----------------------------------|\n"
        texto += f"| Tipo de mecánica     | {tipo_mecanica or 'No definido'}\n"
        texto += f"| Tipo de carrocería   | {tipo_carroceria or 'No definido'}\n"
        texto += f"| Estética mínima      | {estetica_min if estetica_min else 'No definido'}\n"
        texto += f"| Premium mínima       | {premium_min if premium_min else 'No definido'}\n"
        texto += f"| Singularidad mínima  | {singular_min if singular_min else 'No definido'}\n"

    texto += "\n¿Hay algo que quieras ajustar o añadir?"
    return texto