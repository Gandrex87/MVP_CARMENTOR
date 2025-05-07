# utils/rag_carroceria.py
import os
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings 
from langchain_community.vectorstores import FAISS
from utils.rag_reader import cargar_carrocerias_desde_pdf
from utils.conversion import is_yes


# Mapa de sinónimos por nivel de aventura
AVENTURA_SYNONYMS = {
    "ninguna":   ["ciudad", "urbano", "asfalto", "bajo consumo", "carretera"],
    "ocasional": ["campo", "ligero fuera de asfalto", "excursiones", "familia", 'uso_profesional'],
    "extrema":   ["off-road", "terrenos difíciles", "extrema","tracción 4x4"]
}

USO_PROF_SYNONYMS = [
    "profesional", "entregas", "transporte", "carga", "comercio"
]

# 1️⃣ Define tu fuente de datos enriquecida (puede venir de un CSV o PDF)
DATA = cargar_carrocerias_desde_pdf("./utils/tipos_carroceria.pdf")

# Variable privada para cachear el vectorstore
_vectorstore = None

def _build_vectorstore():
    # ② Cogemos la API key en el momento de crear embeddings
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Para usar RAG necesitas definir OPENAI_API_KEY en tu entorno"
        )
    # Creamos embeddings con la versión correcta
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    # Convertimos cada entrada en un Document
    docs = [
        Document(
            page_content=f"{item['tipo']}: {item['descripcion']} Tags: {item['tags']}",
            metadata={"tipo": item["tipo"]}
        )
        for item in DATA
    ]
    return FAISS.from_documents(docs, embeddings)

def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = _build_vectorstore()
    return _vectorstore

def get_recommended_carrocerias(preferencias: dict, filtros: dict, k: int = 4) -> list[str]:
    vs = get_vectorstore()
    # Montamos un query sencillo según las preferencias
    partes = []
       
    if is_yes(preferencias.get("solo_electricos")):
        partes.append("eléctrico")
    if is_yes(preferencias.get("valora_estetica")):
        partes.append("diseño")
        # ─── Enriquecer uso profesional ───
    if is_yes(preferencias.get("uso_profesional")):
        partes.append("profesional")
        partes.extend(USO_PROF_SYNONYMS)
            
    # ─── ENRIQUECIMIENTO de aventura ───
    raw_av = preferencias.get("aventura")
    if hasattr(raw_av, "value"):
        nivel = raw_av.value.strip().lower()
    else:
        nivel = str(raw_av or "").strip().lower()

    if nivel in AVENTURA_SYNONYMS:
        #partes.append(f"{nivel}")
        partes.extend(AVENTURA_SYNONYMS[nivel])
    #DEBUG
    print(f"Query partes: {partes}")
    # Si no hay nada, query por defecto      
    query = " ".join(partes) or "coche"
    # Recuperamos los documentos más relevantes
    docs = vs.similarity_search(query, k=k)
    tipos = []
    for doc in docs:
        tipo = doc.metadata.get("tipo")
        if tipo and tipo not in tipos:
            tipos.append(tipo)
    return tipos
