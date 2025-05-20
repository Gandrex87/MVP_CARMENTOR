# utils/build_faiss_index.py
import os
from dotenv import load_dotenv

if __name__ == "__main__":  
    load_dotenv() # Asegúrate de tener tu .env con OPENAI_API_KEY
    from .rag_carroceria import create_and_save_faiss_index, PDF_PATH, FAISS_INDEX_DIR

    print("Cargando variables de entorno...")
    print(f"Este script construirá el índice FAISS desde '{PDF_PATH}' y lo guardará en '{FAISS_INDEX_DIR}'.")
    # Opcional: Preguntar al usuario si está seguro, especialmente si el índice ya existe.
    # proceed = input(f"El directorio del índice '{FAISS_INDEX_DIR}' podría ser sobrescrito. ¿Continuar? (s/N): ")
    # if proceed.lower() != 's':
    #     print("Operación cancelada.")
    #     exit()

    try:
        # Verificar si el directorio existe, si no, crearlo (FAISS.save_local lo crea si no existe el path final)
        if not os.path.exists(FAISS_INDEX_DIR):
            os.makedirs(FAISS_INDEX_DIR, exist_ok=True) # exist_ok=True para no fallar si ya existe
            print(f"Directorio del índice creado: {FAISS_INDEX_DIR}")
            
        create_and_save_faiss_index(PDF_PATH, FAISS_INDEX_DIR)
        print("Proceso de construcción del índice completado.")
    except Exception as e:
        print(f"Error durante la construcción del índice: {e}")