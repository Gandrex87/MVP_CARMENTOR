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


# --- RANGOS MIN-MAX PARA ESCALADO EN BIGQUERY (`utils/bigquery_tools.py`) ---
# Mapeo de nombres de campo de rating a texto amigable para el usuario para node Etapa 1
MAPA_RATING_A_PREGUNTA_AMIGABLE = {
    "rating_fiabilidad_durabilidad": "la Fiabilidad y Durabilidad",
    "rating_seguridad": "la Seguridad",
    "rating_comodidad": "la Comodidad",
    "rating_impacto_ambiental": "el Bajo Impacto Medioambiental",
    "rating_costes_uso": "los Costes de Uso y Mantenimiento",
    "rating_tecnologia_conectividad": "la Tecnología y Conectividad"
}

# Lógica Distintivo Ambiental (Específica ZBE - activada si CP está en ZBE)
BONUS_ZBE_DISTINTIVO_FAVORABLE = 0.10 # # (CERO, 0, ECO, C)
PENALTY_ZBE_DISTINTIVO_DESFAVORABLE = -0.10 #  (B, NA)

# Lógica Distintivo Ambiental (General - activada por alto rating de impacto ambiental)
BONUS_DISTINTIVO_ECO_CERO_C = 0.06 
PENALTY_DISTINTIVO_NA_B = -0.10

BONUS_OCASION_POR_IMPACTO_AMBIENTAL = 0.10 


#Valores Pesos basado en 'priorizar_ancho' (priorizar_ancho de pasajeros Z>=2)
PESO_CRUDO_BASE_ANCHO_GRAL = 1.0
PESO_CRUDO_FAV_ANCHO = 5.0

# Ajustes de pesos crudos aditivos por clima
AJUSTE_CRUDO_SEGURIDAD_POR_NIEBLA = 2.0 # Cuánto sumar al peso crudo de seguridad si hay niebla
AJUSTE_CRUDO_TRACCION_POR_NIEVE = 5.0 # Cuánto sumar al peso crudo de tracción si hay nieve
AJUSTE_CRUDO_TRACCION_POR_MONTA = 2.0 # Cuánto sumar al peso crudo de tracción si es clima de montaña

# Definir aquí los rangos mínimos y máximos para cada característica/Valores de bd
MIN_MAX_RANGES = {
    "estetica": (1.0, 10.0),"premium": (1.0, 10.0),"singular": (1.0, 10.0),
    "altura_libre_suelo": (79.0, 314.0), "batalla": (1650.0, 4035.0),        
    "indice_altura_interior": (0.9, 2.7), "ancho": (1410.0, 2164.0),
    "fiabilidad": (1.0, 10.0), "durabilidad": (1.0, 10.0), 
    "seguridad": (1.0, 10.0),  "comodidad": (1.0, 10.0),  
    "tecnologia": (1.0, 10.0), "acceso_low_cost": (1.0, 10.0), 
    "deportividad": (1.0, 10.0),"devaluacion": (0.0, 10.0), 
    "maletero_minimo": (11.0, 15000.0), # Litros 
    "maletero_maximo": (11.0, 15000.0), # Litros
    "largo": (2450.0, 6400.0), # mm, 
    "autonomia_uso_maxima": (30.8, 1582.4), # 
    "peso": (470.0, 3500.0), 
    "indice_consumo_energia": (7.4, 133.0),
    "costes_de_uso": (3.0, 31.0), 
    "costes_mantenimiento": (1.0, 10.0) ,
    "par": (41.0, 967.0), 
    "capacidad_remolque_con_freno": (100.0, 3600.0), 
    "capacidad_remolque_sin_freno": (35.0, 1250.0), 
    "superficie_planta": (2.9, 14.0), # m^2, ej: (largo_min * ancho_min)/10^6
    "diametro_giro": (7.0, 15.6),     # metros
    "alto_vehiculo": (1052.0, 2940.0),  # mm, para la altura total del vehículo
    "relacion_peso_potencia": (1.8, 28.3), # kg/CV, un valor menor es mejor, por lo que el escalado debe ser invertido. 
    "potencia_maxima": (41.0, 789.0),    # CV, más es mejor
    "aceleracion_0_100": (2.5, 34.0)     # segundos, un valor menor es mejor, por lo que el escalado debe ser invertido.
}

# --- VALORES DE AJUSTE DIRECTO AL SCORE (BONUS/PENALIZACIONES) (`utils/bigquery_tools.py`) ---
# Estos son valores absolutos que se suman/restan al score final.
# Ajusta su magnitud para controlar su impacto relativo al score ponderado.
# Escala sugerida para estos ajustes: -0.2 a +0.2 para no dominar completamente un score que tiende a 0-1.

# Penalización por Puertas
PENALTY_PUERTAS_BAJAS = -0.10

# Penalizaciones por Comodidad (si comodidad es alta, penalizar estos)
PENALTY_LOW_COST_POR_COMODIDAD = -0.10 # Cuánto restar si es muy low-cost y se quiere confort
PENALTY_DEPORTIVIDAD_POR_COMODIDAD = -0.10 # Cuánto restar si es muy deportivo y se quiere confort
UMBRAL_LOW_COST_PENALIZABLE_SCALED = 0.5 # Penalizar si acceso_low_cost_scaled >= 0.5  # Sobre valor escalado (0-1)
UMBRAL_DEPORTIVIDAD_PENALIZABLE_SCALED = 0.5 # Penalizar si deportividad_scaled >= 0.5  # Sobre valor escalado (0-1)

# Penalización por Antigüedad (si tecnología es alta)
PENALTY_ANTIGUEDAD_MAS_10_ANOS = -0.25
PENALTY_ANTIGUEDAD_7_A_10_ANOS = -0.15
PENALTY_ANTIGUEDAD_5_A_7_ANOS  = -0.07


# --- UMBRALES PARA ACTIVAR FLAGS EN PYTHON (`graph/perfil/nodes.py` - `finalizar_y_presentar_node`) ---
# Ratings de usuario (0-10)
UMBRAL_COMODIDAD_PARA_PENALIZAR_FLAGS = 7 
UMBRAL_TECNOLOGIA_PARA_PENALIZAR_ANTIGUEDAD_FLAG = 7 
UMBRAL_IMPACTO_AMBIENTAL_PARA_LOGICA_DISTINTIVO_FLAG = 8

# --- LÓGICA DE PESOS CRUDOS (`utils/weights.py`) ---
# Límite máximo para cualquier peso crudo individual antes de normalizar
MAX_SINGLE_RAW_WEIGHT = 10.0 # Definir el tope máximo para un peso crudo individual
MIN_SINGLE_RAW_WEIGHT = 0.0 # Definir el tope minimo

# Aventura
AVENTURA_RAW_WEIGHTS = {
  "ninguna":   {"altura_libre_suelo":  0,   "traccion":  0,  "reductoras":  0},
  "ocasional": {"altura_libre_suelo":  5,   "traccion":  3,  "reductoras":  1},
  "extrema":   {"altura_libre_suelo":  7,   "traccion": 7,  "reductoras":  8}}

# Valores de Pesos basados en altura_mayor_190 en Wights.py
PESO_CRUDO_BASE_BATALLA_ALTURA_MAYOR_190 = 1.0
PESO_CRUDO_FAV_BATALLA_ALTURA_MAYOR_190 = 5.0
PESO_CRUDO_FAV_IND_ALTURA_INT_ALTURA_MAYOR_190 = 8.0


#Valores Pesos basado en prioriza_baja_depreciacion
PESO_CRUDO_BASE_DEVALUACION = 1.0
PESO_CRUDO_FAV_DEVALUACION = 10.0

# Valores pesos de carga y espacio en weights.py
PESO_CRUDO_BASE_MALETERO= 1.0
PESO_CRUDO_FAV_MALETERO_MIN = 8.0
PESO_CRUDO_FAV_MALETERO_MAX = 6.0
PESO_CRUDO_FAV_MALETERO_ESP_OBJ_ESPECIALES = 7.0

# Umbrales para activar pesos específicos de impacto/costes en compute_raw_weights
UMBRAL_RATING_IMPACTO_PARA_FAV_PESO_CONSUMO = 7
UMBRAL_RATING_COSTES_USO_PARA_FAV_CONSUMO_COSTES = 7
UMBRAL_RATING_COMODIDAD_PARA_FAVORECER = 8

# Valores de peso crudo a sumar si se cumplen umbrales de ratings
RAW_PESO_BASE_AUT_VEHI = 0.5
RAW_WEIGHT_ADICIONAL_FAV_IND_ALTURA_INT_POR_COMODIDAD = 4.0
RAW_WEIGHT_ADICIONAL_FAV_AUTONOMIA_VEHI_POR_COMODIDAD = 5.0
RAW_PESO_BASE_COSTE_USO_DIRECTO = 0.5
RAW_PESO_BASE_COSTE_MANTENIMIENTO_DIRECTO = 0.5
RAW_WEIGHT_ADICIONAL_FAV_BAJO_PESO_POR_IMPACTO = 10.0
RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_IMPACTO = 7.0
RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_COSTES = 6.0 
RAW_WEIGHT_FAV_BAJO_COSTE_USO_DIRECTO = 7.0
RAW_WEIGHT_FAV_BAJO_COSTE_MANTENIMIENTO_DIRECTO = 7.0

# --- Reglas para estetica_min, premium_min, singular_min postprocessing.py ---
PESO_CRUDO_FAV_ESTETICA = 8.0
PESO_CRUDO_FAV_PREMIUM= 8.0
PESO_CRUDO_FAV_SINGULAR= 4.0
PESO_CRUDO_BASE_ESTETICA= 1.0
PESO_CRUDO_BASE_PREMIUM= 1.0
PESO_CRUDO_BASE_SINGULAR= 1.0


# Pesos crudos para preferencias de garaje/aparcamiento
PESO_CRUDO_FAV_MENOR_SUPERFICIE = 3.0 # fav_menor_superficie_planta
PESO_CRUDO_FAV_MENOR_DIAMETRO_GIRO = 5.0 #fav_menor_diametro_giro
PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE = 8.0 # Para largo, ancho, alto problemáticos
PESO_CRUDO_BASE_BAJO_DIMENSIONES_GARAJE = 0.5 # Peso si no es una preocupación explícita

# Pesos crudos para Estilo de Conducción
# Si estilo es DEPORTIVO
RAW_PESO_DEPORTIVIDAD_ALTO = 4.0
RAW_PESO_MENOR_REL_PESO_POTENCIA_ALTO = 10.0
RAW_PESO_POTENCIA_MAXIMA_ALTO = 5.0
RAW_PESO_PAR_MOTOR_DEPORTIVO_ALTO = 4.0
RAW_PESO_MENOR_ACELERACION_ALTO = 6.0
# Si estilo es MIXTO
RAW_PESO_DEPORTIVIDAD_MEDIO = 2.0
RAW_PESO_MENOR_REL_PESO_POTENCIA_MEDIO = 5.0
RAW_PESO_POTENCIA_MAXIMA_MEDIO = 2.5
RAW_PESO_PAR_MOTOR_DEPORTIVO_MEDIO = 2.0
RAW_PESO_MENOR_ACELERACION_MEDIO = 3.0
# Si estilo es TRANQUILO o no definido (base)
RAW_PESO_DEPORTIVIDAD_BAJO = 1.0
RAW_PESO_MENOR_REL_PESO_POTENCIA_BAJO = 1.0
RAW_PESO_POTENCIA_MAXIMA_BAJO = 1.0
RAW_PESO_PAR_MOTOR_DEPORTIVO_BAJO = 1.0
RAW_PESO_MENOR_ACELERACION_BAJO = 1.0

# Pesos crudos para arrastre de remolque si es 'sí' weights.py
RAW_PESO_PAR_MOTOR_REMOLQUE = 6.0
RAW_PESO_CAP_REMOLQUE_CF = 7.0
RAW_PESO_CAP_REMOLQUE_SF = 3.0
# Pesos crudos base para remolque si es 'no' o None
RAW_PESO_BASE_REMOLQUE = 1.0

# --- SINÓNIMOS PARA RAG (`utils/rag_carroceria.py`) ---
# Renombrados para evitar colisión con AVENTURA_RAW_WEIGHTS si las claves fueran idénticas

UMBRAL_RATING_COMODIDAD_RAG = 8.0 # Umbral de rating de comodidad para activar sinónimos RAG

# Mapa de sinónimos por nivel de aventura
AVENTURA_SYNONYMS_RAG = {
    "ninguna":   ["ciudad", "asfalto", "uso diario", "practicidad", "maniobrable"],
    "ocasional": ["campo", "ligero fuera de asfalto", "excursiones", "versátil"],
    "extrema":   ["off-road", "terrenos difíciles","tracción 4x4", "gran altura libre", "reductoras"]}

# Tags del PDF relevantes: "Transporte de objetos especiales", "logística", "entregas", "comercio", "servicio técnico", "carga pesada"
USO_PROF_CARGA_SYNONYMS_RAG = ["transporte de mercancías", "logística", "furgón" ]

USO_PROF_PASAJEROS_SYNONYMS_RAG = ["transporte personas", "rutas de personal", "muchos asientos"]

# Tags del PDF relevantes: FURGONETA (intrínsecamente mixto), PICKUP (doble cabina), SUV, FAMILIAR.
USO_PROF_MIXTO_SYNONYMS_RAG = [
    "uso mixto profesional", "vehículo combi", "transporte equipo y personal", "trabajo y familia adaptable", "doble cabina" ]

# Si valora_estetica == "sí"
ESTETICA_VALORADA_SYNONYMS_RAG = [ "diseño", "elegancia", "llamar atención" ]

# Si num_ninos_silla > 0 o muchos pasajeros
ESPACIO_PASAJEROS_NINOS_SYNONYMS_RAG = [ "espacio sillas infantiles", "modularidad asientos"]

# Si apasionado_motor == "sí"
APASIONADO_MOTOR_SYNONYMS_RAG = [ "conducción emocionante", "singular", "ágil en curvas"]

# Podrías incluso tener para SOLO_ELECTRICOS, aunque "eléctrico" es bastante directo
SOLO_ELECTRICOS_SYNONYMS_RAG = ["cero emisiones", "sostenible", "bajo consumo energético"]
ALTA_COMODIDAD_CARROCERIA_SYNONYMS_RAG = ["comodidad y confort","derivado de 2VOL o 3VOL", "monovolumen espacioso"]
NECESITA_ESPACIO_OBJETOS_ESPECIALES_SYNONYMS_RAG = ["maletero amplio", "portón trasero grande", "modularidad"]
CLIMA_MONTA_CARROCERIA_SYNONYMS_RAG = ["todoterreno", "SUV robusto"]

#graph/nodes.py
#funcion calcular_flags_dinamicos_node
UMBRAL_COMODIDAD_PARA_PENALIZAR_FLAGS = 7
UMBRAL_TECNOLOGIA_PARA_PENALIZAR_ANTIGUEDAD_FLAG = 7
UMBRAL_IMPACTO_AMBIENTAL_PARA_LOGICA_DISTINTIVO_FLAG = 8