
def finalizar_y_presentar_node(state: EstadoAnalisisPerfil) -> dict:
    """
    Realiza los cálculos finales (Modo 1 econ, RAG carrocerías, pesos, flags de penalización) 
    y formatea la tabla resumen final una vez toda la información está completa.
    """
    print("--- Ejecutando Nodo: finalizar_y_presentar_node ---")
    historial = state.get("messages", [])
    preferencias_obj = state.get("preferencias_usuario") # Este es el objeto PerfilUsuario
    filtros_obj = state.get("filtros_inferidos")       # Objeto FiltrosInferidos
    economia_obj = state.get("economia")           # Objeto EconomiaUsuario
    info_pasajeros_obj = state.get("info_pasajeros") # Objeto InfoPasajeros
    priorizar_ancho_flag = state.get("priorizar_ancho", False)
    codigo_postal_usuario_val = state.get("codigo_postal_usuario")
    pesos_calculados = None # Inicializar
    tabla_final_md = "Error al generar el resumen." # Default
    info_clima_obj = state.get("info_clima_usuario") # Es un objeto InfoClimaUsuario o None

    # Verificar pre-condiciones
    if not preferencias_obj or not filtros_obj or not economia_obj: # info_pasajeros es opcional para este check
         print("ERROR (Finalizar) ► Faltan datos esenciales (perfil/filtros/economia) para finalizar.")
         ai_msg = AIMessage(content="Lo siento, parece que falta información para generar el resumen final.")
         # Devolver un estado mínimo para no romper el grafo
         return {
             "messages": historial + [ai_msg],
             "preferencias_usuario": preferencias_obj, 
             "info_pasajeros": info_pasajeros_obj,
             "filtros_inferidos": filtros_obj, 
             "economia": economia_obj, "pesos": None,
             "tabla_resumen_criterios": None, 
             "coches_recomendados": None,
            #  "penalizar_puertas_bajas": state.get("penalizar_puertas_bajas"),
            # "priorizar_ancho": priorizar_ancho_flag,
            # "flag_penalizar_low_cost_comodidad": False, # Default
            #"flag_penalizar_deportividad_comodidad": False ,# Default
            #"flag_penalizar_antiguo_por_tecnologia": False,
            #"aplicar_logica_distintivo_ambiental": False, # <-- Default para el nuevo flag
             "codigo_postal_usuario": codigo_postal_usuario_val,
             "info_clima_usuario": info_clima_obj,
             "es_municipio_zbe": False, # Default para el nuevo flag
             "es_zona_nieblas_estado": False, #flags clima para el estado (aunque no se usen directamente en BQ, es bueno tenerlos)
             "es_zona_nieve_estado": False,
             "es_zona_clima_monta_estado": False,
         }
    # Trabajar con una copia de filtros para las modificaciones
    filtros_actualizados = filtros_obj.model_copy(deep=True)   
         
 # --- LÓGICA MODO 1 ECON (como la tenías) ---
    print("DEBUG (Finalizar) ► Verificando si aplica lógica Modo 1...")
    if economia_obj.modo == 1:
        # ... (tu lógica existente para calcular modo_adq_rec, etc. y actualizar filtros_actualizados) ...
        # Ejemplo resumido:
        print("DEBUG (Finalizar) ► Modo 1 detectado. Calculando recomendación...")
        try:
            ingresos = economia_obj.ingresos; ahorro = economia_obj.ahorro; anos_posesion = economia_obj.anos_posesion
            if ingresos is not None and ahorro is not None and anos_posesion is not None:
                 t = min(anos_posesion, 8); ahorro_utilizable = ahorro * 0.75
                 potencial_ahorro_plazo = ingresos * 0.1 * t
                 if potencial_ahorro_plazo <= ahorro_utilizable:
                     modo_adq_rec, precio_max_rec, cuota_max_calc = "Contado", potencial_ahorro_plazo, None
                 else:
                     modo_adq_rec, precio_max_rec, cuota_max_calc = "Financiado", None, (ingresos * 0.1) / 12
                 update_dict = {"modo_adquisicion_recomendado": modo_adq_rec, "precio_max_contado_recomendado": precio_max_rec, "cuota_max_calculada": cuota_max_calc}
                 filtros_actualizados = filtros_actualizados.model_copy(update=update_dict) 
                 print(f"DEBUG (Finalizar) ► Filtros actualizados con recomendación Modo 1: {filtros_actualizados}")
        except Exception as e_calc:
            print(f"ERROR (Finalizar) ► Fallo durante cálculo de recomendación Modo 1: {e_calc}")
    else:
         print("DEBUG (Finalizar) ► Modo no es 1, omitiendo cálculo de recomendación.")
    # --- FIN LÓGICA MODO 1 ---
    
    # Convertir a dicts ANTES de pasarlos a funciones que los esperan así
    prefs_dict_para_funciones = preferencias_obj.model_dump(mode='json', exclude_none=False)
    filtros_dict_para_rag = filtros_actualizados.model_dump(mode='json', exclude_none=False)
    info_pasajeros_dict_para_rag = info_pasajeros_obj.model_dump(mode='json') if info_pasajeros_obj else None
    info_clima_dict_para_rag = info_clima_obj.model_dump(mode='json') if info_clima_obj else None
    # 1. Llamada RAG
    if not filtros_actualizados.tipo_carroceria: 
        print("DEBUG (Finalizar) ► Llamando a RAG...")
        try:
            tipos_carroceria_rec = get_recommended_carrocerias(
                prefs_dict_para_funciones, 
                filtros_dict_para_rag, 
                info_pasajeros_dict_para_rag,
                info_clima_dict_para_rag, # <-- NUEVO: Pasar info_clima a RAG 
                k=4 #antes 4 HACER PRUEBAS
            ) 
            print(f"DEBUG (Finalizar) ► RAG recomendó: {tipos_carroceria_rec}")
            filtros_actualizados.tipo_carroceria = tipos_carroceria_rec 
        except Exception as e_rag:
            print(f"ERROR (Finalizar) ► Fallo en RAG: {e_rag}")
            filtros_actualizados.tipo_carroceria = ["Error RAG"] 
    
    # --- LÓGICA PARA FLAGS DE PENALIZACIÓN POR COMODIDAD (USANDO OBJETO Pydantic) ---
    flag_penalizar_low_cost_comodidad = False
    flag_penalizar_deportividad_comodidad = False

    # Usamos el objeto preferencias_obj directamente aquí
    if preferencias_obj and preferencias_obj.rating_comodidad is not None:
        if preferencias_obj.rating_comodidad >= UMBRAL_COMODIDAD_PARA_PENALIZAR_FLAGS:
            flag_penalizar_low_cost_comodidad = True
            flag_penalizar_deportividad_comodidad = True
            print(f"DEBUG (Finalizar) ► Rating Comodidad ({preferencias_obj.rating_comodidad}) >= {UMBRAL_COMODIDAD_PARA_PENALIZAR_FLAGS}. Activando flags de penalización.")
    
    # --- NUEVA LÓGICA PARA FLAG DE PENALIZACIÓN POR ANTIGÜEDAD Y TECNOLOGÍA ---
    
    flag_penalizar_antiguo_tec = False 
    if preferencias_obj and preferencias_obj.rating_tecnologia_conectividad is not None:
        if preferencias_obj.rating_tecnologia_conectividad >= UMBRAL_TECNOLOGIA_PARA_PENALIZAR_ANTIGUEDAD_FLAG:
            flag_penalizar_antiguo_tec = True
            print(f"DEBUG (Finalizar) ► Rating Tecnología ({preferencias_obj.rating_tecnologia_conectividad}) >= {UMBRAL_TECNOLOGIA_PARA_PENALIZAR_ANTIGUEDAD_FLAG}. Activando flag de penalización por antigüedad.")
            
    # --- NUEVA LÓGICA PARA FLAG DE DISTINTIVO AMBIENTAL ---
    flag_aplicar_logica_distintivo = False # Default
    
    if preferencias_obj and preferencias_obj.rating_impacto_ambiental is not None:
        if preferencias_obj.rating_impacto_ambiental >= UMBRAL_IMPACTO_AMBIENTAL_PARA_LOGICA_DISTINTIVO_FLAG:
            flag_aplicar_logica_distintivo = True
            print(f"DEBUG (Finalizar) ► Rating Impacto Ambiental ({preferencias_obj.rating_impacto_ambiental}) >= {UMBRAL_IMPACTO_AMBIENTAL_PARA_LOGICA_DISTINTIVO_FLAG}. Activando lógica de distintivo ambiental.")
   
    # --- PREPARAR FLAGS CLIMÁTICOS PARA compute_raw_weights ---
    es_nieblas = False
    es_nieve = False
    es_monta = False
    if info_clima_obj and info_clima_obj.cp_valido_encontrado: # Solo si tenemos datos válidos de clima
        es_nieblas = info_clima_obj.ZONA_NIEBLAS or False
        es_nieve = info_clima_obj.ZONA_NIEVE or False
        es_monta = info_clima_obj.ZONA_CLIMA_MONTA or False
    
    # --- NUEVA LÓGICA PARA FLAG ZBE ---
    flag_es_municipio_zbe = False # Default
    if info_clima_obj and info_clima_obj.cp_valido_encontrado and info_clima_obj.MUNICIPIO_ZBE is True:
        flag_es_municipio_zbe = True
        print(f"DEBUG (Finalizar) ► CP en MUNICIPIO_ZBE. Activando flag es_municipio_zbe.")
    # --- FIN NUEVA LÓGICA FLAG ZBE ---
    
    # 2. Cálculo de Pesos
    print("DEBUG (Finalizar) ► Calculando pesos...")
    try:
        estetica_min_val = filtros_actualizados.estetica_min
        premium_min_val = filtros_actualizados.premium_min
        singular_min_val = filtros_actualizados.singular_min

        raw_weights = compute_raw_weights(
            preferencias=prefs_dict_para_funciones, # compute_raw_weights espera un dict
            estetica_min_val=estetica_min_val,
            premium_min_val=premium_min_val,
            singular_min_val=singular_min_val,
            priorizar_ancho=priorizar_ancho_flag,
            es_zona_nieblas=es_nieblas,
            es_zona_nieve=es_nieve,
            es_zona_clima_monta=es_monta
        )
        pesos_calculados = normalize_weights(raw_weights)
        print(f"DEBUG (Finalizar) ► Pesos calculados: {pesos_calculados}") 
    except Exception as e_weights:
        print(f"ERROR (Finalizar) ► Fallo calculando pesos: {e_weights}")
        traceback.print_exc()
        pesos_calculados = {} # Default a dict vacío en error para evitar None más adelante
    
    # 3.Formateo de la Tabla
    print("DEBUG (Finalizar) ► Formateando tabla final...")
    try:
        info_clima_dict_para_tabla = info_clima_obj.model_dump(mode='json') if info_clima_obj else {} 
        # Pasamos los OBJETOS Pydantic originales (o actualizados)
        tabla_final_md = formatear_preferencias_en_tabla(
            preferencias=preferencias_obj, 
            filtros=filtros_actualizados, 
            economia=economia_obj,
            codigo_postal_usuario=codigo_postal_usuario_val,
            info_clima_usuario=info_clima_dict_para_tabla # <-- PASAR INFO CLIMA
            
            # info_pasajeros también podría pasarse si el formateador lo usa
        )
        print("\n--- TABLA RESUMEN GENERADA (DEBUG) ---")
        print(tabla_final_md)
        print("--------------------------------------\n")
    except Exception as e_format:
        print(f"ERROR (Finalizar) ► Fallo formateando la tabla: {e_format}")
        tabla_final_md = "Error al generar el resumen de criterios."

    # 4. Crear y añadir mensaje final
    final_ai_msg = AIMessage(content=tabla_final_md)
    historial_final = list(historial)
    if not historial or historial[-1].content != final_ai_msg.content:
        historial_final.append(final_ai_msg)

    return {
        **state, # Propaga el estado original
        "filtros_inferidos": filtros_actualizados, # Sobrescribe con el actualizado
        "pesos": pesos_calculados,                 # Añade/Sobrescribe
        "messages": historial_final,               # Sobrescribe
        "tabla_resumen_criterios": tabla_final_md, # Añade/Sobrescribe
        "coches_recomendados": None,               # Añade/Sobrescribe
        "priorizar_ancho": priorizar_ancho_flag,   # Sobrescribe con el valor local
        "flag_penalizar_low_cost_comodidad": flag_penalizar_low_cost_comodidad, # Añade/Sobrescribe
        "flag_penalizar_deportividad_comodidad": flag_penalizar_deportividad_comodidad, # Añade/Sobrescribe
        "flag_penalizar_antiguo_por_tecnologia": flag_penalizar_antiguo_tec,
        "es_municipio_zbe": flag_es_municipio_zbe,
        "aplicar_logica_distintivo_ambiental": flag_aplicar_logica_distintivo,
        "codigo_postal_usuario": codigo_postal_usuario_val, 
        "info_clima_usuario": info_clima_obj, # Propagar el objeto completo
        "pregunta_pendiente": None                 # Sobrescribe
    }