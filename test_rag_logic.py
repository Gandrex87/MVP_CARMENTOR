import os
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import vertexai

# --- 1. IMPORTA TUS MODELOS PYDANTIC ---
# Asegúrate de que la ruta de importación sea correcta según la estructura de tu proyecto.
# Puede que necesites añadir `utils` o `models` al path si es necesario.
from graph.perfil.state import (
    PerfilUsuario, InfoPasajeros, InfoClimaUsuario, FiltrosInferidos
)
from utils.enums import(TipoUsoProfesional, NivelAventura)
from utils.conversion import is_yes
from utils.rag_carroceria import get_recommended_carrocerias, get_vectorstore
# --- 2. CASOS DE PRUEBA CON OBJETOS PYDANTIC ---
# Cada 'inputs' ahora contiene instancias reales de tus clases, como en tu agente.

casos_de_prueba = [
    {
        "nombre": "Prueba 1: Familia numerosa que necesita 6 plazas",
        "inputs": {
            "preferencias": PerfilUsuario(), # Perfil base
            "info_pasajeros": InfoPasajeros(num_otros_pasajeros=5 , suele_llevar_acompanantes= True , frecuencia_viaje_con_acompanantes = 'frecuente'), # 5 pasajeros + conductor = 6
            "info_clima": None,
            "filtros_inferidos": FiltrosInferidos(plazas_min=6) # El filtro clave
        },
        "resultado_esperado": ['FAMILIAR', 'MONOVOLUMEN', 'FURGONETA', 'SUV']
    },
    {
        "nombre": "Prueba 2: Conduce caminos fuera del asfalto y lleva carga objetos grandes",
        "inputs": {
            "preferencias": PerfilUsuario(aventura=NivelAventura.extrema , transporta_carga_voluminosa = "sí" , necesita_espacio_objetos_especiales = "sí"),
            "info_pasajeros": None,
            "info_clima": InfoClimaUsuario(ZONA_CLIMA_MONTA=True, ZONA_NIEVE=True),
            "filtros_inferidos": None
        },#autocaravana no fuera del asfalto -  FALTA TODOTERRENO / SI ES TERRENOS  DIFICLES DEBERIA   DESCARTAR FAMILIAR
        "resultado_esperado": ["TODOTERRENO", "PICKUP" ,"SUV", 'FURGONETA' ]
    },
    {
        "nombre": "Prueba 3: Ejecutivo que valora estética y confort",
        "inputs": {
            "preferencias": PerfilUsuario(prefiere_diseno_exclusivo = "sí" ,valora_estetica="sí", rating_comodidad=8 , transporta_carga_voluminosa = "no" ),
            "info_pasajeros": InfoPasajeros(suele_llevar_acompanantes=True ,composicion_pasajeros_texto = "un adulto" ),
            "info_clima": None,
            "filtros_inferidos": None
        },
        "resultado_esperado": ["COUPE", "DESCAPOTABLE", "3VOL"] #podrian estar todas si
    },
    {
        "nombre": "Prueba 4: Usuario Eco-Práctico (La prueba original)",
        "inputs": {
            "preferencias": PerfilUsuario(
                aventura=NivelAventura.ninguna,
                rating_impacto_ambiental=9,
                rating_costes_uso=9
            ),
            "info_pasajeros": None,
            "info_clima": None,
            "filtros_inferidos": None
        },
        "resultado_esperado": ["2VOL", "FAMILIAR", "SUV" , "3VOL" "COUPE", "DESCAPOTABLE" , "FURGONETA" , "AUTOCARAVANA", "MONOVOLUMEN"] # 
    },
    {
        "nombre": "Prueba 5: Usuario que arrastra remolque y deportivo",
        "inputs": {
            "preferencias": PerfilUsuario(prefiere_diseno_exclusivo = "sí" ,valora_estetica="sí", arrastra_remolque="sí", estilo_conduccion = 'deportivo' ,necesita_espacio_objetos_especiales = "no" ),
            "info_pasajeros": None,
            "info_clima": None,
            "filtros_inferidos": None
        },
        "resultado_esperado": ["PICKUP", "TODOTERRENO", "SUV" ,"2VOL", "FAMILIAR", "SUV" , "3VOL" "COUPE", "DESCAPOTABLE" , "FURGONETA" , "AUTOCARAVANA" , "MONOVOLUMEN"]
    },
#     {
#         "nombre": "Prueba 6: Uso profesional para reparto en ciudad",
#         "inputs": {
#             "preferencias": PerfilUsuario(uso_profesional="sí", tipo_uso_profesional=TipoUsoProfesional.CARGA),
#             "info_pasajeros": None,
#             "info_clima": None,
#             "filtros_inferidos": None
#         },
#         "resultado_esperado": [' FURGONETA','COMERCIAL', 'PICKUP']
#     },
#     # --- ¡NUEVO CASO DE PRUEBA AÑADIDO! ---
#     {
#         "nombre": "Prueba 7: El Urbanita Eficiente",
#         "inputs": {
#             "preferencias": PerfilUsuario(
#                 aventura=NivelAventura.ninguna,
#                 coche_principal_hogar="sí",
#                 rating_impacto_ambiental=9,
#                 rating_costes_uso=9,
#                 rating_comodidad=6
#             ),
#             "info_pasajeros": InfoPasajeros(suele_llevar_acompanantes=False),
#             "info_clima": InfoClimaUsuario(MUNICIPIO_ZBE=True, ZONA_GLP=True),
#             "filtros_inferidos": FiltrosInferidos(
#                 estetica_min=1.0,
#                 premium_min=1.0,
#                 singular_min=2.0
#             )
#         },
#         # Esperamos que los coches más eficientes y prácticos para la ciudad sean los primeros.
#         "resultado_esperado": ["2VOL", "FAMILIAR", "COMERCIAL", "SUV"]
#     },
#     {
#     "nombre": "Prueba 8: El Urbanita 100% Eléctrico",
#     "inputs": {
#         "preferencias": PerfilUsuario(
#             # Restricciones y preferencias clave
#             solo_electricos='sí',
#             aventura=NivelAventura.ninguna,
#             coche_principal_hogar="sí",
            
#             # Ratings que refuerzan la elección de un eléctrico
#             rating_impacto_ambiental=10,
#             rating_costes_uso=8,
#             rating_tecnologia_conectividad=7
#         ),
#         "info_pasajeros": InfoPasajeros(suele_llevar_acompanantes=False),
#         "info_clima": InfoClimaUsuario(MUNICIPIO_ZBE=True), # Refuerza el contexto urbano
#         "filtros_inferidos": None
#     },
#     # Esperamos que las opciones no eléctricas o poco eficientes sean descartadas
#     # o reciban una puntuación muy baja en el re-ranking.
#     "resultado_esperado": ["2VOL", "FAMILIAR" , "SUV"]
# },
#     {
#     "nombre": "Prueba 9: El Viajero que Prioriza Confort y Espacio",
#     "inputs": {
#         "preferencias": PerfilUsuario(
#             # La clave del test: máxima puntuación en comodidad
#             rating_comodidad=10,
            
#             # Reforzamos la necesidad de espacio si/no
#             transporta_carga_voluminosa="no", 
#             coche_principal_hogar="sí",
            
#             # Indicamos que el uso principal es en carretera, no en terrenos difíciles
#             aventura=NivelAventura.ninguna
#         ),
#         # Simulamos que a menudo viaja con adultos, lo que requiere espacio y confort
#         "info_pasajeros": InfoPasajeros(
#             suele_llevar_acompanantes=True,
#             frecuencia_viaje_con_acompanantes="frecuente",
#             composicion_pasajeros_texto="suelo llevar a mis padres o amigos"
#         ),
#         "info_clima": None,
#         "filtros_inferidos": None
#     },
    # Esperamos que las carrocerías diseñadas para el confort en carretera y el espacio
    # sean las mejor puntuadas. El orden puede variar, pero estas tres deben ser las finalistas.
    #"resultado_esperado": ["MONOVOLUMEN", "3VOL", "FAMILIAR","FURGONETA"]
#},
{
    "nombre": "Prueba 10: El Entusiasta del Diseño y la Conducción",
    "inputs": {
        "preferencias": PerfilUsuario(
            # Las dos únicas y claras prioridades del usuario
            apasionado_motor='sí',
            valora_estetica='sí',
            
            # El resto de preferencias son neutras o negativas
            uso_profesional='no',
            transporta_carga_voluminosa='no',
            aventura=NivelAventura.ninguna,
            rating_comodidad=5, # Rating neutro
            rating_costes_uso=3, # Rating bajo, refuerza el desinterés por lo práctico
            rating_impacto_ambiental=2 # Rating bajo
        ),
        "info_pasajeros": InfoPasajeros(suele_llevar_acompanantes=False),
        "info_clima": None,
        "filtros_inferidos": None
    },
    
    
    
    
    # Esperamos que las carrocerías deportivas y con estilo dominen el ranking.
    "resultado_esperado": ["COUPE", "DESCAPOTABLE", "3VOL (Tres volúmenes)"]
}

]

def ejecutar_pruebas():
    """
    Función principal que corre todos los casos de prueba definidos.
    """
    print("--- INICIANDO SET DE PRUEBAS ROBUSTAS DEL SISTEMA RAG ---")
    
    print("Cargando Vector Store...")
    get_vectorstore()
    print("Vector Store listo.\n")
    
    pruebas_pasadas = 0
    
    for i, test in enumerate(casos_de_prueba):
        print(f"▶️ Ejecutando Caso de Prueba #{i+1}: {test['nombre']}")
        
        inputs = test["inputs"]
        
        # --- 3. LLAMADA A LA FUNCIÓN ALINEADA CON LA FIRMA FINAL ---
        resultado_obtenido = get_recommended_carrocerias(
            preferencias=inputs["preferencias"],
            info_pasajeros=inputs.get("info_pasajeros"),
            info_clima=inputs.get("info_clima"),
            filtros_inferidos=inputs.get("filtros_inferidos"), # Añadimos el nuevo argumento
            k=len(test["resultado_esperado"])
        )
        
        # --- 4. VALIDACIÓN ESTRICTA (ORDEN Y CONTENIDO) ---
        # Comparamos las listas directamente para asegurar que el orden es el esperado.
        if resultado_obtenido == test["resultado_esperado"]:
            print(f"  ✅ Pasa. Resultado: {resultado_obtenido}")
            pruebas_pasadas += 1
        else:
            print(f"  ❌ FALLA.")
            print(f"     -> Esperado: {test['resultado_esperado']}")
            print(f"     -> Obtenido: {resultado_obtenido}")
        print("-" * 40)

    print("\n--- RESUMEN DE PRUEBAS ---")
    print(f"Total de pruebas: {len(casos_de_prueba)}")
    print(f"Pruebas pasadas: {pruebas_pasadas}")
    print(f"Pruebas fallidas: {len(casos_de_prueba) - pruebas_pasadas}")
    print("--------------------------")

if __name__ == "__main__":
    load_dotenv()
    
    # Inicialización de Vertex AI (importante para las llamadas a Gemini)
    try:
        PROJECT_ID = "thecarmentor-mvp2" # Asegúrate de que sea tu ID de proyecto
        LOCATION = "us-central1"
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        logging.info(f"Vertex AI inicializado para el proyecto {PROJECT_ID} en {LOCATION}")
    except Exception as e:
        logging.warning(f"Vertex AI ya podría estar inicializado o falló la inicialización: {e}")
        
    ejecutar_pruebas()