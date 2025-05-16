from typing import Optional, Any, Dict # Añadir tipos
from graph.perfil.state import PerfilUsuario, FiltrosInferidos, EconomiaUsuario
#from utils.enums import Transmision, NivelAventura 
from utils.conversion import is_yes

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
    # Usar is_yes para las booleanas
    estetica_str = "Importante" if is_yes(prefs_dict.get("valora_estetica")) else "No prioritaria"
    
    # Usar .value para los Enums (asegurándonos de que el valor exista)
    transm_val = prefs_dict.get("transmision_preferida") # Esto será el valor (str) gracias a model_dump(mode='json')
    transm_str = transm_val.capitalize() if transm_val else "No definido"

    aventura_val = prefs_dict.get("aventura") # Esto será el valor (str)
    aventura_str = aventura_val.capitalize() if aventura_val else "No definido"
    
    coche_principal_val = prefs_dict.get("coche_principal_hogar")
    if coche_principal_val is None:
        coche_principal_str = "No especificado"
    else:
        coche_principal_str = "Sí" if is_yes(coche_principal_val) else "No"
    
    uso_prof_val = prefs_dict.get("uso_profesional")
    uso_prof_str = "Profesional" if is_yes(uso_prof_val) else "Particular"
    if is_yes(uso_prof_val):
        tipo_uso_val_str = prefs_dict.get("tipo_uso_profesional") 
        if tipo_uso_val_str and tipo_uso_val_str.strip(): # Asegurar que no sea cadena vacía
            tipo_uso_display_str = tipo_uso_val_str.capitalize()
        else:
            tipo_uso_display_str = "No especificado" # <-- VALOR POR DEFECTO
   
    
    dise_exclusivo_val = prefs_dict.get("prefiere_diseno_exclusivo")
    dise_exclusivo_str = "No especificado"
    if dise_exclusivo_val is not None:
        dise_exclusivo_str = "Sí (Exclusivo)" if is_yes(dise_exclusivo_val) else "No (Discreto)"
    
    baja_depr_val = prefs_dict.get("prioriza_baja_depreciacion")
    baja_depr_str = "No especificado"
    if baja_depr_val is not None:
        baja_depr_str = "Sí" if is_yes(baja_depr_val) else "No"
    
    # --- 1) Cabecera de preferencias ---
    texto = "✅ He entendido lo siguiente sobre tus preferencias:\n\n"
    texto += "| Preferencia              | Valor                      |\n"
    texto += "|--------------------------|----------------------------|\n"
    texto += f"| Apasionado del motor    | {'Sí' if is_yes(prefs_dict.get('apasionado_motor')) else 'No'} |\n" # Usar Sí/No directamente
    texto += f"| Estética                | {estetica_str} |\n"
    texto += f"| Principal del Hogar     | {coche_principal_str} |\n" # <-- Fila añadida
    texto += f"| Uso                     | {uso_prof_str} |\n"
    if is_yes(uso_prof_val):
        tipo_uso_val_str = prefs_dict.get("tipo_uso_profesional") 
        tipo_uso_display_str = "No especificado" # Default para esta sección
        if tipo_uso_val_str and tipo_uso_val_str.strip():
            tipo_uso_display_str = tipo_uso_val_str.capitalize()
        texto+=f"|   ↳ Tipo Profesional  | {tipo_uso_display_str} \n" # AHORA ESTÁ DENTRO DEL IF  
    texto += f"| Tipo de coche           | {'Eléctrico' if is_yes(prefs_dict.get('solo_electricos')) else 'No necesariamente eléctrico'} |\n"
    texto += f"| Diseño exclusivo        | {dise_exclusivo_str} |\n"
    texto += f"| Altura                  | {'Mayor a 1.90 m' if is_yes(prefs_dict.get('altura_mayor_190')) else 'Menor a 1.90 m'} |\n"
    texto += f"| Peso                    | {'Mayor a 100 kg' if is_yes(prefs_dict.get('peso_mayor_100')) else 'Menor a 100 kg'}   |\n"
    texto += f"| Transmisión preferida   | {transm_str}      |\n"
    texto += f"| Aventura                | {aventura_str}    |\n"
    texto += f"| Prioriza Baja Depreciación| {baja_depr_str} |\n"
    
    # Mostrar los nuevos ratings 0-10
    if any(prefs_dict.get(f"rating_{cat}") is not None for cat in ["fiabilidad_durabilidad", "seguridad", "comodidad", "impacto_ambiental", "costes_uso", "tecnologia_conectividad"]):
        texto += "\n📊 Importancia de Características (0-10):\n\n" # Nueva sub-sección
        texto += "| Característica                   | Rating (0-10) |\n"
        texto += "|----------------------------------|---------------|\n"
        
        ratings_map = {
            "Fiabilidad y Durabilidad": prefs_dict.get("rating_fiabilidad_durabilidad"),
            "Seguridad": prefs_dict.get("rating_seguridad"),
            "Comodidad": prefs_dict.get("rating_comodidad"),
            "Impacto Ambiental": prefs_dict.get("rating_impacto_ambiental"),
            #"Costes de Uso/Mantenimiento": prefs_dict.get("rating_costes_uso"),
            "Tecnología y Conectividad": prefs_dict.get("rating_tecnologia_conectividad"),
            
        }
        for desc, val in ratings_map.items():
            texto += f"| {desc:<32} | {val if val is not None else 'N/A'} |\n"

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

    # --- AÑADIR FILAS PARA RECOMENDACIÓN MODO 1 ---
        modo_adq = filtros_dict.get("modo_adquisicion_recomendado")
        if modo_adq: # Solo mostrar si se calculó
             texto += f"| Modo Adquisición Rec. | {modo_adq} |\n"
             if modo_adq == "Contado":
                  precio_rec = filtros_dict.get("precio_max_contado_recomendado")
                  precio_str = f"{precio_rec:,.0f} €".replace(",",".") if isinstance(precio_rec, float) else "N/A"
                  texto += f"| Precio Máx. Contado Rec.| {precio_str} |\n"
             elif modo_adq == "Financiado":
                  cuota_calc = filtros_dict.get("cuota_max_calculada")
                  cuota_str = f"{cuota_calc:,.0f} €/mes".replace(",",".") if isinstance(cuota_calc, float) else "N/A"
                  texto += f"| Cuota Máx. Calculada    | {cuota_str} |\n"

    # --- 3) Economía del usuario ---
    if econ_dict: # Verifica si hay datos económicos
        texto += "\n💰 Economía del usuario:\n\n"
        texto += "| Concepto                | Valor               |\n" # Ajustar ancho si es necesario
        texto += "|-------------------------|---------------------|\n"
        
        modo = econ_dict.get("modo") 
        modo_str = "Asesor Financiero" if modo == 1 else "Presupuesto Definido" if modo == 2 else "No definido"
        texto += f"| Modo                    | {modo_str} |\n"

        # --- NUEVA LÍNEA AÑADIDA ---
        anos = econ_dict.get("anos_posesion")
        # Formatear si es un número, si no, indicar que no está definido
        anos_str = f"{anos} años" if isinstance(anos, int) else "No especificado" 
        texto += f"| Años Posesión Estimados | {anos_str} |\n" # <-- Fila añadida
        # --- FIN LÍNEA AÑADIDA ---

        # Resto de la lógica para Modo 1 o Modo 2 (como la tenías corregida)
        if modo == 1: 
            ing = econ_dict.get("ingresos")
            ah  = econ_dict.get("ahorro")
            ing_str = f"{ing:,.0f} €".replace(",",".") if isinstance(ing, (int, float)) else "No definido"
            ah_str  = f"{ah:,.0f} €".replace(",",".")  if isinstance(ah, (int, float)) else "No definido"
            # Podrías ajustar el label si ingresos son mensuales vs anuales
            texto += f"| Ingresos (Aprox Anual)| {ing_str} |\n" 
            texto += f"| Ahorro disponible       | {ah_str} |\n"
        elif modo == 2: 
            sub = econ_dict.get("submodo") 
            sub_str = "Pago Contado" if sub == 1 else "Cuotas Mensuales" if sub == 2 else "No definido"
            texto += f"| Tipo de Pago            | {sub_str} |\n"

            if sub == 1: 
                pago = econ_dict.get("pago_contado")
                pago_str = f"{pago:,.0f} €".replace(",",".") if isinstance(pago, (int, float)) else "No definido"
                texto += f"| Presupuesto Contado     | {pago_str} |\n"
            elif sub == 2: 
                cuota = econ_dict.get("cuota_max")
                entrada = econ_dict.get("entrada") 
                
                cuota_str = f"{cuota:,.0f} €/mes".replace(",",".") if isinstance(cuota, (int, float)) else "No definido"
                texto += f"| Cuota máxima            | {cuota_str} |\n"
                
                if entrada is not None and isinstance(entrada, (int, float)):
                    ent_str = f"{entrada:,.0f} €".replace(",",".")
                    texto += f"| Entrada inicial         | {ent_str} |\n"

    return texto.strip()