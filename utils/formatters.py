from utils.conversion import normalizar_texto
from utils.conversion import get_enum_names 
from graph.perfil.state import NivelAventura
import unicodedata
import re



def formatear_preferencias_en_tabla(preferencias, filtros=None) -> str:
    if hasattr(preferencias, "model_dump"):
        preferencias = preferencias.model_dump()
    if filtros and hasattr(filtros, "model_dump"):
        filtros = filtros.model_dump()
    aventura = preferencias.get("aventura")
    estetica_pref = preferencias.get("valora_estetica")
    if estetica_pref is None:
        estetica_str = "No definido"
    else:
        estetica_str = "Importante" if normalizar_texto(estetica_pref) == "si" else "No prioritaria"
     # Transmisión preferida ahora puede ser AUTOMÁTICO, MANUAL o AMBOS
    transm = preferencias.get("transmision_preferida")
    if transm:
        # Aseguramos capitalizar bien, incluso si viene como enum o str
        transm_str = str(transm).capitalize()
    else:
        transm_str = "No definido"
    
    # … resto de la tabla …

        
    texto = "✅ He entendido lo siguiente sobre tus preferencias:     \n\n"
    texto +=  "| Preferencia             | Valor                      |\n"
    texto +=  "|-------------------------|----------------------------|\n"
    texto += f"| Tipo de coche           | {'Eléctrico' if normalizar_texto(preferencias.get('solo_electricos', '')) == 'si' else 'No necesariamente eléctrico'} \n"
    texto += f"| Uso                     | {'Uso profesional' if normalizar_texto(preferencias.get('uso_profesional', '')) == 'si' else 'Particular'}           \n"
    texto += f"| Altura                  | {'Mayor a 1.90 m' if normalizar_texto(preferencias.get('altura_mayor_190', '')) == 'si' else 'Menor a 1.90 m'}       \n"
    texto += f"| Peso                    | {'Mayor a 100 kg' if normalizar_texto(preferencias.get('peso_mayor_100', '')) == 'si' else 'Menor a 100 kg'}         \n"   
    texto += f"| Estética                | {estetica_str}                                                                                                       \n"   
    texto += f"| Transmisión preferida   | {transm_str}                                                                                                        \n"
    texto += f"| Apasionado del motor    | {'Sí' if normalizar_texto(preferencias.get('apasionado_motor', '')) == 'si' else 'No'}                               \n"
    texto += f"| Aventura con tu vehiculo| {aventura.value.capitalize() if hasattr(aventura, 'value') else (aventura or 'No definido').capitalize()}             \n"
    
    if filtros: 
        tipo_mecanica = ", ".join(get_enum_names(filtros.get("tipo_mecanica", [])))
        tipo_carroceria = ", ".join(get_enum_names(filtros.get("tipo_carroceria", [])))
        estetica_min = filtros.get("estetica_min")
        premium_min = filtros.get("premium_min")
        singular_min = filtros.get("singular_min")
        texto += "\n\n🎯 Filtros técnicos inferidos:\n\n"
        texto += "| Filtro técnico        | Valor                            |\n"
        texto += "|-----------------------|----------------------------------|\n"
        texto += f"| Tipo de mecánica     | {tipo_mecanica or 'No definido'}\n"
        texto += f"| Tipo de carrocería   | {tipo_carroceria or 'No definido'}\n"
        texto += f"| Estética mínima      | {estetica_min if estetica_min else 'No definido'}\n"
        texto += f"| Premium mínima       | {premium_min if premium_min else 'No definido'}\n"
        texto += f"| Singularidad mínima  | {singular_min if singular_min else 'No definido'}\n"

    texto += "\n¿Hay algo que quieras ajustar o añadir?"
    return texto