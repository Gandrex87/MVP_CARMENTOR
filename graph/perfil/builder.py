# graph/builder.py

from langgraph.graph import StateGraph, START, END
from graph.perfil.state import EstadoAnalisisPerfil # Ajusta la ruta si es necesario
from graph.perfil.nodes import ( saludo_y_pregunta_inicial_node, recopilar_cp_node,  buscar_info_clima_node, validar_y_decidir_cp_node, preguntar_cp_node,
    recopilar_preferencias_node, generar_mensaje_transicion_perfil, construir_filtros_node,recopilar_economia_node, preguntar_economia_node,
    preguntar_preferencias_node, preguntar_economia_node,buscar_coches_finales_node, generar_mensaje_transicion_pasajeros,
    recopilar_info_pasajeros_node, preguntar_info_pasajeros_node,aplicar_filtros_pasajeros_node, calcular_recomendacion_economia_modo1_node,
    calcular_flags_dinamicos_node,calcular_pesos_finales_node,formatear_tabla_resumen_node, calcular_km_anuales_postprocessing_node)
from graph.perfil.memory import get_memory 
from graph.perfil.condition import (ruta_decision_cp_refactorizada, decidir_siguiente_paso_economia, decidir_siguiente_paso_perfil, decidir_siguiente_paso_pasajeros, 
                                    decidir_ruta_inicial, route_based_on_state_node)
import logging


def build_sequential_agent_graph(): 
    workflow = StateGraph(EstadoAnalisisPerfil)

    # --- 1. Añadir todos los nodos ---
    workflow.add_node("saludo_y_pregunta_inicial", saludo_y_pregunta_inicial_node)
    # (Tu lista de nodos es correcta, la mantenemos) 
    workflow.add_node("router", route_based_on_state_node)
    workflow.add_node("recopilar_cp", recopilar_cp_node)
    workflow.add_node("validar_y_decidir_cp", validar_y_decidir_cp_node)
    workflow.add_node("preguntar_cp", preguntar_cp_node)
    workflow.add_node("buscar_info_clima", buscar_info_clima_node)

    workflow.add_node("recopilar_preferencias", recopilar_preferencias_node)
    workflow.add_node("preguntar_preferencias", preguntar_preferencias_node)
    workflow.add_node("generar_mensaje_transicion", generar_mensaje_transicion_perfil)
        
    workflow.add_node("recopilar_info_pasajeros", recopilar_info_pasajeros_node)
    workflow.add_node("preguntar_info_pasajeros", preguntar_info_pasajeros_node)
    workflow.add_node("aplicar_filtros_pasajeros", aplicar_filtros_pasajeros_node)
    workflow.add_node("generar_mensaje_transicion_pasajeros", generar_mensaje_transicion_pasajeros)
    workflow.add_node("construir_filtros", construir_filtros_node)


    workflow.add_node("recopilar_economia", recopilar_economia_node)
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
    decidir_ruta_inicial, # Tu función de enrutamiento principal
    {   "iniciar_conversacion": "saludo_y_pregunta_inicial",
        "recopilar_cp": "recopilar_cp",
        "recopilar_preferencias": "recopilar_preferencias", 
        "recopilar_info_pasajeros": "recopilar_info_pasajeros",
        "recopilar_economia": "recopilar_economia", 
        "iniciar_finalizacion": "calcular_recomendacion_economia_modo1",
        "buscar_coches_finales": "buscar_coches_finales" 
    }
)
    # Después del saludo y la primera pregunta, el agente debe esperar la respuesta del usuario.
    workflow.add_edge("saludo_y_pregunta_inicial", END)
    # --- 3. Conectar las aristas de cada flujo ---
     #Después de intentar recopilar, siempre validamos.
    workflow.add_edge("recopilar_cp", "validar_y_decidir_cp")
    # Flujo de Código Postal

    # Después de validar, la arista condicional decide el siguiente paso.
    workflow.add_conditional_edges(
        "validar_y_decidir_cp",
        ruta_decision_cp_refactorizada,
        {
            "avanzar_a_clima": "buscar_info_clima",
            "repreguntar_cp": "preguntar_cp"
        }
    )

    # Si tenemos que volver a preguntar, el turno del agente termina.
    workflow.add_edge("preguntar_cp", END)
    workflow.add_edge("buscar_info_clima", "router")  # Después de buscar el clima, la etapa termina y volvemos al router principal.
        
    # Flujo de Perfil
    workflow.add_conditional_edges(
    "recopilar_preferencias",
    decidir_siguiente_paso_perfil,
    {
        "preguntar_preferencias": "preguntar_preferencias",
        "generar_mensaje_transicion": "generar_mensaje_transicion" # <-- AÑADE ESTA LÍNEA
    }
)
    # --- 4. Conecta el nuevo nodo al siguiente paso lógico ---
    # Después de mostrar el mensaje de transición, el control debe volver al router
    # principal para que decida qué hacer a continuación (que será iniciar el
    # flujo de pasajeros).
    workflow.add_edge("generar_mensaje_transicion", "router")
    # Las demás aristas, como la que va de 'preguntar_preferencias' a END, se mantienen igual.
    workflow.add_edge("preguntar_preferencias", END)

    # Flujo de Pasajeros
    # El router principal ya dirige a "recopilar_info_pasajeros" cuando es el momento.
    # Ahora, definimos lo que pasa DESPUÉS de recopilar la información.
    workflow.add_conditional_edges(
        "recopilar_info_pasajeros",
        decidir_siguiente_paso_pasajeros,
        {
            "preguntar_info_pasajeros": "preguntar_info_pasajeros",
            "generar_mensaje_transicion_pasajeros": "generar_mensaje_transicion_pasajeros" # <-- AÑADE ESTA LÍNEA
        }
    )

    # --- 4. Conecta el nuevo nodo al siguiente paso lógico ---
    # Después de mostrar el mensaje, calculamos los filtros y luego volvemos al router.
    workflow.add_edge("generar_mensaje_transicion_pasajeros", "aplicar_filtros_pasajeros")
    workflow.add_edge("aplicar_filtros_pasajeros", "router")
    workflow.add_edge("preguntar_info_pasajeros", END)
     
    # Flujo de Economía
    workflow.add_conditional_edges(
    "recopilar_economia",
    decidir_siguiente_paso_economia, # <-- Nuestra nueva función de decisión
    {
        "preguntar_economia": "preguntar_economia",
        "iniciar_finalizacion": "calcular_recomendacion_economia_modo1" # <-- Tu nodo de finalización
    }
    )
    # Si tenemos que volver a preguntar, el turno del agente termina.
    workflow.add_edge("preguntar_economia", END)
    # El flujo de Finalización continúa como lo tenías.
    workflow.add_edge("calcular_recomendacion_economia_modo1", "construir_filtros")
    
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