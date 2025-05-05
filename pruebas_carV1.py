# run_agent.py
import sys
import traceback
from dotenv import load_dotenv # Para cargar variables de entorno como la API key
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from graph.perfil.builder import build_sequential_agent_graph


# --- Importaciones de LangChain/LangGraph y de tu proyecto ---
# Asegúrate que las rutas sean correctas desde donde ejecutes el script
# Si ejecutas desde la raíz del proyecto, estas importaciones deberían funcionar
# si tienes los __init__.py en su sitio.
try:
    from langchain_core.messages import HumanMessage, AIMessage
    from graph.perfil.builder import build_sequential_agent_graph # Ajusta la ruta
    # Necesario si quieres que el script espere si no se puede importar el grafo
    # from graph.state import EstadoAnalisisPerfil # No estrictamente necesario aquí
except ImportError as e:
    print(f"Error: No se pudieron importar módulos necesarios: {e}")
    print("Asegúrate de que las rutas sean correctas, que los __init__.py existan y que el entorno virtual esté activado.")
    sys.exit(1) # Salir si no se pueden importar

# --- Función Principal de Conversación ---
def run_conversation(thread_id: str = "conversacion_script_1"):
    """Inicia y maneja una conversación con el agente LangGraph."""
    
    # Cargar variables de entorno (ej: OPENAI_API_KEY desde .env)
    load_dotenv() 
    print("INFO: Variables de entorno cargadas.")

    # Construir el grafo (asume que esto puede tardar un poco la primera vez)
    print("INFO: Construyendo el grafo del agente...")
    try:
        graph = build_sequential_agent_graph() 
        print("INFO: Grafo compilado exitosamente.")
    except Exception as e_build:
        print(f"ERROR FATAL: No se pudo construir el grafo: {e_build}")
        traceback.print_exc()
        sys.exit(1)

    # Configuración de la conversación (usando el thread_id pasado)
    config = {"configurable": {"thread_id": thread_id}}
    print(f"\n--- Iniciando Conversación ---")
    print(f"(Thread ID: {thread_id})")
    print("(Escribe 'salir', 'exit' o 'quit' para terminar)")

    while True:
        # Obtener entrada del usuario
        try:
            user_input = input("\nTú: ")
            if user_input.lower() in ["salir", "exit", "quit"]:
                print("Asistente: ¡Hasta luego!")
                break
            # Mensaje a enviar al grafo
            current_input_messages = [HumanMessage(content=user_input)]
        except EOFError: # Manejo por si se corta la entrada
            print("\nAsistente: Detectado fin de entrada. ¡Adiós!")
            break

        print("Asistente: Pensando...")
        # Invocar el grafo
        try:
            output = graph.invoke({"messages": current_input_messages}, config) 
            
            # Procesar y mostrar la última respuesta de la IA
            if output and "messages" in output and output["messages"]:
                 last_message = output["messages"][-1]
                 
                 print("\nAsistente:")
                 if isinstance(last_message, AIMessage):
                     # pretty_print() funciona bien en terminales que soportan colores
                     last_message.pretty_print() 
                     
                     # --- Condición de Parada ---
                     # Sigue siendo la forma más simple por ahora.
                     # Asegúrate que el texto del encabezado de tu tabla final sea EXACTO.
                     if "✅ He entendido lo siguiente" in last_message.content: 
                         print("\n--- Fin de la Conversación (Resumen Final Generado) ---")
                         break
                         
                 else: # Mensaje inesperado
                     print(f"(Mensaje inesperado: {type(last_message)})")
                     print(last_message)
                     break # Salir si algo raro pasa
                     
            else: # Salida vacía o sin mensajes
                 print("WARN: La salida del grafo no contiene mensajes o está vacía.")
                 break

        except Exception as e: # Capturar cualquier error durante la invocación
            print(f"\nERROR: Ocurrió un error al invocar el grafo: {e}")
            traceback.print_exc() 
            break # Salir en caso de error

# --- Punto de Entrada del Script ---
if __name__ == "__main__":
    # Puedes hardcodear un ID o tomarlo de argumentos de línea de comandos si quieres
    conversation_thread_id = "mi_conversacion_123" 
    run_conversation(thread_id=conversation_thread_id)