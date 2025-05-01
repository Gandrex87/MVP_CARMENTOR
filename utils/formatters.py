from utils.conversion import normalizar_texto
from utils.conversion import get_enum_names 
from typing import Optional, Any, Dict # Añadir tipos
from graph.perfil.state import PerfilUsuario, FiltrosInferidos, EconomiaUsuario
from utils.enums import Transmision, NivelAventura 
from utils.conversion import is_yes, get_enum_names # Añadir is_yes

# Define tipos más específicos para las entradas (opcional pero recomendado)
PreferenciasInput = Optional[PerfilUsuario | Dict[str, Any]]
FiltrosInput = Optional[FiltrosInferidos | Dict[str, Any]]
EconomiaInput = Optional[EconomiaUsuario | Dict[str, Any]]

def formatear_preferencias_en_tabla(
    preferencias: PreferenciasInput, 
    filtros: FiltrosInput = None, 
    economia: EconomiaInput = None
) -> str:
    """
    Devuelve una tabla Markdown con:
     - Preferencias del usuario
     - Filtros técnicos inferidos
     - Datos de economía (si se proporcionan)
    """

    # --- Convertir a dict para acceso uniforme (si son Pydantic models) ---
    prefs_dict = preferencias.model_dump(mode='json') if hasattr(preferencias, "model_dump") else preferencias or {}
    filtros_dict = filtros.model_dump(mode='json') if hasattr(filtros, "model_dump") else filtros or {}
    econ_dict = economia.model_dump(mode='json') if hasattr(economia, "model_dump") else economia or {}

    # --- Preparar algunos valores ---
    # Usar is_yes para las booleanas
    estetica_str = "Importante" if is_yes(prefs_dict.get("valora_estetica")) else "No prioritaria"
    
    # Usar .value para los Enums (asegurándonos de que el valor exista)
    transm_val = prefs_dict.get("transmision_preferida") # Esto será el valor (str) gracias a model_dump(mode='json')
    transm_str = transm_val.capitalize() if transm_val else "No definido"

    aventura_val = prefs_dict.get("aventura") # Esto será el valor (str)
    aventura_str = aventura_val.capitalize() if aventura_val else "No definido"

    # --- 1) Cabecera de preferencias ---
    texto = "✅ He entendido lo siguiente sobre tus preferencias:\n\n"
    texto += "| Preferencia             | Valor                      |\n"
    texto += "|-------------------------|----------------------------|\n"
    texto += f"| Tipo de coche           | {'Eléctrico' if is_yes(prefs_dict.get('solo_electricos')) else 'No necesariamente eléctrico'} |\n"
    texto += f"| Uso                     | {'Uso profesional' if is_yes(prefs_dict.get('uso_profesional')) else 'Particular'} |\n"
    texto += f"| Altura                  | {'Mayor a 1.90 m' if is_yes(prefs_dict.get('altura_mayor_190')) else 'Menor a 1.90 m'} |\n"
    texto += f"| Peso                    | {'Mayor a 100 kg' if is_yes(prefs_dict.get('peso_mayor_100')) else 'Menor a 100 kg'} |\n"
    texto += f"| Estética                | {estetica_str} |\n"
    texto += f"| Transmisión preferida   | {transm_str} |\n"
    texto += f"| Apasionado del motor    | {'Sí' if is_yes(prefs_dict.get('apasionado_motor')) else 'No'} |\n" # Usar Sí/No directamente
    texto += f"| Aventura                | {aventura_str} |\n"

    # --- 2) Filtros técnicos ---
    # (Asumiendo que tipo_mecanica y tipo_carroceria en filtros_dict ya son listas de strings (valores enum)
    # porque get_enum_names se usa antes o porque model_dump ya lo hizo)
    if filtros_dict:
        # get_enum_names ya no es necesaria aquí si model_dump(mode='json') o el RAG devuelven strings
        mech_list = filtros_dict.get("tipo_mecanica", [])
        mech = ", ".join(mech_list) if mech_list else "No definido"
        
        card_list = filtros_dict.get("tipo_carroceria", []) # Asumiendo que RAG devuelve lista de strings
        card = ", ".join(card_list) if card_list else "No definido"
        
        texto += "\n🎯 Filtros técnicos inferidos:\n\n"
        texto += "| Filtro técnico        | Valor                            |\n"
        texto += "|-----------------------|----------------------------------|\n"
        texto += f"| Tipo de mecánica     | {mech} |\n"
        texto += f"| Tipo de carrocería   | {card} |\n" # Asegúrate que tipo_carroceria esté en FiltrosInferidos
        texto += f"| Estética mínima      | {filtros_dict.get('estetica_min','No definido')} |\n"
        texto += f"| Premium mínima       | {filtros_dict.get('premium_min','No definido')} |\n"
        texto += f"| Singularidad mínima  | {filtros_dict.get('singular_min','No definido')} |\n"

    # --- 3) Economía del usuario ---
    if econ_dict:
        texto += "\n💰 Economía del usuario:\n\n"
        texto += "| Concepto           | Valor               |\n"
        texto += "|--------------------|---------------------|\n"
        
        modo = econ_dict.get("modo") # Obtener el modo (debería ser 1 o 2)
        modo_str = "Asesor Financiero" if modo == 1 else "Presupuesto Definido" if modo == 2 else "No definido"
        texto += f"| Modo               | {modo_str} |\n"

        # --- CORREGIR LÓGICA AQUÍ ---
        if modo == 1: # Comparar con entero 1
            ing = econ_dict.get("ingresos")
            ah  = econ_dict.get("ahorro")
            # Formatear números o mostrar "No definido"
            ing_str = f"{ing:,.0f} €".replace(",",".") if isinstance(ing, (int, float)) else "No definido"
            ah_str  = f"{ah:,.0f} €".replace(",",".")  if isinstance(ah, (int, float)) else "No definido"
            texto += f"| Ingresos anuales   | {ing_str} |\n" # Ajusta texto si son mensuales
            texto += f"| Ahorro disponible  | {ah_str} |\n"
        elif modo == 2: # Comparar con entero 2
            sub = econ_dict.get("submodo") # Obtener submodo (debería ser 1 o 2)
            sub_str = "Pago Contado" if sub == 1 else "Cuotas Mensuales" if sub == 2 else "No definido"
            texto += f"| Tipo de Pago       | {sub_str} |\n"

            if sub == 1: # Comparar con entero 1
                pago = econ_dict.get("pago_contado")
                pago_str = f"{pago:,.0f} €".replace(",",".") if isinstance(pago, (int, float)) else "No definido"
                texto += f"| Presupuesto Contado| {pago_str} |\n"
            elif sub == 2: # Comparar con entero 2
                cuota = econ_dict.get("cuota_max")
                entrada = econ_dict.get("entrada") # Entrada es opcional
                
                cuota_str = f"{cuota:,.0f} €/mes".replace(",",".") if isinstance(cuota, (int, float)) else "No definido"
                texto += f"| Cuota máxima       | {cuota_str} |\n"
                
                if entrada is not None and isinstance(entrada, (int, float)):
                    ent_str = f"{entrada:,.0f} €".replace(",",".")
                    texto += f"| Entrada inicial    | {ent_str} |\n"

    # Puedes cambiar este mensaje final si lo deseas
    # texto += "\n¿Hay algo que quieras ajustar o añadir?" 
    texto += "\n\nEspero que este resumen te sea útil."

    return texto.strip() # Quitar espacios extra al final