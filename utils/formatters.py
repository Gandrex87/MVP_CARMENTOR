from typing import Optional, Any, Dict # Añadir tipos
from graph.perfil.state import PerfilUsuario, FiltrosInferidos, EconomiaUsuario 
#from utils.enums import Transmision, NivelAventura 
from utils.conversion import is_yes

# Define tipos más específicos para las entradas (opcional pero recomendado)
PreferenciasInput = Optional[PerfilUsuario | Dict[str, Any]]
FiltrosInput = Optional[FiltrosInferidos | Dict[str, Any]]
EconomiaInput = Optional[EconomiaUsuario | Dict[str, Any]] # <-- Descomentado para claridad

def formatear_preferencias_en_tabla(
    preferencias: PreferenciasInput, 
    # ▼▼▼ CORRECCIÓN 1: El nombre del parámetro ahora es 'economia' ▼▼▼
    economia: EconomiaInput, 
    info_pasajeros: Optional[Dict[str, Any]],
    filtros: FiltrosInput = None, 
    codigo_postal_usuario: Optional[str] = None,
    info_clima_usuario: Optional[Dict[str, Any]] = None
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
    econ_obj = EconomiaUsuario(**economia) if isinstance(economia, dict) else economia
    info_clima_dict = info_clima_usuario if info_clima_usuario is not None else {}
    pasajeros_dict = info_pasajeros if info_pasajeros is not None else {}
    
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
   
    estetica_str =  prefs_dict.get("valora_estetica")
    dise_exclusivo_val = prefs_dict.get("prefiere_diseno_exclusivo")
    dise_exclusivo_str = "No especificado"
    if dise_exclusivo_val is not None:
        dise_exclusivo_str = "Sí (Exclusivo)" if is_yes(dise_exclusivo_val) else "No (Discreto)"
    
    baja_depr_val = prefs_dict.get("prioriza_baja_depreciacion")
    baja_depr_str = "No especificado"
    if baja_depr_val is not None:
        baja_depr_str = "Sí" if is_yes(baja_depr_val) else "No"
      # Código Postal
    cp_str = codigo_postal_usuario if codigo_postal_usuario and codigo_postal_usuario.strip() else "No proporcionado"
    
    # --- 1) Cabecera de preferencias ---
    texto = "✅ He entendido lo siguiente sobre tus preferencias:         \n\n"
    texto += "| Preferencia                 | Valor                      |\n"
    texto += "|-----------------------------|----------------------------|\n" 
    texto +=f"| Código Postal               | {cp_str}                   |\n"
    # --- NUEVA SECCIÓN PARA INFO CLIMA ---
    # Solo mostrar si hay datos climáticos y el CP fue válido y encontrado
    if info_clima_dict and info_clima_dict.get("cp_valido_encontrado", False):
        climas_activos = []
        # Nombres más amigables para mostrar en la tabla
        mapa_nombres_clima = {
            "MUNICIPIO_ZBE": "Zona Bajas Emis. (ZBE)",
            "ZONA_LLUVIAS": "Zona Lluvias Frec.",
            "ZONA_NIEBLAS": "Zona Nieblas Frec.",
            "ZONA_NIEVE": "Zona Nieve Frec.",
            "ZONA_CLIMA_MONTA": "Zona Clima Montaña",
            "ZONA_GLP": "Disponib. GLP Común",
            "ZONA_GNV": "Disponib. GNV Común"
        }
        for clave_clima, nombre_amigable in mapa_nombres_clima.items():
            if info_clima_dict.get(clave_clima) is True: # Comprobar explícitamente True
                climas_activos.append(nombre_amigable)
        
        if climas_activos:
            texto += f"|Condiciones Zona   | {', '.join(climas_activos)} \n"
        else:
            texto += f"|Condiciones Zona   | Generales / No específicas  \n"
    elif cp_str != "No proporcionado": # Se dio CP pero no se encontraron datos de zona
         texto += f"|Condiciones Zona      | No disponibles para este CP \n"
    # --- FIN SECCIÓN INFO CLIMA ---
    texto += f"| Apasionado del motor      | {'Sí' if is_yes(prefs_dict.get('apasionado_motor')) else 'No'} \n" # Usar Sí/No directamente
    texto += f"| Estética                  | {estetica_str}              \n"
    texto += f"| Principal del Hogar       | {coche_principal_str}       \n" # <-- Fila añadida
    texto += f"| Uso                       | {uso_prof_str}              \n"
    if is_yes(uso_prof_val):
        tipo_uso_val_str = prefs_dict.get("tipo_uso_profesional") 
        tipo_uso_display_str = "No especificado" # Default para esta sección
        if tipo_uso_val_str and tipo_uso_val_str.strip():
            tipo_uso_display_str = tipo_uso_val_str.capitalize()
        texto+=f"|   ↳ Tipo Profesional    | {tipo_uso_display_str}      \n" # AHORA ESTÁ DENTRO DEL IF  
    texto += f"| Tipo de coche             | {'Eléctrico' if is_yes(prefs_dict.get('solo_electricos')) else 'No necesariamente eléctrico'} \n"
    texto += f"| Diseño exclusivo          | {dise_exclusivo_str}        \n"
    texto += f"| Altura                    | {'Mayor a 1.90 m' if is_yes(prefs_dict.get('altura_mayor_190')) else 'Menor a 1.90 m'} \n"
    texto += f"| Transmisión preferida     | {transm_str}                \n"
    texto += f"| Aventura                  | {aventura_str}              \n"
    texto += f"| Prioriza Baja Depreciación| {baja_depr_str}             \n"
    
    # Mostrar los nuevos ratings 0-10
    if any(prefs_dict.get(f"rating_{cat}") is not None for cat in ["fiabilidad_durabilidad", "seguridad", "comodidad", "impacto_ambiental", "costes_uso", "tecnologia_conectividad"]):
        texto += "\n📊 Importancia de Características  \n\n" # Nueva sub-sección
        texto += "| Característica         | Rating (0-10)               |\n"
        texto += "|------------------------|-----------------------------|\n"
        
        ratings_map = {
            "Fiabilidad y Durabilidad": prefs_dict.get("rating_fiabilidad_durabilidad"),
            "Seguridad": prefs_dict.get("rating_seguridad"),
            "Comodidad": prefs_dict.get("rating_comodidad"),
            "Impacto Ambiental": prefs_dict.get("rating_impacto_ambiental"),
            "Costes de Uso/Mantenimiento": prefs_dict.get("rating_costes_uso"),
            "Tecnología y Conectividad": prefs_dict.get("rating_tecnologia_conectividad"),
            
        }
        for desc, val in ratings_map.items():
            texto += f"| {desc:<32} | {val if val is not None else 'N/A'}\n"
    # --- NUEVA SECCIÓN PARA INFO PASAJEROS ---
    texto += "\n👥 Información de Pasajeros:\n\n"
    texto += "| Detalle Pasajeros          | Valor                       |\n"
    texto += "|----------------------------|-----------------------------|\n"

    suele_acomp_val = pasajeros_dict.get("suele_llevar_acompanantes") # Ahora es booleano
    suele_acomp_str = "No especificado"
    if suele_acomp_val is not None:
        suele_acomp_str = "Sí" if suele_acomp_val else "No"
    texto += f"| Suele llevar acompañantes|{suele_acomp_str}             |\n"

    if suele_acomp_val is True: # Solo mostrar detalles si SÍ suele llevar acompañantes
        frec_viaje_acomp_val = pasajeros_dict.get("frecuencia_viaje_con_acompanantes")
        frec_viaje_acomp_str = frec_viaje_acomp_val.capitalize() if frec_viaje_acomp_val else "No especificada"
        texto += f"|  ↳ Frecuencia con ellos| {frec_viaje_acomp_str}     |\n"

        # compos_pasajeros_val = pasajeros_dict.get("composicion_pasajeros_texto")
        # compos_pasajeros_str = compos_pasajeros_val if compos_pasajeros_val and compos_pasajeros_val.strip() else "No detallada"
        # texto += f"|   ↳ Composición (desc.)  | {compos_pasajeros_str} |\n" # Opcional mostrar el texto libre

        num_ninos_silla_val = pasajeros_dict.get("num_ninos_silla")
        num_ninos_silla_str = str(num_ninos_silla_val) if num_ninos_silla_val is not None else "0"
        texto += f"|   ↳ Niños en Silla    | {num_ninos_silla_str}       |\n"
        
        num_otros_pas_val = pasajeros_dict.get("num_otros_pasajeros")
        num_otros_pas_str = str(num_otros_pas_val) if num_otros_pas_val is not None else "0"
        texto += f"|   ↳ Otros Pasajeros   | {num_otros_pas_str}         |\n"

    # El campo 'frecuencia' general (nunca, ocasional, frecuente) se puede mostrar si es diferente
    # o si resume bien lo anterior. Por ahora, los detalles de arriba son más informativos.
    # frecuencia_general_val = pasajeros_dict.get("frecuencia")
    # if frecuencia_general_val:
    #     texto += f"| Frecuencia General Viaje   | {frecuencia_general_val.capitalize()} |\n"
    # --- FIN NUEVA SECCIÓN INFO PASAJEROS ---
    
    # --- 2) Filtros técnicos ---
    # (Asumiendo que tipo_mecanica y tipo_carroceria en filtros_dict ya son listas de strings (valores enum)
    # porque get_enum_names se usa antes o porque model_dump ya lo hizo)
    if filtros_dict:
        # get_enum_names ya no es necesaria aquí si model_dump(mode='json') o el RAG devuelven strings
        mech_list = filtros_dict.get("tipo_mecanica", [])
        mech = ", ".join(mech_list) if mech_list else "No definido"
        
        card_list = filtros_dict.get("tipo_carroceria", []) # Asumiendo que RAG devuelve lista de strings
        card = ", ".join(card_list) if card_list else "No definido"
        
        texto += "\n🎯 Filtros técnicos inferidos:                       \n\n"
        texto += "| Filtro técnico        | Valor                        |\n"
        texto += "|-----------------------|------------------------------|\n"
        texto +=f"| Tipo de mecánica      | {mech} |\n"
        texto +=f"| Tipo de carrocería    | {card} |\n" # Asegúrate que tipo_carroceria esté en FiltrosInferidos

    # --- AÑADIR FILAS PARA RECOMENDACIÓN MODO 1 ---
        modo_adq = filtros_dict.get("modo_adquisicion_recomendado")
        if modo_adq: # Solo mostrar si se calculó
             texto += f"| Modo Adquisición Rec. | {modo_adq}             |\n"
             if modo_adq == "Contado":
                  precio_rec = filtros_dict.get("precio_max_contado_recomendado")
                  precio_str = f"{precio_rec:,.0f} €".replace(",",".") if isinstance(precio_rec, float) else "N/A"
                  texto += f"| Precio Máx. Contado Rec.| {precio_str}    |\n"
             elif modo_adq == "Financiado":
                  cuota_calc = filtros_dict.get("cuota_max_calculada")
                  cuota_str = f"{cuota_calc:,.0f} €/mes".replace(",",".") if isinstance(cuota_calc, float) else "N/A"
                  texto += f"| Cuota Máx. Calculada    | {cuota_str}     |\n"

    # --- 3) Economía del usuario ---
   # --- 3) Economía del usuario ---
    # ▼▼▼ CORRECCIÓN 2: Usamos `texto +=` para AÑADIR, no para sobrescribir ▼▼▼
    if econ_obj:
        # Encabezado de la sección
        texto += "\n💰 **Resumen Económico**\n\n" # <-- Cambio de `=` a `+=`
        texto += "| Concepto                 | Valor                        |\n"
        texto += "|--------------------------|------------------------------|\n"

        # --- Lógica Principal (sin cambios) ---
        if econ_obj.presupuesto_definido is False:
            modo_str = "Asesor Financiero"
            texto += f"| Modo                     | {modo_str:<28} |\n"
            ing = econ_obj.ingresos
            ah = econ_obj.ahorro
            ing_str = f"{ing:,.0f} €".replace(",", ".") if isinstance(ing, (int, float)) else "No definido"
            ah_str = f"{ah:,.0f} €".replace(",", ".") if isinstance(ah, (int, float)) else "No definido"
            texto += f"| Ingresos (Anual)         | {ing_str:<28} |\n"
            texto += f"| Ahorro disponible        | {ah_str:<28} |\n"

        elif econ_obj.presupuesto_definido is True:
            modo_str = "Presupuesto Definido"
            texto += f"| Modo                     | {modo_str:<28} |\n"
            if econ_obj.pago_contado is not None:
                tipo_pago_str = "Pago Contado"
                texto += f"| Tipo de Pago             | {tipo_pago_str:<28} |\n"
                pago = econ_obj.pago_contado
                pago_str = f"{pago:,.0f} €".replace(",", ".") if isinstance(pago, (int, float)) else "No definido"
                texto += f"| Presupuesto Contado      | {pago_str:<28} |\n"
            elif econ_obj.cuota_max is not None:
                tipo_pago_str = "Cuotas Mensuales"
                texto += f"| Tipo de Pago             | {tipo_pago_str:<28} |\n"
                cuota = econ_obj.cuota_max
                entrada = econ_obj.entrada
                cuota_str = f"{cuota:,.0f} €/mes".replace(",", ".") if isinstance(cuota, (int, float)) else "No definido"
                texto += f"| Cuota máxima             | {cuota_str:<28} |\n"
                if entrada is not None and isinstance(entrada, (int, float)):
                    ent_str = f"{entrada:,.0f} €".replace(",", ".")
                    texto += f"| Entrada inicial          | {ent_str:<28} |\n"
        else:
            texto += "| Modo                     | No definido                  |\n"

    return texto.strip()
