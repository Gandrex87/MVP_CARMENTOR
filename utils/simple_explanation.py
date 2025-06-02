#usada en el Nodo final para explicar el coche recomendado
import pandas as pd
import traceback
from typing import Dict, List, Optional, Any
import logging # Asegúrate de tener logging
from langchain_core.messages import AIMessage
from graph.perfil.state import EstadoAnalisisPerfil, PerfilUsuario 
from utils.conversion import is_yes 

def _generar_explicacion_simple_coche(
    coche_dict: Dict[str, Any], 
    pesos_normalizados: Dict[str, float],
    preferencias_usuario: Optional[PerfilUsuario], 
    n_top_factores: int = 2
) -> str:
    """
    Genera una explicación simple basada en los N factores con mayor contribución al score.
    """
    if not preferencias_usuario: 
        return "Este coche se ajusta bien a varios de los criterios generales."

    contribuciones = []
    
    # ¡ESTE MAPA ES CRUCIAL Y DEBE ESTAR COMPLETO Y CORRECTO!
    mapa_pesos_a_explicacion = {
        "estetica": {"nombre_amigable": "un buen diseño", "pref_campo": "valora_estetica", "pref_texto_si": "valoras la estética"},
        "premium": {"nombre_amigable": "un carácter premium", "pref_campo": "apasionado_motor", "pref_texto_si": "eres un apasionado del motor"},
        "singular": {"nombre_amigable": "un toque de singularidad", "pref_campo": "prefiere_diseno_exclusivo", "pref_texto_si": "prefieres un diseño exclusivo"},
        "altura_libre_suelo": {"nombre_amigable": "buena altura libre al suelo", "pref_campo": "aventura", "pref_texto_si": "buscas aventura"},
        "traccion": {"nombre_amigable": "un sistema de tracción eficaz", "pref_campo": "aventura", "pref_texto_si": "buscas aventura"}, # También influenciado por clima
        "reductoras": {"nombre_amigable": "capacidades off-road (reductoras)", "pref_campo": "aventura", "pref_texto_si": "buscas aventura extrema"},
        "batalla": {"nombre_amigable": "una buena batalla (espacio interior)", "pref_campo": "altura_mayor_190", "pref_texto_si": "eres una persona alta"},
        "indice_altura_interior": {"nombre_amigable": "un buen índice de altura interior", "pref_campo": "altura_mayor_190", "pref_texto_si": "eres una persona alta"}, # También influenciado por alta comodidad
        "rating_fiabilidad_durabilidad": {"nombre_amigable": "alta fiabilidad y durabilidad", "pref_campo": "rating_fiabilidad_durabilidad", "pref_texto_si": "la fiabilidad y durabilidad son muy importantes para ti"},
        "rating_seguridad": {"nombre_amigable": "un alto nivel de seguridad", "pref_campo": "rating_seguridad", "pref_texto_si": "la seguridad es clave para ti"}, # También influenciado por niebla
        "rating_comodidad": {"nombre_amigable": "un gran confort", "pref_campo": "rating_comodidad", "pref_texto_si": "el confort es una prioridad"},
        "rating_impacto_ambiental": {"nombre_amigable": "un menor impacto ambiental", "pref_campo": "rating_impacto_ambiental", "pref_texto_si": "te preocupa el impacto ambiental"},
        "rating_tecnologia_conectividad": {"nombre_amigable": "buena tecnología y conectividad", "pref_campo": "rating_tecnologia_conectividad", "pref_texto_si": "la tecnología es importante para ti"},
        "devaluacion": {"nombre_amigable": "una baja depreciación esperada", "pref_campo": "prioriza_baja_depreciacion", "pref_texto_si": "te importa la baja depreciación"},
        "maletero_minimo_score": {"nombre_amigable": "un maletero mínimo adecuado", "pref_campo": "transporta_carga_voluminosa", "pref_texto_si": "necesitas transportar carga"},
        "maletero_maximo_score": {"nombre_amigable": "un maletero máximo generoso", "pref_campo": "transporta_carga_voluminosa", "pref_texto_si": "necesitas transportar carga"},
        "largo_vehiculo_score": {"nombre_amigable": "un buen tamaño general (largo)", "pref_campo": "necesita_espacio_objetos_especiales", "pref_texto_si": "necesitas espacio para objetos especiales"},
        "ancho_general_score": {"nombre_amigable": "una buena anchura general", "pref_campo": "priorizar_ancho", "pref_texto_si": "necesitas un coche ancho para pasajeros/objetos"},
        "autonomia_vehiculo": {"nombre_amigable": "una buena autonomía", "pref_campo": "rating_comodidad", "pref_texto_si": "valoras el confort (que puede incluir viajes largos)"},
        "fav_bajo_peso": {"nombre_amigable": "un peso contenido (eficiencia)", "pref_campo": "rating_impacto_ambiental", "pref_texto_si": "te preocupa el impacto ambiental"},
        "fav_bajo_consumo": {"nombre_amigable": "un bajo consumo", "pref_campo": "rating_impacto_ambiental", "pref_texto_si": "te preocupa el impacto ambiental y/o los costes"},
        "fav_bajo_coste_uso_directo": {"nombre_amigable": "bajos costes de uso", "pref_campo": "rating_costes_uso", "pref_texto_si": "los costes de uso son importantes para ti"},
        "fav_bajo_coste_mantenimiento_directo": {"nombre_amigable": "bajos costes de mantenimiento", "pref_campo": "rating_costes_uso", "pref_texto_si": "los costes de mantenimiento son importantes para ti"},
        "par_motor_remolque_score": {"nombre_amigable": "buen par motor para remolcar", "pref_campo": "arrastra_remolque", "pref_texto_si": "necesitas arrastrar remolque"},
        "cap_remolque_cf_score": {"nombre_amigable": "buena capacidad de remolque con freno", "pref_campo": "arrastra_remolque", "pref_texto_si": "necesitas arrastrar remolque"},
        "cap_remolque_sf_score": {"nombre_amigable": "buena capacidad de remolque sin freno", "pref_campo": "arrastra_remolque", "pref_texto_si": "necesitas arrastrar remolque"},
        "fav_menor_superficie_planta": {"nombre_amigable": "un tamaño compacto para aparcar", "pref_campo": "problemas_aparcar_calle", "pref_texto_si": "tienes problemas para aparcar en la calle"},
        "fav_menor_diametro_giro": {"nombre_amigable": "un buen diámetro de giro (maniobrabilidad)", "pref_campo": "espacio_sobra_garage", "pref_texto_si": "tu garaje es ajustado"},
        "fav_menor_largo_garage": {"nombre_amigable": "un largo adecuado para tu garaje", "pref_campo": "problema_dimension_garage", "pref_texto_si": "el largo es un problema en tu garaje"}, # Se podría mejorar para mostrar la dimensión
        "fav_menor_ancho_garage": {"nombre_amigable": "un ancho contenido para tu garaje", "pref_campo": "problema_dimension_garage", "pref_texto_si": "el ancho es un problema en tu garaje"},
        "fav_menor_alto_garage": {"nombre_amigable": "una altura adecuada para tu garaje", "pref_campo": "problema_dimension_garage", "pref_texto_si": "la altura es un problema en tu garaje"},
        "deportividad_style_score": {"nombre_amigable": "un carácter deportivo", "pref_campo": "estilo_conduccion", "pref_texto_si": "prefieres un estilo de conducción deportivo"},
        "fav_menor_rel_peso_potencia_score": {"nombre_amigable": "una buena relación peso/potencia", "pref_campo": "estilo_conduccion", "pref_texto_si": "prefieres un estilo de conducción deportivo"},
        "potencia_maxima_style_score": {"nombre_amigable": "una potencia considerable", "pref_campo": "estilo_conduccion", "pref_texto_si": "prefieres un estilo de conducción deportivo"},
        "par_motor_style_score": {"nombre_amigable": "un buen par motor para dinamismo", "pref_campo": "estilo_conduccion", "pref_texto_si": "prefieres un estilo de conducción deportivo"},
        "fav_menor_aceleracion_score": {"nombre_amigable": "una buena aceleración", "pref_campo": "estilo_conduccion", "pref_texto_si": "prefieres un estilo de conducción deportivo"},
    }

    for clave_peso, peso_norm in pesos_normalizados.items():
        if peso_norm > 0.01: # Considerar solo pesos con alguna relevancia
            clave_feature_scaled = ""
            # --- Lógica para mapear clave_peso a clave_feature_scaled ---
            if clave_peso.startswith("rating_"): clave_feature_scaled = clave_peso.replace("rating_", "") + "_scaled"
            elif clave_peso.endswith("_score"): clave_feature_scaled = clave_peso.replace("_score", "") + "_scaled"
            elif clave_peso.startswith("fav_menor_"): clave_feature_scaled = clave_peso.replace("fav_menor_", "menor_") + "_scaled"
            elif clave_peso.startswith("fav_bajo_"): clave_feature_scaled = clave_peso.replace("fav_", "") + "_scaled"
            elif clave_peso == "deportividad_style_score": clave_feature_scaled = "deportividad_style_scaled"
            elif clave_peso == "potencia_maxima_style_score": clave_feature_scaled = "potencia_maxima_style_scaled"
            elif clave_peso == "par_motor_style_score": clave_feature_scaled = "par_scaled" 
            elif clave_peso == "ancho_general_score": clave_feature_scaled = "ancho_scaled" # El peso es ancho_general_score, la feature es ancho_scaled
            else: clave_feature_scaled = clave_peso + "_scaled"
            # --- Fin lógica de mapeo ---
            
            valor_escalado = coche_dict.get(clave_feature_scaled)

            # --- AJUSTAR UMBRAL DE VALOR_ESCALADO ---
            if valor_escalado is not None and valor_escalado > 0.40: # Umbral ligeramente más bajo
                contribucion = valor_escalado * peso_norm
                if clave_peso in mapa_pesos_a_explicacion:
                    info_mapa = mapa_pesos_a_explicacion[clave_peso]
                    pref_valor_usuario = getattr(preferencias_usuario, info_mapa["pref_campo"], None)
                    
                    # --- LÓGICA MEJORADA PARA condicion_pref_cumplida ---
                    condicion_pref_cumplida = False
                    if isinstance(pref_valor_usuario, (int, float)): # Es un rating 0-10
                        condicion_pref_cumplida = pref_valor_usuario >= 5 # Umbral para considerar un rating activo en explicación
                    elif isinstance(pref_valor_usuario, bool): # Para campos sí/no que son booleanos
                        condicion_pref_cumplida = pref_valor_usuario is True
                    elif isinstance(pref_valor_usuario, str) and is_yes(pref_valor_usuario): # Para campos sí/no que son strings
                        condicion_pref_cumplida = True
                    elif isinstance(pref_valor_usuario, list) and pref_valor_usuario: # Para List[Enum] como problema_dimension_garage
                        # Si el peso es relevante, la lista no estará vacía
                        # Aquí podríamos ser más específicos si el texto lo requiere
                        condicion_pref_cumplida = True 
                    elif pref_valor_usuario is not None and not isinstance(pref_valor_usuario, (int, float, bool, str, list)):
                        # Podría ser un Enum (NivelAventura, EstiloConduccion, etc.)
                        # Si hay un peso asociado, la preferencia se considera activa para la explicación.
                        condicion_pref_cumplida = True
                    # --- FIN LÓGICA MEJORADA ---
                    
                    if condicion_pref_cumplida:
                        contribuciones.append({
                            "nombre_amigable_caracteristica": info_mapa["nombre_amigable"],
                            "contrib": contribucion,
                            "pref_texto_usuario": info_mapa["pref_texto_si"]
                        })
                else:
                    logging.warning(f"WARN (Explicacion) ► Clave de peso '{clave_peso}' no encontrada en mapa_pesos_a_explicacion.")


    if not contribuciones:
        return "Se ajusta bien a tus criterios generales."

    contribuciones.sort(key=lambda x: x["contrib"], reverse=True)
    top_contribuciones = contribuciones[:n_top_factores]

    if not top_contribuciones:
         return "Es una opción interesante según tus preferencias."

    frases_explicativas = []
    for item in top_contribuciones:
        frases_explicativas.append(f"ofrece {item['nombre_amigable_caracteristica']} (importante porque {item['pref_texto_usuario']})")
    
    if len(frases_explicativas) == 1:
        return f"Destaca principalmente porque {frases_explicativas[0]}."
    elif len(frases_explicativas) > 1:
        explicacion_final = f"Destaca porque {frases_explicativas[0]}"
        for i in range(1, len(frases_explicativas)):
            # Usar un conector más variado y natural
            if i == 1 and len(frases_explicativas) == 2:
                conector = " y también porque "
            elif i == len(frases_explicativas) - 1 : # El último
                 conector = ", y finalmente porque "
            else: # Intermedios
                 conector = ", además porque "
            explicacion_final += f"{conector}{frases_explicativas[i]}"
        explicacion_final += "."
        return explicacion_final
        
    return "Es una buena opción considerando tus prioridades."