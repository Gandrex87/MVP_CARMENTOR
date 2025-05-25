# graph/builder.py (o graph/perfil/builder.py según tu estructura)

from langgraph.graph import StateGraph, START, END
from graph.perfil.state import EstadoAnalisisPerfil # Ajusta la ruta si es necesario
from graph.perfil.nodes import (preguntar_cp_inicial_node,   recopilar_cp_node,
    validar_cp_node,
    buscar_info_clima_node,
    recopilar_preferencias_node,validar_preferencias_node,
    inferir_filtros_node,validar_filtros_node,recopilar_economia_node, preguntar_economia_node,
    validar_economia_node, finalizar_y_presentar_node, preguntar_preferencias_node,
    preguntar_filtros_node, preguntar_economia_node,buscar_coches_finales_node,
    recopilar_info_pasajeros_node, validar_info_pasajeros_node,  preguntar_info_pasajeros_node,aplicar_filtros_pasajeros_node)
from .memory import get_memory 
from graph.perfil.condition import (ruta_decision_cp, ruta_decision_economia, ruta_decision_filtros, ruta_decision_perfil,ruta_decision_pasajeros, 
                                    decidir_ruta_inicial, route_based_on_state_node)

    
def build_sequential_agent_graph(): 
    workflow = StateGraph(EstadoAnalisisPerfil)

    # 1. Añadir todos los nodos (incluyendo el nuevo de economía)
    workflow.add_node("router", route_based_on_state_node) # <-- Nodo Router
    # Etapa 0: Codigo postal
    workflow.add_node("preguntar_cp_inicial", preguntar_cp_inicial_node) 
    workflow.add_node("recopilar_cp", recopilar_cp_node)
    workflow.add_node("validar_cp", validar_cp_node)
    workflow.add_node("buscar_info_clima", buscar_info_clima_node)
    
    # Etapa 1: Perfil
    workflow.add_node("recopilar_preferencias", recopilar_preferencias_node)
    workflow.add_node("validar_preferencias", validar_preferencias_node)
    workflow.add_node("preguntar_preferencias", preguntar_preferencias_node) 
    # Etapa 1.5: Pasajeros
    workflow.add_node("recopilar_info_pasajeros", recopilar_info_pasajeros_node) 
    workflow.add_node("validar_info_pasajeros", validar_info_pasajeros_node)   
    workflow.add_node("preguntar_info_pasajeros", preguntar_info_pasajeros_node) 
    workflow.add_node("aplicar_filtros_pasajeros", aplicar_filtros_pasajeros_node)
    # Etapa 2: Filtros Técnicos
    workflow.add_node("inferir_filtros", inferir_filtros_node)
    workflow.add_node("validar_filtros", validar_filtros_node)
    workflow.add_node("preguntar_filtros", preguntar_filtros_node) 
    # Etapa 3: Economía
    workflow.add_node("recopilar_economia", recopilar_economia_node)
    workflow.add_node("validar_economia", validar_economia_node)
    workflow.add_node("preguntar_economia", preguntar_economia_node) 
    
    # Etapa 4 y 5: Finalización y BQ
    workflow.add_node("finalizar_y_presentar", finalizar_y_presentar_node)
    workflow.add_node("buscar_coches_finales", buscar_coches_finales_node)

# 2. Definir punto de entrada FIJO al ROUTER
    workflow.set_entry_point("router")
# 2.1 Definir punto de entrada CONDICIONAL (Orden Correcto)
    workflow.add_conditional_edges(
        "router", # Nodo origen es el router
        decidir_ruta_inicial, # La función que contiene la lógica
        { # Mapeo: los strings devueltos a los nodos donde empezar CADA etapa
         
            "recopilar_cp": "recopilar_cp",
            "recopilar_preferencias": "recopilar_preferencias", 
            "recopilar_info_pasajeros": "recopilar_info_pasajeros",
            "inferir_filtros": "inferir_filtros",
            "recopilar_economia": "recopilar_economia", 
            "finalizar_y_presentar": "finalizar_y_presentar",
            "buscar_coches_finales": "buscar_coches_finales",
        }
    )

    # 3. Conectar las etapas en el orden CORRECTO (Perfil -> Pasajeros -> Filtros -> Economía -> Finalizar -> BQ)

# --- NUEVA ETAPA 0: CÓDIGO POSTAL ---
    # El router ya puede dirigir a recopilar_cp.
    # Si es el primerísimo turno, llm_cp_extractor en recopilar_cp hará la pregunta inicial.
    # preguntar_cp_inicial_node es para cuando se necesita re-preguntar explícitamente.
    workflow.add_edge("recopilar_cp", "validar_cp")
    workflow.add_conditional_edges("validar_cp", ruta_decision_cp, # Nueva función condicional
        {
            "repreguntar_cp": "preguntar_cp_inicial", 
            "buscar_clima": "buscar_info_clima"})
    workflow.add_edge("preguntar_cp_inicial", END) 
    # Después de buscar clima (o si se omitió CP), va al inicio de la etapa de Perfil
    workflow.add_edge("buscar_info_clima", "recopilar_preferencias") 
    
# Etapa 1: Perfil -> Pasajeros
    workflow.add_edge("recopilar_preferencias", "validar_preferencias")
    workflow.add_conditional_edges("validar_preferencias",ruta_decision_perfil, 
        {  "necesita_pregunta_perfil": "preguntar_preferencias", 
            "pasar_a_pasajeros": "recopilar_info_pasajeros" # <-- CORRECTO: Va a pasajeros
        })
    workflow.add_edge("preguntar_preferencias", END) 

    # Etapa 1.5: Pasajeros -> Filtros
    workflow.add_edge("recopilar_info_pasajeros", "validar_info_pasajeros")
    workflow.add_conditional_edges("validar_info_pasajeros", ruta_decision_pasajeros,
        {
            "necesita_pregunta_pasajero": "preguntar_info_pasajeros",
            "aplicar_filtros": "aplicar_filtros_pasajeros" 
        }
    )
    workflow.add_edge("preguntar_info_pasajeros", END) 
    workflow.add_edge("aplicar_filtros_pasajeros", "inferir_filtros") # <-- CORRECTO: Va a Etapa 2 (Filtros)

    # Etapa 2: Filtros Técnicos -> Economía
    workflow.add_edge("inferir_filtros", "validar_filtros")
    workflow.add_conditional_edges(
         "validar_filtros",
         ruta_decision_filtros,
         { "necesita_pregunta_filtro": "preguntar_filtros",
           "pasar_a_economia": "recopilar_economia" # <-- Va directo a recopilar economía
         })
    workflow.add_edge("preguntar_filtros", END) 
 
    # Etapa 3: Economía -> Finalizar
    workflow.add_edge("recopilar_economia", "validar_economia")
    workflow.add_conditional_edges( "validar_economia",ruta_decision_economia, 
        {
            "necesita_pregunta_economia": "preguntar_economia", # Usa el nodo genérico
            "pasar_a_finalizar": "finalizar_y_presentar" 
        }
    )
    workflow.add_edge("preguntar_economia", END) 

    # Etapa 4 y 5: Finalización y Búsqueda
    workflow.add_edge("finalizar_y_presentar", "buscar_coches_finales") 
    workflow.add_edge("buscar_coches_finales", END) 

    # 4. Compilar
    print("INFO ► Compilando el grafo...")
    graph = workflow.compile(checkpointer=get_memory())
    print("INFO ► Grafo compilado exitosamente.")
    return graph
