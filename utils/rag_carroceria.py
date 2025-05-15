# utils/rag_carroceria.py
import os
import logging
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings 
from langchain_community.vectorstores import FAISS
from utils.rag_reader import cargar_carrocerias_desde_pdf
from typing import Optional, List, Dict, Any # Añade los que necesites
from utils.conversion import is_yes



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



# Mapa de sinónimos por nivel de aventura
AVENTURA_SYNONYMS = {
    "ninguna":   ["ciudad", "asfalto", "uso diario", "practicidad", "maniobrable"],
    "ocasional": ["campo", "ligero fuera de asfalto", "excursiones", "profesional", "versátil"],
    "extrema":   ["off-road", "terrenos difíciles","tracción 4x4","barro", "gran altura libre", "reductora"]
}

# USO_PROF_SYNONYMS = [
#     "profesional", "transporte de mercancías", "transporte de pasajeros", "herramientas", "comercio", "logística"
# ]

# NUEVOS SINÓNIMOS SUGERIDOS (a usar dinámicamente en get_recommended_carrocerias)
USO_PROF_CARGA_SYNONYMS = [
    "transporte de mercancías", "herramientas", "materiales", "logística", "entregas", "furgón" 
    # Tags del PDF relevantes: "Transporte de objetos especiales", "logística", "entregas", "comercio", "servicio técnico", "carga pesada"
]

USO_PROF_PASAJEROS_SYNONYMS = [
    "transporte de personas","vehículo de pasajeros", "transporte escolar", "rutas de personal",
    "muchos asientos"
    # Tags del PDF relevantes: "Muchos pasajeros" (en FURGONETA, MONOVOLUMEN), "viajes familiares" (FURGONETA) podría tener una connotación.
]

USO_PROF_MIXTO_SYNONYMS = [
    "uso mixto profesional", "versatilidad carga y pasajeros", "vehículo combi", 
    "transporte de equipo y personal", "trabajo y familia adaptable", "doble cabina"
    # Tags del PDF relevantes: FURGONETA (intrínsecamente mixto), PICKUP (doble cabina), SUV, FAMILIAR.
]


ESTETICA_VALORADA_SYNONYMS = [ # Si valora_estetica == "sí"
   "diseño", "elegancia", "llamar atención" # Algunos ya están en tags del PDF
]

ESPACIO_PASAJEROS_NINOS_SYNONYMS = [ # Si num_ninos_silla > 0 o muchos pasajeros
   "espacio sillas infantiles", "modularidad asientos", "accesibilidad plazas traseras"
]

APASIONADO_MOTOR_SYNONYMS = [ # Si apasionado_motor == "sí"
    "conducción emocionante", "singular", "motor avanzado", "ágil en curvas"
]

# Podrías incluso tener para SOLO_ELECTRICOS, aunque "eléctrico" es bastante directo
SOLO_ELECTRICOS_SYNONYMS = ["cero emisiones", "sostenible", "bajo consumo energético"]


def get_recommended_carrocerias(preferencias: dict,  filtros: dict, info_pasajeros: Optional[dict], k: int = 4) -> list[str]: # El arg 'filtros' sigue sin usarse
    vs = get_vectorstore() # Ahora usa la nueva lógica
    partes = []
    # Aquí lógica para construir 'partes' de la query RAG / basada en 'preferencias' y SYNONYMS.
    if is_yes(preferencias.get("solo_electricos")):
        partes.append("eléctrico")
        partes.extend(SOLO_ELECTRICOS_SYNONYMS)
    # if is_yes(preferencias.get("uso_profesional")):
    #     partes.extend(USO_PROF_SYNONYMS)
    if is_yes(preferencias.get("valora_estetica")):
       #partes.append("diseño") # Término principal
        partes.extend(ESTETICA_VALORADA_SYNONYMS)
    if is_yes(preferencias.get("apasionado_motor")):
        #partes.append("conducción emocionante") # Término principal
        partes.extend(APASIONADO_MOTOR_SYNONYMS)
            
    raw_av = preferencias.get("aventura")
    nivel_aventura_str = ""
    if hasattr(raw_av, "value"): # Si es un Enum
        nivel_aventura_str = raw_av.value.strip().lower()
    elif isinstance(raw_av, str): # Si ya es un string
        nivel_aventura_str = raw_av.strip().lower()

    if nivel_aventura_str in AVENTURA_SYNONYMS:
        partes.extend(AVENTURA_SYNONYMS[nivel_aventura_str])
    
    # --- Lógica Mejorada para USO_PROFESIONAL ---
    if is_yes(preferencias.get("uso_profesional")):
        partes.append("profesional") # Término base siempre que sea uso profesional

        # Obtener el detalle del uso profesional. Asumimos que si existe, está en 'preferencias'.
        # Si lo guardas en otro sitio (ej. un campo específico en el estado), ajusta cómo lo obtienes.
        detalle_uso = preferencias.get("tipo_uso_profesional", "").lower() # "" como default si no existe

        if detalle_uso == "carga":
            logging.info("RAG Query: Añadiendo sinónimos para USO PROFESIONAL - CARGA.")
            partes.extend(USO_PROF_CARGA_SYNONYMS)
        elif detalle_uso == "pasajeros":
            logging.info("RAG Query: Añadiendo sinónimos para USO PROFESIONAL - PASAJEROS.")
            partes.extend(USO_PROF_PASAJEROS_SYNONYMS)
        elif detalle_uso == "mixto":
            logging.info("RAG Query: Añadiendo sinónimos para USO PROFESIONAL - MIXTO.")
            partes.extend(USO_PROF_MIXTO_SYNONYMS)
                
    # Información de Pasajeros (¡NUEVO!)
    if isinstance(info_pasajeros, dict): # Verificar que info_pasajeros sea un diccionario y no None
        frecuencia = info_pasajeros.get("frecuencia", "nunca")
        num_ninos_silla = info_pasajeros.get("num_ninos_silla", 0)
        num_otros_pasajeros = info_pasajeros.get("num_otros_pasajeros", 0)

        if frecuencia != "nunca":
            if num_ninos_silla > 0:
                logging.info("RAG Query: Añadiendo sinónimos por niños con silla.")
                partes.extend(ESPACIO_PASAJEROS_NINOS_SYNONYMS)
            elif (num_ninos_silla + num_otros_pasajeros) >= 2: 
                logging.info("RAG Query: Añadiendo sinónimos por número de acompañantes >= 2.")
                partes.extend(["espacio para pasajeros", "viajar acompañado", "amplitud interior"])
                if "muchas plazas" not in partes: partes.append("muchas plazas")
                if "gran capacidad interior" not in partes: partes.append("gran capacidad interior")
    else:
        logging.info("RAG Query: No se proporcionó información de pasajeros o es inválida.")

    # Evitar duplicados en la lista de partes (opcional, pero puede limpiar la query)
    partes_unicas = []
    for p in partes:
        if p not in partes_unicas:
            partes_unicas.append(p)
    partes = partes_unicas
            
    logging.info(f"Partes de la query RAG (pre-join): {partes}")
    
    logging.info(f"Partes de la query RAG: {partes}")
    query = " ".join(partes) if partes else "coche versátil y práctico" # Query por defecto mejorada

    logging.info(f"Ejecutando búsqueda RAG con query: '{query}' y k={k}")
    docs = vs.similarity_search(query, k=k)
    
    tipos_recomendados = []
    seen_tipos = set()
    for doc in docs:
        tipo = doc.metadata.get("tipo")
        if tipo and tipo not in seen_tipos:
            tipos_recomendados.append(tipo)
            seen_tipos.add(tipo)
            
    logging.info(f"Tipos de carrocería recomendados por RAG: {tipos_recomendados}")
    return tipos_recomendados
