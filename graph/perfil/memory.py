# from langgraph.checkpoint.memory import MemorySaver
# graph/perfil/memory.py
import os
import logging
import asyncio # Para ejecutar setup si es necesario desde un contexto síncrono
from typing import Literal, Optional

# Activar, descomentar estas tres lineas de codigo en caso de hacer pruebas en local y con memoria RAM del ordenador
# #======================================================================
# from langgraph.checkpoint.memory import MemorySaver
# def get_memory():
#     return MemorySaver()
# #======================================================================

# # Activar, descomentar las lineas abajo en caso de hacer API y con memoria en SQLCLOUD:
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver 

logger = logging.getLogger(__name__)


##Variable global para almacenar la instancia del checkpointer inicializada
_checkpointer_instance: Optional[AsyncPostgresSaver] = None
_db_conn_str: Optional[str] = None # Para construir la instancia si es necesario

async def ensure_tables_exist(conn_string: str):
    """
    Asegura que las tablas del checkpointer existan.
    Se llama una vez durante el startup de la aplicación.
    """
    logger.info(f"AsyncPostgresSaver: Verificando/creando tablas para la BBDD...")
    try:
        ##Usar async with para el setup, como en la documentación
        async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer_for_setup:
            await checkpointer_for_setup.setup()
        logger.info("AsyncPostgresSaver: Tablas del checkpointer verificadas/creadas exitosamente.")
    except ImportError:
        logger.error("Error de importación para AsyncPostgresSaver o psycopg. "
                     "Instala 'langgraph-checkpoint-postgres' y 'psycopg[binary]'.")
        raise
    except Exception as e:
        logger.error(f"Error durante el setup de tablas de AsyncPostgresSaver: {e}", exc_info=True)
        raise RuntimeError(f"No se pudo hacer setup de las tablas de AsyncPostgresSaver: {e}")

def set_checkpointer_instance(instance: AsyncPostgresSaver):
    """Función para establecer la instancia global del checkpointer desde main.py"""
    global _checkpointer_instance
    _checkpointer_instance = instance

def get_memory() -> AsyncPostgresSaver:
    """
    Devuelve la instancia del checkpointer AsyncPostgresSaver previamente inicializada.
    """
    global _checkpointer_instance
    if _checkpointer_instance is None:
      ##  Esto no debería ocurrir si la inicialización en startup fue exitosa.
        logger.error("ERROR CRÍTICO: get_memory() llamado pero _checkpointer_instance es None.")
        raise RuntimeError(
            "AsyncPostgresSaver no ha sido inicializado. "
            "Asegúrate de que el evento de startup de FastAPI lo configure correctamente."
        )
    return _checkpointer_instance
