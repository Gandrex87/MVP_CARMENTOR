# # utils/rag_carroceria.py
# import os
# import logging
# from langchain.schema import Document
# from langchain_openai import OpenAIEmbeddings 
# from langchain_community.vectorstores import FAISS
# from utils.rag_reader import cargar_carrocerias_desde_pdf
# from typing import Optional, List, Dict, Any # Añade los que necesites
# from dotenv import load_dotenv
# import json
# from utils.conversion import is_yes
# from graph.perfil.state import ( PerfilUsuario, FiltrosInferidos, InfoPasajeros, InfoClimaUsuario, )
# from config.settings import (AVENTURA_SYNONYMS_RAG, USO_PROF_MIXTO_SYNONYMS_RAG, USO_PROF_PASAJEROS_SYNONYMS_RAG,
#                              USO_PROF_MIXTO_SYNONYMS_RAG, ESTETICA_VALORADA_SYNONYMS_RAG, ESPACIO_PASAJEROS_NINOS_SYNONYMS_RAG, 
#                              APASIONADO_MOTOR_SYNONYMS_RAG, SOLO_ELECTRICOS_SYNONYMS_RAG, ALTA_COMODIDAD_CARROCERIA_SYNONYMS_RAG,
#                              NECESITA_ESPACIO_OBJETOS_ESPECIALES_SYNONYMS_RAG, CLIMA_MONTA_CARROCERIA_SYNONYMS_RAG, USO_PROF_CARGA_SYNONYMS_RAG 
#                              , UMBRAL_RATING_COMODIDAD_RAG
#                              )

# # Después (en create_and_save_faiss_index):
# from langchain_google_vertexai import VertexAIEmbeddings

# # --- Constantes ---
# PDF_PATH = "utils/tipos_carroceria.pdf"  # Ruta a tu PDF
# FAISS_INDEX_DIR = "./faiss_carroceria_index" # Directorio donde se guardará/cargará el índice localmente

# # Variable global para cachear el vectorstore en RAM después de cargarlo/construirlo
# _vectorstore_cache = None


# # Configurar logging básico si no lo tienes en otro lado
# logging.basicConfig(level=logging.DEBUG, format='%(levelname)s (RAG): %(message)s')
# #logging.basicConfig(level=logging.INFO,

# def create_and_save_faiss_index(pdf_path: str, index_save_path: str):
#     """
#     Carga datos del PDF, construye el índice FAISS y lo guarda en disco.
#     Esta función se llamaría explícitamente cuando el PDF cambie.
#     """
#     logging.info(f"Iniciando la creación del índice FAISS desde {pdf_path}...")
#     api_key = os.getenv("OPENAI_API_KEY")
#     if not api_key:
#         logging.error("OPENAI_API_KEY no está definida en el entorno.")
#         raise RuntimeError("OPENAI_API_KEY no definida.")

#     try:
#         #embeddings = OpenAIEmbeddings(openai_api_key=api_key)
#         embeddings = VertexAIEmbeddings(model_name="text-multilingual-embedding-002") 
#         logging.info("Cargando y parseando datos del PDF...")
#         data_from_pdf = cargar_carrocerias_desde_pdf(pdf_path)
#         if not data_from_pdf:
#             logging.error("No se pudieron cargar datos del PDF o el PDF está vacío.")
#             raise ValueError("No se pudieron cargar datos del PDF.")
        
#         docs = []
#         for item in data_from_pdf:
#             # El page_content es para la búsqueda semántica.
#             page_content = f"{item['tipo']}: {item['descripcion']} Tags: {item['tags']}"
            
#             # El metadata es para el filtrado exacto. Le pasamos el item entero.
#             # LangChain se encargará de manejarlo.
#             metadata = item.copy()  # Usamos una copia para evitar efectos secundarios
            
#             docs.append(Document(page_content=page_content, metadata=metadata))
        
        
#         logging.info(f"Creando embeddings y construyendo índice FAISS para {len(docs)} documentos...")
#         vectorstore = FAISS.from_documents(docs, embeddings)
        
#         logging.info(f"Guardando índice FAISS en {index_save_path}...")
#         vectorstore.save_local(index_save_path)
#         logging.info(f"Índice FAISS guardado exitosamente en {index_save_path}.")
#         return vectorstore # Devuelve el vectorstore recién construido por si se quiere usar inmediatamente
#     except Exception as e:
#         logging.error(f"Error durante la creación y guardado del índice FAISS: {e}")
#         raise

# def load_faiss_index(index_load_path: str, allow_dangerous_deserialization: bool = True) -> Optional[FAISS]:
#     """
#     Carga un índice FAISS preexistente desde el disco.
#     """
#     api_key = os.getenv("OPENAI_API_KEY")
#     if not api_key:
#         logging.error("OPENAI_API_KEY no está definida para cargar el índice.")
#         raise RuntimeError("OPENAI_API_KEY no definida.")
    
#     #embeddings = OpenAIEmbeddings(openai_api_key=api_key)
#     embeddings = VertexAIEmbeddings(model_name="text-multilingual-embedding-002") 

#     if os.path.exists(index_load_path + "/index.faiss") and \
#        os.path.exists(index_load_path + "/index.pkl"):
#         try:
#             logging.info(f"Cargando índice FAISS desde {index_load_path}...")
#             # La flag allow_dangerous_deserialization es necesaria para cargar archivos .pkl
#             # Asegúrate de confiar en el origen de tus archivos de índice.
#             vectorstore = FAISS.load_local(index_load_path, embeddings, allow_dangerous_deserialization=allow_dangerous_deserialization)
#             logging.info("Índice FAISS cargado exitosamente desde disco.")
#             return vectorstore
#         except Exception as e:
#             logging.error(f"Error al cargar el índice FAISS desde {index_load_path}: {e}")
#             # Podrías optar por reconstruirlo aquí si falla la carga y estás en desarrollo,
#             # pero para producción, si el índice debe existir y no se puede cargar, es un error.
#             return None # O lanzar la excepción
#     else:
#         logging.warning(f"No se encontraron archivos de índice FAISS en {index_load_path}.")
#         return None

# def get_vectorstore(force_rebuild: bool = False) -> FAISS:
#     """
#     Obtiene el vectorstore. Lo carga desde disco si existe y no está en caché,
#     o lo construye (y guarda) si no existe o si force_rebuild es True.
#     Cachea el vectorstore en RAM para la sesión actual.
#     """
#     global _vectorstore_cache
    
#     if not force_rebuild and _vectorstore_cache is not None:
#         logging.info("Usando Vector Store cacheado en RAM.")
#         return _vectorstore_cache

#     # Intentar cargar desde disco
#     if not force_rebuild:
#         vs_from_disk = load_faiss_index(FAISS_INDEX_DIR)
#         if vs_from_disk:
#             _vectorstore_cache = vs_from_disk
#             return _vectorstore_cache
#         else:
#             logging.info(f"No se pudo cargar el índice desde {FAISS_INDEX_DIR} o no existe. Procediendo a construirlo.")
    
#     # Si no se cargó o se fuerza la reconstrucción, construir y guardar
#     try:
#         _vectorstore_cache = create_and_save_faiss_index(PDF_PATH, FAISS_INDEX_DIR)
#         return _vectorstore_cache
#     except Exception as e:
#         logging.error(f"Fallo crítico al obtener el vector store: {e}")
#         # Decide cómo manejar esto: ¿lanzar excepción o devolver None y que el RAG falle controladamente?
#         # Por ahora, lanzamos para que sea evidente el problema.
#         raise RuntimeError(f"No se pudo construir ni cargar el vector store: {e}")

# # Añade estas importaciones al principio de tu archivo utils/rag_carroceria.py
# import json
# import time
# import re
# from google.cloud import aiplatform
# import vertexai
# from vertexai.generative_models import GenerativeModel, Part


# # --- NUEVA FUNCIÓN AUXILIAR PARA CONSOLIDAR EL CONTEXTO ---

# def _crear_contexto_para_llm_juez(
#     preferencias: PerfilUsuario,
#     info_pasajeros: Optional[InfoPasajeros],
#     info_clima: Optional[InfoClimaUsuario],
#     filtros_inferidos: Optional[FiltrosInferidos]
# ) -> Dict[str, Any]:
#     """
#     Crea un diccionario de contexto LIMPIO, INTERPRETATIVO y relevante para
#     pasar al LLM Juez, guiando su razonamiento.
#     """
#     # Convertimos los objetos Pydantic a diccionarios para un manejo fácil y seguro
#     prefs_dict = preferencias.model_dump(exclude_none=True)
#     pasajeros_dict = info_pasajeros.model_dump(exclude_none=True) if info_pasajeros else {}

#     contexto = {}
    
#     # --- LÓGICA DE EXTRACCIÓN MEJORADA Y MÁS INTELIGENTE ---

#     # 1. Recopilar TODOS los ratings altos para reflejar múltiples prioridades.
#     ratings = {k: v for k, v in prefs_dict.items() if k.startswith("rating_")}
#     prioridades_altas = []
#     UMBRAL_PRIORIDAD_ALTA = 8
    
#     for key, value in ratings.items():
#         if value >= UMBRAL_PRIORIDAD_ALTA:
#             # Limpiamos el nombre de la clave para que sea legible
#             nombre_prioridad = key.replace('rating_', '').replace('_', ' ')
#             prioridades_altas.append(f"'{nombre_prioridad.capitalize()}' ({value}/10)")

#     if prioridades_altas:
#         # Unimos todas las prioridades altas en una sola frase clara.
#         contexto['prioridades_del_usuario'] = f"El usuario da alta prioridad a: {', '.join(prioridades_altas)}."

#     # 2. Describir las necesidades de espacio y pasajeros de forma explícita.
#     if is_yes(prefs_dict.get('transporta_carga_voluminosa')):
#         contexto['necesidad_de_carga'] = "Requiere transportar carga voluminosa."
    
#     if pasajeros_dict.get('suele_llevar_acompanantes'):
#         frecuencia = pasajeros_dict.get('frecuencia_viaje_con_acompanantes', 'ocasionalmente')
#         contexto['necesidad_de_pasajeros'] = f"Suele viajar con pasajeros de forma {frecuencia}."
    
#     # Esta es una desambiguación CRUCIAL
#     if 'necesidad_de_carga' in contexto and 'necesidad_de_pasajeros' in contexto and ratings.get('rating_comodidad', 0) >= 8:
#         contexto['aclaracion_clave'] = "Necesita espacio de carga, aunque prioriza tambien comodidad de los pasajeros en viaje"

#     # # 3. Describir el perfil de uso y aventura de forma explícita.
#     # aventura = prefs_dict.get("aventura", "ninguna")
#     # if aventura == "ninguna":
#     #     contexto['perfil_de_conduccion'] = "Uso exclusivo en ciudad y carretera (asfalto)."
#     # else:
#     #     contexto['perfil_de_conduccion'] = f"el perfil del usuario lo hace buscar un coche que le permita salir de aventura, off-road '{aventura}'."
    
#     if is_yes(prefs_dict.get('uso_profesional')):
#         uso_prof_tipo = prefs_dict.get('tipo_uso_profesional', 'general').capitalize()
#         contexto['perfil_de_uso'] = f"Profesional para '{uso_prof_tipo}'."
#         # Añadimos un detalle crucial si es para ciudad
#         if prefs_dict.get("aventura") == "ninguna":
#             contexto['entorno_principal'] = "Principalmente en entorno urbano y carretera."
#     else:
#         # Lógica para uso particular
#         aventura = prefs_dict.get("aventura", "ninguna")
#         if aventura == "ninguna":
#             contexto['perfil_de_uso'] = "Particular, principalmente en ciudad y carretera."
#         else:
#             contexto['perfil_de_uso'] = f"perfil particular, aunque busca un coche que le permita salir de aventura de manera '{aventura}'."
#     # 4. Añadir restricciones duras.
#     if is_yes(prefs_dict.get('solo_electricos')):
#         contexto['restriccion_mecanica'] = "Debe ser un coche 100% eléctrico."
        
#     return contexto


# # --- NUEVA FUNCIÓN DE PUNTUACIÓN Y RE-RANKING ---


# def puntuar_candidato_con_llm(contexto_usuario: Dict[str, Any], coche_candidato: Dict[str, Any]) -> Optional[Dict[str, Any]]:
#     """
#     Usa un LLM (Gemini en Vertex AI) para puntuar la idoneidad de un coche para un usuario.
#     Recibe un contexto de usuario unificado y limpio.
#     """
#     # NOTA: Usamos el nombre del modelo más reciente, rápido y eficiente para esta tarea.
#     #model = GenerativeModel("gemini-1.0-pro")
#     model = GenerativeModel("gemini-2.0-flash-lite")

#     # --- PROMPT MEJORADO Y MÁS CONCISO ---
#     # En lugar de un JSON completo, creamos un resumen en lenguaje natural
#     # de las preferencias clave del usuario. Esto es más eficiente y directo.
    
#     resumen_preferencias = []
#     for key, value in contexto_usuario.items():
#         resumen_preferencias.append(f"- {key.replace('_', ' ').capitalize()}: {value}")
#     resumen_str = "\n".join(resumen_preferencias)

#     prompt = f"""
#     **Tarea:** Eres un experto asesor de coches. Evalúa la idoneidad de la carrocería para el usuario.

#     **Preferencias Clave del Usuario:**
#     {resumen_str}

#     **Información del Coche a Evaluar:**
#     - **Tipo:** {coche_candidato.get('tipo', 'N/A')}
#     - **Descripción:** {coche_candidato.get('descripcion', 'N/A')}
#     - **Tags:** {coche_candidato.get('tags', 'N/A')}
#     - Metadatos Clave:
#         - Plazas Máximas Típicas: {coche_candidato.get('plazas_maximas', 5)}
#         - Permite Carga Especial: {coche_candidato.get('permite_objetos_especiales', False)}

#     **Instrucciones de Puntuación:**
#     1.  **Reglas No Negociables (Primero y más importante):**
#         - Si el usuario necesita 'plazas_minimas_necesarias', y las 'Plazas Máximas Típicas' del coche son insuficientes, la puntuación **no puede ser superior a 2**.
#         - Si el usuario tiene una 'restriccion_mecanica' (ej: solo eléctrico), y el coche evaluado es incompatible, la puntuación **no puede ser superior a 1**.

#     2.  **Evaluación General:**
#         - Después de aplicar las reglas no negociables, evalúa cómo el resto de las características del coche encajan con las 'prioridades_del_usuario' y su 'perfil_de_uso'.
#         - Otorga una puntuación final de 1 (totalmente inadecuado) a 10 (perfectamente adecuado).

#     3.  **Formato de Salida:**
#         - Responde **únicamente** con un objeto JSON válido con las claves "puntuacion" (int) y "justificacion" (str breve).
#     """

#     try:
#         response = model.generate_content([prompt])
#         texto_respuesta = response.text
#         json_match = re.search(r'\{.*\}', texto_respuesta, re.DOTALL)
#         if not json_match:
#             logging.error(f"ERROR (LLM Judge) ► El LLM no devolvió un JSON para {coche_candidato.get('tipo')}.")
#             return None
        
#         data = json.loads(json_match.group(0))
#         puntuacion = int(data.get("puntuacion", 0))
#         justificacion = data.get("justificacion", "")

#         logging.info(f"INFO (LLM Judge) ► {coche_candidato.get('tipo')} puntuado con {puntuacion}/10.")
#         # logging.debug(f"DEBUG (LLM Judge) ► Justificación: {justificacion}") # Opcional si quieres ver la razón
        
#         return {"puntuacion": puntuacion, "justificacion": justificacion}

#     except Exception as e:
#         logging.error(f"ERROR (LLM Judge) ► Fallo en la llamada a Gemini para {coche_candidato.get('tipo')}: {e}")
#         return None


# # --- VERSIÓN FINAL Y OPTIMIZADA DE LA FUNCIÓN PRINCIPAL ---
# import concurrent.futures
# def get_recommended_carrocerias(
#     preferencias: PerfilUsuario,
#     info_pasajeros: Optional[InfoPasajeros],
#     info_clima: Optional[InfoClimaUsuario],
#     filtros_inferidos: Optional[FiltrosInferidos],
#     k: int = 4,
#     num_candidates_to_rerank: int = 8,
#     max_workers: int = 4,# Número de llamadas paralelas
# ) -> List[str]:
#     """
#     Obtiene recomendaciones usando un sistema RAG avanzado con query inteligente
#     y Re-Ranking por LLM.
#     """
#     try:
#         # La inicialización de Vertex AI debería hacerse una vez al inicio de la aplicación,
#         # no en cada llamada a esta función.
#         pass
#     except Exception:
#         pass

#     vs = get_vectorstore()
#     if not vs:
#         logging.warning("WARN (RAG) ► Vectorstore no disponible.")
#         return ["SUV", "MONOVOLUMEN", "FAMILIAR", "3VOL"][:k]

#     # --- PASO 1: CONVERTIR OBJETOS PYDANTIC A DICCIONARIOS ---
#     # Esto resuelve el AttributeError y nos da una fuente de datos consistente.
#     prefs_dict = preferencias.model_dump(exclude_none=True)
#     pasajeros_dict = info_pasajeros.model_dump(exclude_none=True) if info_pasajeros else {}
#     clima_dict = info_clima.model_dump(exclude_none=True) if info_clima else {}
#     filtros_dict = filtros_inferidos.model_dump(exclude_none=True) if filtros_inferidos else {}

#     # --- PASO 2: CONSTRUCCIÓN DE QUERY INTELIGENTE PARA LA BÚSQUEDA INICIAL ---
#     partes_query = []
    
#     # Lógica de Aventura
#     # Aventura
#     aventura_val = prefs_dict.get("aventura")
#     nivel_aventura_str = ""
#     if hasattr(aventura_val, "value"): nivel_aventura_str = aventura_val.value.strip().lower()
#     elif isinstance(aventura_val, str): nivel_aventura_str = aventura_val.strip().lower()

#     if nivel_aventura_str and nivel_aventura_str in AVENTURA_SYNONYMS_RAG:
#         partes_query.extend(AVENTURA_SYNONYMS_RAG[nivel_aventura_str])
#     elif not nivel_aventura_str or nivel_aventura_str == "ninguna":
#         if "ninguna" in AVENTURA_SYNONYMS_RAG: partes_query.extend(AVENTURA_SYNONYMS_RAG["ninguna"])
#         else: partes_query.extend(["urbano", "carretera", "compacto"])
    
#     # Lógica de Pasajeros para la query (¡NUEVO Y CRUCIAL!)
#     if pasajeros_dict.get("num_otros_pasajeros", 0) >= 4:
#         partes_query.extend(["muchos pasajeros", "siete plazas", "familiar grande", "máxima capacidad interior"])

#     # Lógica de Ratings para refinar la query
#     UMBRAL_RATING_IMPORTANTE = 8
#     if (prefs_dict.get("rating_impacto_ambiental", 0) >= UMBRAL_RATING_IMPORTANTE or
#         prefs_dict.get("rating_costes_uso", 0) >= UMBRAL_RATING_IMPORTANTE):
#         partes_query.extend(["bajo consumo", "mantenimiento económico", "eficiente"])
    
#     if is_yes(prefs_dict.get("apasionado_motor")) and APASIONADO_MOTOR_SYNONYMS_RAG:
#         partes_query.extend(APASIONADO_MOTOR_SYNONYMS_RAG)
    
#     # Uso Profesional
#     if is_yes(prefs_dict.get("uso_profesional")):
#         partes_query.append("profesional") 
#         tipo_uso_prof_val = prefs_dict.get("tipo_uso_profesional")
#         detalle_uso_str = ""
#         if hasattr(tipo_uso_prof_val, "value"): detalle_uso_str = tipo_uso_prof_val.value.lower()
#         elif isinstance(tipo_uso_prof_val, str): detalle_uso_str = tipo_uso_prof_val.lower()

#         if detalle_uso_str == "carga" and USO_PROF_CARGA_SYNONYMS_RAG: partes_query.extend(USO_PROF_CARGA_SYNONYMS_RAG)
#         elif detalle_uso_str == "pasajeros" and USO_PROF_PASAJEROS_SYNONYMS_RAG: partes_query.extend(USO_PROF_PASAJEROS_SYNONYMS_RAG)
#         elif detalle_uso_str == "mixto" and USO_PROF_MIXTO_SYNONYMS_RAG: partes_query.extend(USO_PROF_MIXTO_SYNONYMS_RAG)

#     # Alta Comodidad
#     rating_comodidad_val = prefs_dict.get("rating_comodidad")
#     if rating_comodidad_val is not None and rating_comodidad_val >= UMBRAL_RATING_COMODIDAD_RAG and ALTA_COMODIDAD_CARROCERIA_SYNONYMS_RAG:
#         logging.info(f"INFO (RAG) ► Rating Comodidad alto. Enriqueciendo query para confort.")
#         partes_query.extend(ALTA_COMODIDAD_CARROCERIA_SYNONYMS_RAG)
    
#     if is_yes(prefs_dict.get("arrastra_remolque")):
#         logging.info("INFO (RAG) ► Usuario arrastra remolque. Enriqueciendo query RAG para capacidad de arrastre.")
#         partes_query.extend([
#             "capacidad de carga", " transportar cargas grandes","remolcar caravana"])
     
#     # --- LÓGICA PARA INFLUIR RAG CON CLIMA CP DE MONTAÑA ---
#     if info_clima and clima_dict.get("ZONA_CLIMA_MONTA") is True:
#         logging.info("INFO (RAG) ► Zona de Clima de Montaña detectada. Enriqueciendo query RAG.")
#         if CLIMA_MONTA_CARROCERIA_SYNONYMS_RAG:
#             partes_query.extend(CLIMA_MONTA_CARROCERIA_SYNONYMS_RAG)
                 
#     # Información de Pasajeros
#     if isinstance(pasajeros_dict, dict):
#         frecuencia = pasajeros_dict.get("frecuencia", "nunca")
#         num_ninos_silla = pasajeros_dict.get("num_ninos_silla", 0)
#         num_otros_pasajeros = pasajeros_dict.get("num_otros_pasajeros", 0)

#         if frecuencia != "nunca":
#             if num_ninos_silla > 0 and ESPACIO_PASAJEROS_NINOS_SYNONYMS_RAG:
#                 partes_query.extend(ESPACIO_PASAJEROS_NINOS_SYNONYMS_RAG)
#             elif (num_ninos_silla + num_otros_pasajeros) >= 2: 
#                 partes_query.extend(["espacio para pasajeros", "viajar acompañado", "amplitud interior", "muchas plazas"])
#     else:
#         logging.info("INFO (RAG Query) ► No se proporcionó información de pasajeros válida para RAG.")
    
#     # Puedes añadir más lógicas aquí si lo deseas
#     partes_unicas = list(dict.fromkeys(partes_query))
#     query_str = " ".join(partes_unicas).strip()
#     logging.info(f"INFO (RAG) ► Query para búsqueda inicial construida: '{query_str}'")
#     print(f"DEBUG (RAG) ► Query para búsqueda inicial construida: '{query_str}")
    
#     # --- PASO 3: BÚSQUEDA INICIAL DE CANDIDATOS ---
#     #docs_retrieved = vs.similarity_search(query_str, k=12) solo devuelve los docs sin puntuacion.
#     docs_with_scores = vs.similarity_search_with_relevance_scores(query_str, k=12)
#     candidatos_a_puntuar_with_scores = docs_with_scores[:num_candidates_to_rerank]
#     # Corregimos el logging para que maneje la nueva estructura de tupla
#     logging.info(f"INFO (RAG) ► Candidatos pre-seleccionados para re-ranking: {[doc.metadata.get('tipo') for doc, score in candidatos_a_puntuar_with_scores]}")
    
#     # --- PASO 4: CREACIÓN DEL CONTEXTO UNIFICADO PARA EL LLM JUEZ ---
#     contexto_usuario = _crear_contexto_para_llm_juez(
#         preferencias, info_pasajeros, info_clima, filtros_inferidos
#     )
#     logging.info(f"INFO (RAG) ► Contexto de usuario consolidado para el LLM Juez: {contexto_usuario}")
    
#     # --- PASO 5: PUNTUACIÓN Y RE-RANKING CON LLM ---
#    # --- PASO 5: PUNTUACIÓN Y RE-RANKING EN PARALELO ---
#     candidatos_puntuados = []
#     logging.info(f"INFO (RAG) ► Iniciando re-ranking PARALELO de {len(candidatos_a_puntuar_with_scores)} candidatos...")

#     with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
#         # Mapeamos cada futuro a la información completa del candidato (metadata y score)
#         future_to_candidato = {
#             executor.submit(puntuar_candidato_con_llm, contexto_usuario, doc.metadata): (doc.metadata, score)
#             for doc, score in candidatos_a_puntuar_with_scores
#         }

#         for future in concurrent.futures.as_completed(future_to_candidato):
#             coche_candidato_metadata, relevance_score = future_to_candidato[future]
#             try:
#                 resultado_puntuacion = future.result()
#                 if resultado_puntuacion:
#                     candidatos_puntuados.append({
#                         "tipo": coche_candidato_metadata['tipo'],
#                         "puntuacion_llm": resultado_puntuacion['puntuacion'],
#                         "justificacion_llm": resultado_puntuacion['justificacion'],
#                         "relevance_score": relevance_score, # Guardamos el score para desempate
#                         "metadata": coche_candidato_metadata
#                     })
#             except Exception as exc:
#                 logging.error(f"ERROR (RAG Pool) ► El candidato '{coche_candidato_metadata['tipo']}' generó una excepción: {exc}")

#     # --- PASO 6: ORDENAR Y DEVOLVER EL RESULTADO FINAL ---
#     if not candidatos_puntuados:
#         logging.error("ERROR (RAG) ► Ningún candidato pudo ser puntuado por el LLM.")
#         return ["SUV", "FAMILIAR", "COMPACTO"]

#     # Ordenamos por un doble criterio: primero por la puntuación del LLM (más alta es mejor)
#     # y como segundo criterio, por la puntuación de relevancia (más alta es mejor).
#     lista_reordenada = sorted(
#         candidatos_puntuados,
#         key=lambda x: (x['puntuacion_llm'], x['relevance_score']),
#         reverse=True
#     )
    
#     logging.info(f"INFO (RAG) ► Nuevo orden tras re-ranking y desempate: {[c['tipo'] for c in lista_reordenada]}")
    
#     tipos_finales = [c['tipo'] for c in lista_reordenada]
    
#     logging.info(f"INFO (RAG) ► Tipos de carrocería recomendados (final, top {k}): {tipos_finales[:k]}")
#     return tipos_finales[:k]





# # #==========================================================#==========================================================#==========================================================
# # --- Bloque de Ejecución Principal ---
# if __name__ == "__main__":
#     # Esta sección solo se ejecuta cuando corres: python3 -m utils.rag_carroceria
#     print("--- Iniciando la ejecución del script de RAG Carrocería ---")
#     try:
#         from dotenv import load_dotenv
#         import logging
#         load_dotenv()
#         logging.info("Variables de entorno cargadas desde .env")
#     except ImportError:
#         logging.warning("python-dotenv no está instalado. Asegúrate de que OPENAI_API_KEY esté definida manualmente.")

#     # --- INSPECCIÓN DE METADATOS (NUEVO) ---
#     print("\n[Paso de Inspección] Cargando y mostrando los metadatos parseados del PDF...")
#     # Llamamos a la función de parseo directamente para ver su salida.
#     datos_parseados = cargar_carrocerias_desde_pdf(PDF_PATH)
    
#     # Imprimimos cada entrada de forma legible
#     for item in datos_parseados:
#         print(json.dumps(item, indent=4, ensure_ascii=False))
#         print("-" * 20)
    
#     print(f"\nTotal de entradas parseadas: {len(datos_parseados)}")
#     print("-" * 40)
    
#     # --- Creación del Índice ---
#     print("\n[Paso 1] Intentando construir o cargar el Vector Store...")
#     vector_store = get_vectorstore(force_rebuild=True) 
#     # Usamos force_rebuild=True para asegurar que la función de creación se llame sí o sí.
#     vector_store = get_vectorstore(force_rebuild=True) 
    
#     if vector_store:
#         print("✅ Vector Store creado/cargado exitosamente.")
#         print(f"El índice debería estar en la carpeta: {os.path.abspath(FAISS_INDEX_DIR)}")
#     else:
#         print("❌ Fallo al crear/cargar el Vector Store.")
#         exit() # Salimos si no se pudo crear el índice
        
#     # --- Prueba de la función de recomendación ---
#     print("\n[Paso 2] Probando la función get_recommended_carrocerias con un ejemplo...")
    
#     # Creamos un ejemplo de preferencias de usuario
#     preferencias_ejemplo = {
#         "aventura": "ocasional",
#         "necesita_espacio_objetos_especiales": "sí",
#         "valora_estetica": "no"
#     }
#     info_pasajeros_ejemplo = {"num_otros_pasajeros": 2}
#     info_clima_ejemplo = {"ZONA_CLIMA_MONTA": False}
    
#     print(f"Preferencias de prueba: {preferencias_ejemplo}")
    
#     # Llamamos a la función principal que queremos probar
#     recomendaciones = get_recommended_carrocerias(
#         preferencias=preferencias_ejemplo,
#         filtros_tecnicos=None,
#         info_pasajeros=info_pasajeros_ejemplo,
#         info_clima=info_clima_ejemplo
#     )
    
#     print("\n--- Resultados de la Prueba ---")
#     print(f"Recomendaciones obtenidas: {recomendaciones}")
#     print("---------------------------------")
