# graph/builder.py (o graph/perfil/builder.py según tu estructura)

from langgraph.graph import StateGraph, START, END
from graph.perfil.state import EstadoAnalisisPerfil # Ajusta la ruta si es necesario
from graph.perfil.nodes import (recopilar_preferencias_node,validar_preferencias_node,
    inferir_filtros_node,validar_filtros_node,recopilar_economia_node,
    validar_economia_node, finalizar_y_presentar_node, preguntar_preferencias_node, 
    preguntar_filtros_node, preguntar_economia_node)
from .memory import get_memory 
from graph.perfil.condition import ruta_decision_economia, ruta_decision_filtros, ruta_decision_perfil

    
def build_sequential_agent_graph(): 
    workflow = StateGraph(EstadoAnalisisPerfil)

    # 1. Añadir todos los nodos (incluyendo el nuevo de economía)
    print("INFO ► Añadiendo nodos al grafo...")
    workflow.add_node("recopilar_preferencias", recopilar_preferencias_node)
    workflow.add_node("validar_preferencias", validar_preferencias_node)
    workflow.add_node("preguntar_preferencias", preguntar_preferencias_node) # <-- Nuevo
    workflow.add_node("inferir_filtros", inferir_filtros_node)
    workflow.add_node("validar_filtros", validar_filtros_node)
    workflow.add_node("preguntar_filtros", preguntar_filtros_node) 
    workflow.add_node("recopilar_economia", recopilar_economia_node)
    workflow.add_node("validar_economia", validar_economia_node)
    workflow.add_node("preguntar_economia", preguntar_economia_node) # <-- Nuevo
    workflow.add_node("finalizar_y_presentar", finalizar_y_presentar_node)

    # 2. Definir punto de entrada (sigue siendo el mismo)
    #workflow.add_edge(START, "recopilar_preferencias")
    workflow.set_entry_point("recopilar_preferencias") # <-- Forma recomendada

    # 3. Conectar las etapas

    # Etapa 1: Perfil (Como la dejamos)
    # ... (add_edge y add_conditional_edges para perfil) ...
    workflow.add_edge("recopilar_preferencias", "validar_preferencias")
    workflow.add_conditional_edges(
        "validar_preferencias",
        ruta_decision_perfil, 
        {
            "necesita_pregunta_perfil": "preguntar_preferencias", 
            "pasar_a_filtros": "inferir_filtros"  
        }
    )
    workflow.add_edge("preguntar_preferencias", END) 

    # Etapa 2: Filtros (Como la teníamos planeada)
    # ... (add_edge y add_conditional_edges para filtros) ...
    workflow.add_edge("inferir_filtros", "validar_filtros")
    workflow.add_conditional_edges(
         "validar_filtros", 
         ruta_decision_filtros,
         {
            # Si faltan filtros, vamos al nodo que pregunta
         "necesita_pregunta_filtro": "preguntar_filtros", 
            # Si están completos, avanzamos a economía
         "pasar_a_economia": "recopilar_economia" 
         }
     )
    # El nodo que pregunta filtros también termina el turno
    workflow.add_edge("preguntar_filtros", END) 

    # Etapa 3: Economía (Modificado)
    workflow.add_edge("recopilar_economia", "validar_economia")
    workflow.add_conditional_edges(
        "validar_economia",
        ruta_decision_economia, # Usa la función modificada
        {
            # Si devuelve "necesita_pregunta_economia", VAMOS AL NODO QUE PREGUNTA
            "necesita_pregunta_economia": "preguntar_economia", 
            # Si devuelve "pasar_a_finalizar", VAMOS AL INICIO DE LA ETAPA 4
            "pasar_a_finalizar": "finalizar_y_presentar" 
        }
    )
    # El nodo que pregunta economía, también TERMINA la ejecución de este invoke
    workflow.add_edge("preguntar_economia", END) # <-- ¡Importante!

    # Etapa 4: Finalización (Como antes)
    workflow.add_edge("finalizar_y_presentar", END) 

    # 4. Compilar
    print("INFO ► Compilando el grafo...")
    graph = workflow.compile(checkpointer=get_memory())
    print("INFO ► Grafo compilado exitosamente.")
    return graph
