# graph/perfil/builder.py
from langgraph.graph import StateGraph, START ,END
from .state import EstadoAnalisisPerfil
from .nodes import analizar_perfil_usuario_node, validar_preferencias_node
from .memory import get_memory
from .condition import necesita_mas_info  # si ya moviste la lógica

def build_perfil_graph():
    workflow = StateGraph(EstadoAnalisisPerfil)

    # Nodos
    workflow.add_node("analizar_perfil_usuario", analizar_perfil_usuario_node)
    workflow.add_node("validar_preferencias", validar_preferencias_node)

    # Flujo
    workflow.add_edge(START, "analizar_perfil_usuario")
    workflow.add_edge("analizar_perfil_usuario", "validar_preferencias")
    workflow.add_conditional_edges("validar_preferencias", necesita_mas_info)

    return workflow.compile(checkpointer=get_memory())

#Para hacer uso de la funcion:
# from graph.perfil.builder import build_perfil_graph

# graph = build_perfil_graph()

# # Ejemplo de uso
# config = {"configurable": {"thread_id": "abc123"}}
# input_message = HumanMessage(content="Quiero un coche elegante para la ciudad")

# output = graph.invoke({"messages": [input_message]}, config=config)
# for m in output["messages"]:
#     m.pretty_print()



