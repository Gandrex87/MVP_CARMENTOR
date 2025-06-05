# utils/rag_carroceria.py
import os
import logging
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings 
from langchain_community.vectorstores import FAISS
from utils.rag_reader import cargar_carrocerias_desde_pdf
from typing import Optional, List, Dict, Any # Añade los que necesites
from utils.conversion import is_yes
from config.settings import (AVENTURA_SYNONYMS_RAG, USO_PROF_MIXTO_SYNONYMS_RAG, USO_PROF_PASAJEROS_SYNONYMS_RAG,
                             USO_PROF_MIXTO_SYNONYMS_RAG, ESTETICA_VALORADA_SYNONYMS_RAG, ESPACIO_PASAJEROS_NINOS_SYNONYMS_RAG, 
                             APASIONADO_MOTOR_SYNONYMS_RAG, SOLO_ELECTRICOS_SYNONYMS_RAG, ALTA_COMODIDAD_CARROCERIA_SYNONYMS_RAG,
                             NECESITA_ESPACIO_OBJETOS_ESPECIALES_SYNONYMS_RAG, CLIMA_MONTA_CARROCERIA_SYNONYMS_RAG, USO_PROF_CARGA_SYNONYMS_RAG 
                             , UMBRAL_RATING_COMODIDAD_RAG
                             )


# --- Constantes ---
PDF_PATH = "utils/tipos_carrocería.pdf"  # Ruta a tu PDF
FAISS_INDEX_DIR = "./faiss_carroceria_index" # Directorio donde se guardará/cargará el índice localmente

# Variable global para cachear el vectorstore en RAM después de cargarlo/construirlo
_vectorstore_cache = None


# Configurar logging básico si no lo tienes en otro lado
logging.basicConfig(level=logging.INFO, format='%(levelname)s (RAG): %(message)s')

def create_and_save_faiss_index(pdf_path: str, index_save_path: str):
    """
    Carga datos del PDF, construye el índice FAISS y lo guarda en disco.
    Esta función se llamaría explícitamente cuando el PDF cambie.
    """
    logging.info(f"Iniciando la creación del índice FAISS desde {pdf_path}...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("OPENAI_API_KEY no está definida en el entorno.")
        raise RuntimeError("OPENAI_API_KEY no definida.")

    try:
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        
        logging.info("Cargando y parseando datos del PDF...")
        data_from_pdf = cargar_carrocerias_desde_pdf(pdf_path)
        if not data_from_pdf:
            logging.error("No se pudieron cargar datos del PDF o el PDF está vacío.")
            raise ValueError("No se pudieron cargar datos del PDF.")

        docs = [
            Document(
                page_content=f"{item['tipo']}: {item['descripcion']} Tags: {item['tags']}",
                metadata={"tipo": item["tipo"]}
            )
            for item in data_from_pdf
        ]
        logging.info(f"Creando embeddings y construyendo índice FAISS para {len(docs)} documentos...")
        vectorstore = FAISS.from_documents(docs, embeddings)
        
        logging.info(f"Guardando índice FAISS en {index_save_path}...")
        vectorstore.save_local(index_save_path)
        logging.info(f"Índice FAISS guardado exitosamente en {index_save_path}.")
        return vectorstore # Devuelve el vectorstore recién construido por si se quiere usar inmediatamente
    except Exception as e:
        logging.error(f"Error durante la creación y guardado del índice FAISS: {e}")
        raise

def load_faiss_index(index_load_path: str, allow_dangerous_deserialization: bool = True) -> Optional[FAISS]:
    """
    Carga un índice FAISS preexistente desde el disco.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("OPENAI_API_KEY no está definida para cargar el índice.")
        raise RuntimeError("OPENAI_API_KEY no definida.")
    
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)

    if os.path.exists(index_load_path + "/index.faiss") and \
       os.path.exists(index_load_path + "/index.pkl"):
        try:
            logging.info(f"Cargando índice FAISS desde {index_load_path}...")
            # La flag allow_dangerous_deserialization es necesaria para cargar archivos .pkl
            # Asegúrate de confiar en el origen de tus archivos de índice.
            vectorstore = FAISS.load_local(index_load_path, embeddings, allow_dangerous_deserialization=allow_dangerous_deserialization)
            logging.info("Índice FAISS cargado exitosamente desde disco.")
            return vectorstore
        except Exception as e:
            logging.error(f"Error al cargar el índice FAISS desde {index_load_path}: {e}")
            # Podrías optar por reconstruirlo aquí si falla la carga y estás en desarrollo,
            # pero para producción, si el índice debe existir y no se puede cargar, es un error.
            return None # O lanzar la excepción
    else:
        logging.warning(f"No se encontraron archivos de índice FAISS en {index_load_path}.")
        return None

def get_vectorstore(force_rebuild: bool = False) -> FAISS:
    """
    Obtiene el vectorstore. Lo carga desde disco si existe y no está en caché,
    o lo construye (y guarda) si no existe o si force_rebuild es True.
    Cachea el vectorstore en RAM para la sesión actual.
    """
    global _vectorstore_cache
    
    if not force_rebuild and _vectorstore_cache is not None:
        logging.info("Usando Vector Store cacheado en RAM.")
        return _vectorstore_cache

    # Intentar cargar desde disco
    if not force_rebuild:
        vs_from_disk = load_faiss_index(FAISS_INDEX_DIR)
        if vs_from_disk:
            _vectorstore_cache = vs_from_disk
            return _vectorstore_cache
        else:
            logging.info(f"No se pudo cargar el índice desde {FAISS_INDEX_DIR} o no existe. Procediendo a construirlo.")
    
    # Si no se cargó o se fuerza la reconstrucción, construir y guardar
    try:
        _vectorstore_cache = create_and_save_faiss_index(PDF_PATH, FAISS_INDEX_DIR)
        return _vectorstore_cache
    except Exception as e:
        logging.error(f"Fallo crítico al obtener el vector store: {e}")
        # Decide cómo manejar esto: ¿lanzar excepción o devolver None y que el RAG falle controladamente?
        # Por ahora, lanzamos para que sea evidente el problema.
        raise RuntimeError(f"No se pudo construir ni cargar el vector store: {e}")


def get_recommended_carrocerias(
    preferencias: Dict[str, Any], 
    filtros_tecnicos: Optional[Dict[str, Any]], # <--- ASEGÚRATE QUE ESTE ARGUMENTO EXISTA 
    info_pasajeros: Optional[Dict[str, Any]], 
    info_clima: Optional[Dict[str, Any]], # <-- NUEVO ARGUMENTO
    k: int = 5 #antes 4
) -> List[str]:
    """
    Obtiene tipos de carrocería recomendados usando RAG,
    influenciado por las preferencias del usuario.
    """
    vs = get_vectorstore() 
    if not vs:
        logging.warning("WARN (RAG) ► Vectorstore no disponible. Devolviendo fallback de carrocerías.")
        return ["SUV", "MONOVOLUMEN", "FAMILIAR", "3VOL"][:k] 

    partes_query = []

    # --- 1. Construcción de Partes de la Query basada en Preferencias ---
    if is_yes(preferencias.get("solo_electricos")) and SOLO_ELECTRICOS_SYNONYMS_RAG:
        partes_query.extend(SOLO_ELECTRICOS_SYNONYMS_RAG)
    
    if is_yes(preferencias.get("valora_estetica")) and ESTETICA_VALORADA_SYNONYMS_RAG:
        partes_query.extend(ESTETICA_VALORADA_SYNONYMS_RAG)
    
    if is_yes(preferencias.get("apasionado_motor")) and APASIONADO_MOTOR_SYNONYMS_RAG:
        partes_query.extend(APASIONADO_MOTOR_SYNONYMS_RAG)
    
    if is_yes(preferencias.get("arrastra_remolque")):
        logging.info("INFO (RAG) ► Usuario arrastra remolque. Enriqueciendo query RAG para capacidad de arrastre.")
        partes_query.extend([
            "capacidad de carga", " transportar cargas grandes", "robusto", 
            "estructura resistente","remolcar caravana"])
    # Aventura
    aventura_val = preferencias.get("aventura")
    nivel_aventura_str = ""
    if hasattr(aventura_val, "value"): nivel_aventura_str = aventura_val.value.strip().lower()
    elif isinstance(aventura_val, str): nivel_aventura_str = aventura_val.strip().lower()

    if nivel_aventura_str and nivel_aventura_str in AVENTURA_SYNONYMS_RAG:
        partes_query.extend(AVENTURA_SYNONYMS_RAG[nivel_aventura_str])
    elif not nivel_aventura_str or nivel_aventura_str == "ninguna":
        if "ninguna" in AVENTURA_SYNONYMS_RAG: partes_query.extend(AVENTURA_SYNONYMS_RAG["ninguna"])
        else: partes_query.extend(["urbano", "carretera", "compacto"])

    # Uso Profesional
    if is_yes(preferencias.get("uso_profesional")):
        partes_query.append("profesional") 
        tipo_uso_prof_val = preferencias.get("tipo_uso_profesional")
        detalle_uso_str = ""
        if hasattr(tipo_uso_prof_val, "value"): detalle_uso_str = tipo_uso_prof_val.value.lower()
        elif isinstance(tipo_uso_prof_val, str): detalle_uso_str = tipo_uso_prof_val.lower()

        if detalle_uso_str == "carga" and USO_PROF_CARGA_SYNONYMS_RAG: partes_query.extend(USO_PROF_CARGA_SYNONYMS_RAG)
        elif detalle_uso_str == "pasajeros" and USO_PROF_PASAJEROS_SYNONYMS_RAG: partes_query.extend(USO_PROF_PASAJEROS_SYNONYMS_RAG)
        elif detalle_uso_str == "mixto" and USO_PROF_MIXTO_SYNONYMS_RAG: partes_query.extend(USO_PROF_MIXTO_SYNONYMS_RAG)
                
    # Información de Pasajeros
    if isinstance(info_pasajeros, dict):
        frecuencia = info_pasajeros.get("frecuencia", "nunca")
        num_ninos_silla = info_pasajeros.get("num_ninos_silla", 0)
        num_otros_pasajeros = info_pasajeros.get("num_otros_pasajeros", 0)

        if frecuencia != "nunca":
            if num_ninos_silla > 0 and ESPACIO_PASAJEROS_NINOS_SYNONYMS_RAG:
                partes_query.extend(ESPACIO_PASAJEROS_NINOS_SYNONYMS_RAG)
            elif (num_ninos_silla + num_otros_pasajeros) >= 2: 
                partes_query.extend(["espacio para pasajeros", "viajar acompañado", "amplitud interior", "muchas plazas"])
    else:
        logging.info("INFO (RAG Query) ► No se proporcionó información de pasajeros válida para RAG.")

    # Necesidad de Espacio para Objetos Especiales
    if is_yes(preferencias.get("necesita_espacio_objetos_especiales")) and NECESITA_ESPACIO_OBJETOS_ESPECIALES_SYNONYMS_RAG:
        logging.info("INFO (RAG) ► Necesidad de espacio objetos especiales. Enriqueciendo query.")
        partes_query.extend(NECESITA_ESPACIO_OBJETOS_ESPECIALES_SYNONYMS_RAG)
    
    # Alta Comodidad
    rating_comodidad_val = preferencias.get("rating_comodidad")
    if rating_comodidad_val is not None and rating_comodidad_val >= UMBRAL_RATING_COMODIDAD_RAG and ALTA_COMODIDAD_CARROCERIA_SYNONYMS_RAG:
        logging.info(f"INFO (RAG) ► Rating Comodidad alto. Enriqueciendo query para confort.")
        partes_query.extend(ALTA_COMODIDAD_CARROCERIA_SYNONYMS_RAG)
        
    # --- LÓGICA PARA INFLUIR RAG CON CLIMA CP DE MONTAÑA ---
    if info_clima and info_clima.get("ZONA_CLIMA_MONTA") is True:
        logging.info("INFO (RAG) ► Zona de Clima de Montaña detectada. Enriqueciendo query RAG.")
        if CLIMA_MONTA_CARROCERIA_SYNONYMS_RAG:
            partes_query.extend(CLIMA_MONTA_CARROCERIA_SYNONYMS_RAG)
    
    # --- 2. Limpieza y Formación de la Query String ---
    partes_unicas = []
    if partes_query: # Solo procesar si hay partes
        for p in partes_query:
            if p not in partes_unicas:
                partes_unicas.append(p)
            
    query_str = " ".join(partes_unicas).strip()
    if not query_str: 
        query_str = "coche versátil moderno confortable práctico" 
        logging.info(f"INFO (RAG) ► Query RAG vacía, usando fallback: '{query_str}'")

    logging.info(f"INFO (RAG) ► Query RAG construida: '{query_str}' con k={k}")
    print(f"DEBUG (RAG Query Construida) ► Partes: {partes_unicas} -> Query: '{query_str}'")

    # --- 3. Búsqueda por Similitud ---
    try:
        docs = vs.similarity_search(query_str, k=k + 3) # Pedir algunos más para el post-filtrado
    except Exception as e_rag_search:
        logging.error(f"ERROR (RAG) ► Fallo en similarity_search: {e_rag_search}")
        return ["SUV", "FAMILIAR", "COMPACTO"][:k]

    # --- 4. Extracción de Tipos Únicos de los Documentos ---
    tipos_obtenidos_rag = []
    if docs:
        seen_tipos = set()
        for doc in docs:
            tipo = doc.metadata.get("tipo")
            if tipo and tipo not in seen_tipos:
                tipos_obtenidos_rag.append(tipo)
                seen_tipos.add(tipo)
    
    # --- 5. Post-Filtrado Secuencial ---
    tipos_finales = list(tipos_obtenidos_rag) # Trabajar con una copia

    # Post-Filtro 1: Por necesidad de espacio para objetos especiales
    if is_yes(preferencias.get("necesita_espacio_objetos_especiales")):
        tipos_a_excluir_espacio = {"3VOL", "COUPE", "DESCAPOTABLE"}
        logging.info(f"INFO (RAG) ► Aplicando post-filtro por objetos especiales, excluyendo: {tipos_a_excluir_espacio}")
        original_antes_filtro = list(tipos_finales)
        tipos_finales = [tipo for tipo in tipos_finales if tipo.upper() not in tipos_a_excluir_espacio]
        if not tipos_finales and original_antes_filtro:
            logging.warning(f"WARN (RAG) ► Post-filtro por objetos especiales eliminó todos. Revirtiendo este filtro específico.")
            tipos_finales = original_antes_filtro # Revertir solo este filtro

    # Post-Filtro 2: Para perfiles claramente urbanos/particulares/sin carga voluminosa
    transporta_carga_val = preferencias.get("transporta_carga_voluminosa")
    if aventura_val == "ninguna" and \
       not is_yes(preferencias.get("uso_profesional")) and \
       not is_yes(transporta_carga_val): # Verifica también que no transporte carga voluminosa
        
        tipos_a_excluir_urbano = {"TODOTERRENO", "PICKUP", "COMERCIAL", "AUTOCARAVANA"} #Validar con Teo
        logging.info(f"INFO (RAG) ► Perfil urbano/particular/sin carga. Aplicando post-filtro, excluyendo: {tipos_a_excluir_urbano}")
        original_antes_filtro = list(tipos_finales)
        tipos_finales = [tipo for tipo in tipos_finales if tipo.upper() not in tipos_a_excluir_urbano]
        if not tipos_finales and original_antes_filtro:
            logging.warning(f"WARN (RAG) ► Post-filtro urbano eliminó todos. Revirtiendo este filtro específico.")
            tipos_finales = original_antes_filtro # Revertir solo este filtro
            
    # --- 6. Fallback Final y Retorno ---
    if not tipos_finales:
        logging.warning(f"WARN (RAG) ► RAG (después de post-filtros) no devolvió tipos para query: '{query_str}'. Usando fallback general.")
        tipos_finales = ["SUV", "FAMILIAR", "COMPACTO"]
            
    logging.info(f"INFO (RAG) ► Tipos de carrocería recomendados por RAG (final, top {k}): {tipos_finales[:k]}")
    return tipos_finales[:k]



#==========================================================#==========================================================#==========================================================

