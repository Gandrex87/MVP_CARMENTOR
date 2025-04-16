import os
from dotenv import load_dotenv
import logging
logging.basicConfig(level=logging.INFO)

load_dotenv()

GOOGLE_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
LANGCHAIN_TRACING = os.getenv("LANGSMITH_TRACING")
LANGCHAIN_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT")
LANGCHAIN_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGSMITH_PROJECT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not GOOGLE_CREDENTIALS:
    raise ValueError("No se encontró GOOGLE_APPLICATION_CREDENTIALS. Asegúrate de configurar tus credenciales de Google Cloud.")
