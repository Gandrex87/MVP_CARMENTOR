# graph/builder.py

from langgraph.graph import StateGraph, START, END
from graph.perfil.state import EstadoAnalisisPerfil # Ajusta la ruta si es necesario
from graph.perfil.nodes import (preguntar_cp_inicial_node,   recopilar_cp_node, validar_cp_node, buscar_info_clima_node,
    recopilar_preferencias_node,validar_preferencias_node, construir_filtros_node,recopilar_economia_node, preguntar_economia_node,
    validar_economia_node, preguntar_preferencias_node, preguntar_economia_node,buscar_coches_finales_node,
    recopilar_info_pasajeros_node, validar_info_pasajeros_node,  preguntar_info_pasajeros_node,aplicar_filtros_pasajeros_node, calcular_recomendacion_economia_modo1_node,
    calcular_flags_dinamicos_node,calcular_pesos_finales_node,formatear_tabla_resumen_node, calcular_km_anuales_postprocessing_node)
from graph.perfil.memory import get_memory 
from graph.perfil.condition import (ruta_decision_cp, ruta_decision_economia, ruta_decision_perfil,ruta_decision_pasajeros, 
                                    decidir_ruta_inicial, route_based_on_state_node)
import logging

    
# def build_sequential_agent_graph(): 
#     workflow = StateGraph(EstadoAnalisisPerfil)

#     # 1. Añadir todos los nodos (incluyendo el nuevo de economía)
#     workflow.add_node("router", route_based_on_state_node) # <-- Nodo Router
#     # Etapa 0: Codigo postal
#     workflow.add_node("preguntar_cp_inicial", preguntar_cp_inicial_node) 
#     workflow.add_node("recopilar_cp", recopilar_cp_node)
#     workflow.add_node("validar_cp", validar_cp_node)
#     workflow.add_node("buscar_info_clima", buscar_info_clima_node)
    
#     # Etapa 1: Perfil
#     workflow.add_node("recopilar_preferencias", recopilar_preferencias_node)
#     workflow.add_node("validar_preferencias", validar_preferencias_node)
#     workflow.add_node("preguntar_preferencias", preguntar_preferencias_node) 
#     # Etapa 1.5: Pasajeros
#     workflow.add_node("recopilar_info_pasajeros", recopilar_info_pasajeros_node) 
#     workflow.add_node("validar_info_pasajeros", validar_info_pasajeros_node)   
#     workflow.add_node("preguntar_info_pasajeros", preguntar_info_pasajeros_node) 
#     workflow.add_node("aplicar_filtros_pasajeros", aplicar_filtros_pasajeros_node)
#     # Etapa 2: Filtros Técnicos
#     workflow.add_node("inferir_filtros", inferir_filtros_node)
#     # Etapa 3: Economía
#     workflow.add_node("recopilar_economia", recopilar_economia_node)
#     workflow.add_node("validar_economia", validar_economia_node)
#     workflow.add_node("preguntar_economia", preguntar_economia_node) 
    
#     # Etapa 4 y 5: Finalización y BQ
#     workflow.add_node("calcular_recomendacion_economia_modo1", calcular_recomendacion_economia_modo1_node)
#     workflow.add_node("calcular_flags_dinamicos", calcular_flags_dinamicos_node)
#     workflow.add_node("calcular_pesos_finales", calcular_pesos_finales_node)
#     workflow.add_node("formatear_tabla_resumen", formatear_tabla_resumen_node) 
#     workflow.add_node("calcular_km_anuales_postprocessing", calcular_km_anuales_postprocessing_node)
#     workflow.add_node("buscar_coches_finales", buscar_coches_finales_node)

# # 2. Definir punto de entrada FIJO al ROUTER
#     workflow.set_entry_point("router")
# # 2.1 Definir punto de entrada CONDICIONAL
#     workflow.add_conditional_edges(
#         "router", # Nodo origen es el router
#         decidir_ruta_inicial, # La función que contiene la lógica
#         { # Mapeo: los strings devueltos a los nodos donde empezar CADA etapa
         
#             "recopilar_cp": "recopilar_cp",
#             "recopilar_preferencias": "recopilar_preferencias", 
#             "recopilar_info_pasajeros": "recopilar_info_pasajeros",
#             "inferir_filtros": "inferir_filtros",
#             "recopilar_economia": "recopilar_economia", 
#             "iniciar_finalizacion": "calcular_recomendacion_economia_modo1",
#             "buscar_coches_finales": "buscar_coches_finales",
#         }
#     )
# # --- NUEVA ETAPA 0: CÓDIGO POSTAL ---
#     # El router ya puede dirigir a recopilar_cp.
#     # Si es el primerísimo turno, llm_cp_extractor en recopilar_cp hará la pregunta inicial.
#     workflow.add_edge("recopilar_cp", "validar_cp")
#     workflow.add_conditional_edges("validar_cp", ruta_decision_cp, # Nueva función condicional
#         { "repreguntar_cp": "preguntar_cp_inicial", "buscar_clima": "buscar_info_clima"})
#     workflow.add_edge("preguntar_cp_inicial", END) 
#     # Después de buscar clima (o si se omitió CP), va al inicio de la etapa de Perfil
#     workflow.add_edge("buscar_info_clima", "recopilar_preferencias") 
    
# # Etapa 1: Perfil -> Pasajeros
#     workflow.add_edge("recopilar_preferencias", "validar_preferencias")
#     workflow.add_conditional_edges("validar_preferencias",ruta_decision_perfil, 
#         {  "necesita_pregunta_perfil": "preguntar_preferencias", 
#             "pasar_a_pasajeros": "recopilar_info_pasajeros" # <-- CORRECTO: Va a pasajeros
#         })
#     workflow.add_edge("preguntar_preferencias", END) 

#     # Etapa 1.5: Pasajeros -> Filtros
#     workflow.add_edge("recopilar_info_pasajeros", "validar_info_pasajeros")
#     workflow.add_conditional_edges("validar_info_pasajeros", ruta_decision_pasajeros,
#         {
#             "necesita_pregunta_pasajero": "preguntar_info_pasajeros",
#             "aplicar_filtros": "aplicar_filtros_pasajeros" 
#         }
#     )
#     workflow.add_edge("preguntar_info_pasajeros", END) 
#     workflow.add_edge("aplicar_filtros_pasajeros", "inferir_filtros") # <-- CORRECTO: Va a Etapa 2 (Filtros)

#     # Etapa 2: Filtros Técnicos -> Economía
#     workflow.add_edge("inferir_filtros", "recopilar_economia")
 
#     # Etapa 3: Economía -> Finalizar
#     workflow.add_edge("recopilar_economia", "validar_economia")
#     workflow.add_conditional_edges("validar_economia",ruta_decision_economia, 
#         {
#             "necesita_pregunta_economia": "preguntar_economia", # Usa el nodo genérico
#              "iniciar_finalizacion": "calcular_recomendacion_economia_modo1" 
#         }
#     )
#     workflow.add_edge("preguntar_economia", END) 
#     workflow.add_edge("calcular_recomendacion_economia_modo1", "calcular_km_anuales_postprocessing")
#     workflow.add_edge("calcular_km_anuales_postprocessing", "calcular_flags_dinamicos")
#     workflow.add_edge("calcular_flags_dinamicos", "calcular_pesos_finales")
#     workflow.add_edge("calcular_pesos_finales", "formatear_tabla_resumen")
#     #workflow.add_edge("formatear_tabla_resumen", 'buscar_coches_finales') # <-- Termina el turno para mostrar la tabla
#     workflow.add_edge("formatear_tabla_resumen", "buscar_coches_finales") 
    
#     # Etapa 5: Finalización y Búsqueda
#     workflow.add_edge("buscar_coches_finales", END) 

#     # 4. Compilar
#     print("INFO ► Compilando el grafo...")
#     graph = workflow.compile(checkpointer=get_memory())
#     print("INFO ► Grafo compilado exitosamente.")
#     return graph


def build_sequential_agent_graph(): 
    workflow = StateGraph(EstadoAnalisisPerfil)

    # --- 1. Añadir todos los nodos ---
    # (Tu lista de nodos es correcta, la mantenemos)
    workflow.add_node("router", route_based_on_state_node)
    workflow.add_node("recopilar_cp", recopilar_cp_node)
    workflow.add_node("validar_cp", validar_cp_node)
    workflow.add_node("buscar_info_clima", buscar_info_clima_node)
    workflow.add_node("preguntar_cp_inicial", preguntar_cp_inicial_node)
    
    workflow.add_node("recopilar_preferencias", recopilar_preferencias_node)
    workflow.add_node("validar_preferencias", validar_preferencias_node)
    workflow.add_node("preguntar_preferencias", preguntar_preferencias_node)
    
    workflow.add_node("recopilar_info_pasajeros", recopilar_info_pasajeros_node)
    workflow.add_node("validar_info_pasajeros", validar_info_pasajeros_node)
    workflow.add_node("preguntar_info_pasajeros", preguntar_info_pasajeros_node)
    
    # ✅ SUGERENCIA: Renombrar "inferir_filtros" a "construir_filtros" para mayor claridad
    workflow.add_node("construir_filtros", construir_filtros_node)
    workflow.add_node("aplicar_filtros_pasajeros", aplicar_filtros_pasajeros_node)
    
    workflow.add_node("recopilar_economia", recopilar_economia_node)
    workflow.add_node("validar_economia", validar_economia_node)
    workflow.add_node("preguntar_economia", preguntar_economia_node)
    
    workflow.add_node("calcular_recomendacion_economia_modo1", calcular_recomendacion_economia_modo1_node)
    workflow.add_node("calcular_km_anuales_postprocessing", calcular_km_anuales_postprocessing_node)
    workflow.add_node("calcular_flags_dinamicos", calcular_flags_dinamicos_node)
    workflow.add_node("calcular_pesos_finales", calcular_pesos_finales_node)
    workflow.add_node("formatear_tabla_resumen", formatear_tabla_resumen_node)
    workflow.add_node("buscar_coches_finales", buscar_coches_finales_node)

    # --- 2. Definir el punto de entrada y el router principal ---
    workflow.set_entry_point("router")

    workflow.add_conditional_edges(
        "router",
        decidir_ruta_inicial,
        {
            # El router ahora dirige a CADA etapa
            "recopilar_cp": "recopilar_cp",
            "recopilar_preferencias": "recopilar_preferencias", 
            "recopilar_info_pasajeros": "recopilar_info_pasajeros",
            "recopilar_economia": "recopilar_economia", 
            # ✅ La finalización ahora es una cadena que empieza en un solo punto
            "iniciar_finalizacion": "calcular_recomendacion_economia_modo1",
            "buscar_coches_finales": "buscar_coches_finales" 
        }
    )

    # --- 3. Conectar las aristas de cada flujo ---

    # Flujo de Código Postal
    workflow.add_edge("recopilar_cp", "validar_cp")
    workflow.add_conditional_edges("validar_cp", ruta_decision_cp, {
        "repreguntar_cp": "preguntar_cp_inicial",
        "buscar_clima": "buscar_info_clima"
    })
    workflow.add_edge("preguntar_cp_inicial", END)
    # ✅ CORREGIDO: Después de buscar clima, SIEMPRE volvemos al router
    workflow.add_edge("buscar_info_clima", "router") 
    
    # Flujo de Perfil
    workflow.add_edge("recopilar_preferencias", "validar_preferencias")
    workflow.add_conditional_edges("validar_preferencias", ruta_decision_perfil, {
        "necesita_pregunta_perfil": "preguntar_preferencias",
        # ✅ CORREGIDO: Si el perfil está completo, volvemos al router para que decida el siguiente paso
        "pasar_a_pasajeros": "recopilar_info_pasajeros"
    })
    workflow.add_edge("preguntar_preferencias", END) 

    # Flujo de Pasajeros
    workflow.add_edge("recopilar_info_pasajeros", "validar_info_pasajeros")
    workflow.add_conditional_edges("validar_info_pasajeros", ruta_decision_pasajeros, {
        "necesita_pregunta_pasajero": "preguntar_info_pasajeros",
        # ✅ CORREGIDO: Después de aplicar los filtros de pasajeros, volvemos al router
        "aplicar_filtros": "aplicar_filtros_pasajeros"
    })
    workflow.add_edge("preguntar_info_pasajeros", END)
    workflow.add_edge("aplicar_filtros_pasajeros", "router")

    # Flujo de Economía
    workflow.add_edge("recopilar_economia", "validar_economia")
    workflow.add_conditional_edges("validar_economia", ruta_decision_economia, {
        "necesita_pregunta_economia": "preguntar_economia",
        # ✅ CORREGIDO: La decisión de iniciar la finalización la toma el router principal
        "iniciar_finalizacion": "calcular_recomendacion_economia_modo1"  
    })
    workflow.add_edge("preguntar_economia", END) 
    
    # Flujo de Finalización (Cadena de cálculo silencioso)
    # Esta es la única parte que es una cadena lineal, ya que un cálculo depende del anterior.
    workflow.add_edge("calcular_recomendacion_economia_modo1", "construir_filtros") # ✅ Renombrado
    workflow.add_edge("construir_filtros", "calcular_km_anuales_postprocessing")
    workflow.add_edge("calcular_km_anuales_postprocessing", "calcular_flags_dinamicos")
    workflow.add_edge("calcular_flags_dinamicos", "calcular_pesos_finales")
    workflow.add_edge("calcular_pesos_finales", "formatear_tabla_resumen")
    workflow.add_edge("formatear_tabla_resumen", "buscar_coches_finales") 
    workflow.add_edge("buscar_coches_finales", END) 

    # --- 4. Compilar el Grafo ---
    logging.info("Compilando el grafo...")
    graph = workflow.compile(checkpointer=get_memory())
    logging.info("Grafo compilado exitosamente.")
    return graph