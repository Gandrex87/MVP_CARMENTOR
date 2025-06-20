import os
from dotenv import load_dotenv
import logging
logging.basicConfig(level=logging.INFO)

# Carga las variables desde un archivo .env si existe (ideal para desarrollo local)
load_dotenv()

# --- Carga de todas tus variables de entorno ---
# Este método es seguro para ambos entornos. En Cloud Run, las tomará de los secretos que configuraste.
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") # Esta solo existirá localmente
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
LANGCHAIN_TRACING = os.getenv("LANGSMITH_TRACING")
LANGCHAIN_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT")
LANGCHAIN_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGSMITH_PROJECT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# --- Lógica de Autenticación Adaptativa (ESTA ES LA CORRECCIÓN) ---

# 1. Detectamos si estamos en un entorno de producción de Google Cloud (como Cloud Run)
#    buscando la variable de entorno 'K_SERVICE', que Google añade automáticamente.
IS_IN_PRODUCTION = 'K_SERVICE' in os.environ

# 2. Solo validamos las credenciales de archivo si NO estamos en producción.
if not IS_IN_PRODUCTION:
    # Estamos en un entorno local (tu Mac)
    print("Entorno local detectado. Verificando GOOGLE_APPLICATION_CREDENTIALS del archivo .env...")
    if not GOOGLE_CREDENTIALS:
        raise ValueError(
            "Ejecución local: No se encontró GOOGLE_APPLICATION_CREDENTIALS en el entorno. "
            "Asegúrate de que tu archivo .env lo defina correctamente."
        )
else:
    # Estamos en Cloud Run
    print("Entorno de Cloud Run detectado. Se usarán las credenciales automáticas de la cuenta de servicio.")
    # No hacemos nada aquí. Las librerías de Google usarán la cuenta de servicio adjunta automáticamente.
    # La variable GOOGLE_CREDENTIALS será 'None' y eso está bien en este entorno.
    pass


# --------------------------------------- ## --------------------------------------- ## ---------------------------------------
# PESOS CRUDOS:
# Son valores (a menudo en una escala conceptual 0-10 o similar) que reflejan la "importancia inicial" de una característica según las preferencias.
# Se usan solo en compute_raw_weights.
# Su resultado final (después de la normalización) son los @peso_... que se multiplican por las características escaladas (0-1) del coche.

# PENALIZACIONES Y BONIFICACIONES:
# Ajustes Directos al Score (BONUS_..., PENALTY_... en settings.py):
# Estos son valores absolutos que se suman/restan al score final.
# Escala sugerida para estos ajustes: -0.25 a +0.25 para no dominar completamente un score que tiende a 0-1.
# Se usan solo en la query SQL de buscar_coches_bq, dentro de cláusulas CASE WHEN activadas por flags.
# Modifican el score de forma aditiva después de la parte ponderada.





# --------------------------------------- ## --------------------------------------- ## ---------------------------------------
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
    "aceleracion_0_100": (2.5, 34.0),
    'autonomia_uso_principal': (21.8, 1480.6),
    'autonomia_uso_2nd_drive': (326.0, 936.4),
    'tiempo_carga_min': (18.0, 640.1),
    'potencia_maxima_carga_AC': (2.3, 22.0),
    'potencia_maxima_carga_DC': (1.0, 270.0),# segundos, un valor menor es mejor, por lo que el escalado debe ser invertido.
}
# --------------------------------------- ## --------------------------------------- ## ---------------------------------------
# --- VALORES DE AJUSTE DIRECTO AL SCORE (BONUS/PENALIZACIONES) (`utils/bigquery_tools.py`) ---

# --- LÓGICA PARA TRACCIÓN BASADA EN AVENTURA ---
PENALTY_AWD_NINGUNA_AVENTURA = -0.10
BONUS_AWD_NINGUNA_AVENTURA_CLIMA_ADVERSO = 0.10

BONUS_AWD_AVENTURA_OCASIONAL = 0.10
BONUS_AWD_AVENTURA_EXTREMA = 0.20

# --- LÓGICA PARA REDUCTORAS BASADA EN AVENTURA ---
BONUS_REDUCTORAS_AVENTURA_OCASIONAL = 0.10 # 
BONUS_REDUCTORAS_AVENTURA_EXTREMA = 0.20   # 

#valores directos que se suman o restan al score (escala 0-1)
# Penalización por Puertas
PENALTY_PUERTAS_BAJAS = -0.081

# Penalizaciones por Comodidad (si comodidad es alta, penalizar estos)
PENALTY_LOW_COST_POR_COMODIDAD = -0.10 # Cuánto restar si es muy low-cost y se quiere confort
PENALTY_DEPORTIVIDAD_POR_COMODIDAD = -0.10 # Cuánto restar si es muy deportivo y se quiere confort

# Penalización por Antigüedad (si tecnología es alta)
PENALTY_ANTIGUEDAD_MAS_10_ANOS = -0.20
PENALTY_ANTIGUEDAD_7_A_10_ANOS = -0.15
PENALTY_ANTIGUEDAD_5_A_7_ANOS  = -0.081

#valores directos que se suman o restan al score (escala 0-1)
PENALTY_BEV_REEV_AVENTURA_OCASIONAL = -0.10
PENALTY_PHEV_AVENTURA_OCASIONAL = -0.05
PENALTY_ELECTRIFICADOS_AVENTURA_EXTREMA =  -0.25 

# Lógica Distintivo Ambiental (General - activada por alto rating de impacto ambiental - WHEN @flag_aplicar_logica_distintivo = TRUE THEN)
BONUS_DISTINTIVO_ECO_CERO_C = 0.049 
PENALTY_DISTINTIVO_NA_B = -0.081 #Falta separar la nota NA para aplicar diferenciar calificacion.

#WHEN @flag_aplicar_logica_distintivo = TRUE AND COALESCE(sd.ocasion, FALSE) = TRUE THEN
BONUS_OCASION_POR_IMPACTO_AMBIENTAL = 0.081 

# Lógica Distintivo Ambiental (Específica ZBE - activada si CP está en ZBE)
BONUS_ZBE_DISTINTIVO_FAVORABLE_C = 0.081 
BONUS_ZBE_DISTINTIVO_FAVORABLE_ECO_CERO = 0.10

PENALTY_ZBE_DISTINTIVO_DESFAVORABLE_NA =  -0.20
PENALTY_ZBE_DISTINTIVO_DESFAVORABLE_B =  -0.081


# Regla 1: Si flag_favorecer_carroceria_montana es TRUE, los coches con tipo_carroceria 'SUV' o 'TODOTERRENO' reciben un bonus.
# Regla 2: Si flag_favorecer_carroceria_comercial es TRUE, los coches 'COMERCIAL' reciben un bonus.
# Regla 3: Si flag_favorecer_carroceria_pasajeros_pro es TRUE, los coches '3VOL' o 'MONOVOLUMEN' reciben un bonus.
# Regla 4: Si flag_desfavorecer_carroceria_no_aventura es TRUE, los coches 'PICKUP' o 'TODOTERRENO' reciben una penalización.
# Regla 5: si flag_fav_pickup_todoterreno_aventura_extrema es TRUE, coches 'TODOTERRENO' favorece
# Regla 6: si flag_fav_pickup_todoterreno_aventura_extrema es TRUE, coches 'PICKUP' favorece
# Regla 7: si flag_aplicar_logica_objetos_especiales = TRUE, favorecer ('MONOVOLUMEN', 'FURGONETA', 'FAMILIAR', 'SUV'), penalty ('3VOL', 'COUPE', 'DESCAPOTABLE')
# Regla 8: si flag_fav_carroceria_confort = TRUE, favorece ('3VOL', '2VOL', 'SUV', 'FAMILIAR', 'MONOVOLUMEN')
BONUS_CARROCERIA_MONTANA = 0.05
BONUS_CARROCERIA_COMERCIAL = 0.20
BONUS_CARROCERIA_PASAJEROS_PRO = 0.20
PENALTY_CARROCERIA_NO_AVENTURA = -0.15
BONUS_SUV_AVENTURA_OCASIONAL = 0.20
BONUS_TODOTERRENO_AVENTURA_EXTREMA = 0.10 
BONUS_PICKUP_AVENTURA_EXTREMA = 0.05
BONUS_CARROCERIA_OBJETOS_ESPECIALES = 0.10
PENALTY_CARROCERIA_OBJETOS_ESPECIALES = -0.20
BONUS_CARROCERIA_CONFORT = 0.081

# Lógica para FrecuenciaUso.OCASIONALMENTE
BONUS_OCASION_POR_USO_OCASIONAL = 0.081  # Puntos extra si el coche es de OCASION y el uso es ocasional
PENALTY_ELECTRIFICADOS_POR_USO_OCASIONAL = -0.10  # Puntos que se restan a BEV/PHEV/REEV si el uso es ocasional
BONUS_BEV_REEV_USO_DEFINIDO = 0.10 # Bonus para BEV/REEV si el perfil de uso es el ideal para un eléctrico puro
PENALTY_PHEV_USO_INTENSIVO_LARGO = -0.15 # Penalización para PHEVs si el uso es diario/frecuente en trayectos muy largos

# --- BONUS/PENALIZACIONES BASADOS EN KM ANUALES ESTIMADOS ---
# Rango Bajo (< 10.000 km/año)
BONUS_MOTOR_POCO_KM = 0.10 
PENALTY_OCASION_POCO_KM = -0.05  

# Rango Medio (10.000 - 30.000 km/año)
PENALTY_OCASION_MEDIO_KM = -0.10

# Rango Alto (30.000 - 60.000 km/año)
BONUS_MOTOR_MUCHO_KM = 0.10 
PENALTY_OCASION_MUCHO_KM = -0.10

# --- LÓGICA PARA USO MUY ALTO (> 60.000 km/año) ---
# Bonus por tipo de motor
BONUS_BEV_MUY_ALTO_KM = 0.05
BONUS_REEV_MUY_ALTO_KM = 0.081
BONUS_DIESEL_HEVD_MUY_ALTO_KM = 0.10
BONUS_PHEVD_GLP_GNV_MUY_ALTO_KM = 0.03

# Penalización para coches de ocasión
PENALTY_OCASION_MUY_ALTO_KM_V2 = -0.20 # Le pongo V2 para no confundir con la otra constante

# Bonus para coches que pueden aprovechar un punto de carga propio
BONUS_PUNTO_CARGA_PROPIO = 0.10

# Bonus/Penalty favorecer por conducir en ciudad
PENALTY_DIESEL_CIUDAD = -0.15
BONUS_DIESEL_CIUDAD_OCASIONAL = 0.20

# --- LÓGICA PARA TRACCIÓN AWD BASADA EN CLIMA ---
# Ajustes de pesos crudos aditivos por clima
BONUS_AWD_ZONA_NIEVE = 0.10
BONUS_AWD_ZONA_MONTA = 0.05




# --------------------------------------- ## --------------------------------------- ## ---------------------------------------
# --- UMBRALES PARA ACTIVAR FLAGS EN PYTHON (`graph/perfil/nodes.py` - `finalizar_y_presentar_node`) ---

# Umbrales para activar pesos específicos de impacto/costes en compute_raw_weights
UMBRAL_RATING_IMPACTO_PARA_FAV_PESO_CONSUMO = 8
UMBRAL_RATING_COSTES_USO_PARA_FAV_CONSUMO_COSTES = 7
UMBRAL_RATING_COMODIDAD_PARA_FAVORECER = 8
UMBRAL_RATING_COMODIDAD_RAG = 8.0 # Umbral de rating de comodidad para activar sinónimos RAG
UMBRAL_COMODIDAD_PARA_PENALIZAR_FLAGS = 7
UMBRAL_TECNOLOGIA_PARA_PENALIZAR_ANTIGUEDAD_FLAG = 7
UMBRAL_IMPACTO_AMBIENTAL_PARA_LOGICA_DISTINTIVO_FLAG = 7


UMBRAL_COMODIDAD_PARA_FAVORECER_CARROCERIA = 8

# --------------------------------------- ## --------------------------------------- ## --------------------------------------
# --- LÓGICA DE PESOS CRUDOS (`utils/weights.py`) ---
# Límite máximo para cualquier peso crudo individual antes de normalizar
MAX_SINGLE_RAW_WEIGHT = 10.0 #
MIN_SINGLE_RAW_WEIGHT = 0.0 #
PESO_CRUDO_BASE = 1.0

#Valores Pesos basado en 'priorizar_ancho' (priorizar_ancho de pasajeros Z>=2)
PESO_CRUDO_BASE_ANCHO_GRAL = 1.0
PESO_CRUDO_FAV_ANCHO_PASAJEROS_OCASIONAL = 4.0
PESO_CRUDO_FAV_ANCHO_PASAJEROS_FRECUENTE = 8.0

# --- LÓGICA PARA TRACCIÓN AWD BASADA EN CLIMA ---
# Ajustes de pesos crudos aditivos por clima
AJUSTE_CRUDO_SEGURIDAD_POR_NIEBLA = 2.0 # Cuánto sumar al peso crudo de seguridad si hay niebla







# Mapeo directo del nivel de aventura al peso crudo deseado.
altura_map = {
        "ninguna": 1.0,
        "ocasional": 4.0,
        "extrema": 10.0
    }


# Valores de Pesos basados en altura_mayor_190 en Weights.py
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
PESO_CRUDO_FAV_MALETERO_ESP_OBJ_ESPECIALES_ANCHO = 5.0 
PESO_CRUDO_FAV_MALETERO_ESP_OBJ_ESPECIALES_LARGO = 7.0


# Valores de peso crudo a sumar si se cumplen umbrales de ratings en weights.py
RAW_PESO_BASE_AUT_VEHI = 0.5
RAW_WEIGHT_ADICIONAL_FAV_IND_ALTURA_INT_POR_COMODIDAD = 6.0
RAW_WEIGHT_ADICIONAL_FAV_AUTONOMIA_VEHI_POR_COMODIDAD = 4.0
RAW_PESO_BASE_COSTE_USO_DIRECTO = 1.0
RAW_PESO_BASE_COSTE_MANTENIMIENTO_DIRECTO = 1.0
RAW_WEIGHT_ADICIONAL_FAV_BAJO_PESO_POR_IMPACTO = 10.0
RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_IMPACTO = 7.0
RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_COSTES = 5.0 
RAW_WEIGHT_FAV_BAJO_COSTE_USO_DIRECTO = 9.0
RAW_WEIGHT_FAV_BAJO_COSTE_MANTENIMIENTO_DIRECTO = 7.0


RAW_WEIGHT_ADICIONAL_FAV_BAJO_CONSUMO_POR_USO_INTENSIVO = 5.0

# --- Reglas para estetica_min, premium_min, singular_min postprocessing.py ---
PESO_CRUDO_FAV_ESTETICA = 6.0

PESO_CRUDO_FAV_PREMIUM_APASIONADO_MOTOR = 6.0
PESO_CRUDO_FAV_SINGULAR_APASIONADO_MOTOR= 5.0
PESO_CRUDO_FAV_SINGULAR_PREF_DISENO_EXCLUSIVO = 6.0

# Pesos crudos para preferencias de garaje/aparcamiento
PESO_CRUDO_FAV_MENOR_SUPERFICIE = 3.0 # fav_menor_superficie_planta
PESO_CRUDO_FAV_MENOR_DIAMETRO_GIRO = 5.0 #fav_menor_diametro_giro
PESO_CRUDO_FAV_MENOR_DIMENSION_GARAJE = 8.0 # Para largo, ancho, alto problemáticos
PESO_CRUDO_BASE_BAJO_DIMENSIONES_GARAJE = 1.0 # Peso si no es una preocupación explícita

# Pesos crudos para Estilo de Conducción
# Si estilo es DEPORTIVO
RAW_PESO_DEPORTIVIDAD_ALTO = 4.0
RAW_PESO_MENOR_REL_PESO_POTENCIA_ALTO = 10.0
RAW_PESO_POTENCIA_MAXIMA_ALTO = 5.0
RAW_PESO_PAR_MOTOR_DEPORTIVO_ALTO = 4.0
RAW_PESO_MENOR_ACELERACION_ALTO = 6.0
# Si estilo es MIXTO ()
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

#Peso crudo favorecer por conducir en ciudad
PESO_CRUDO_FAV_DIAMETRO_GIRO_CONDUC_CIUDAD = 7.0

# Pesos para nuevas características de carga y autonomía Si km/año > 60.000 
WEIGHT_AUTONOMIA_PRINCIPAL_MUY_ALTO_KM = 9.0
WEIGHT_AUTONOMIA_2ND_DRIVE_MUY_ALTO_KM = 3.0
WEIGHT_TIEMPO_CARGA_MIN_MUY_ALTO_KM = 9.0  # Menor tiempo es mejor
WEIGHT_POTENCIA_AC_MUY_ALTO_KM = 1.0
WEIGHT_POTENCIA_DC_MUY_ALTO_KM = 9.0

# filtro de la cuota máxima en la funcion de busqueda en BigQuery bigquery_tools.py
FACTOR_CONVERSION_PRECIO_CUOTA = 1.35 / 96

# --------------------------------------- ## --------------------------------------- ## ---------------------------------------
# --- MAPEADOS PARA EL CÁLCULO DE KM ANUALES ESTIMADOS ---
MAPA_FRECUENCIA_USO = {
    "diario": 10,
    "frecuentemente": 4,
    "ocasionalmente": 1.5
}

MAPA_DISTANCIA_TRAYECTO = {
    "no supera los 10 km": 10,
    "está entre 10 y 50 km": 30,
    "está entre 51 y 150 km": 100,
    "supera los 150 km": 200
}

MAPA_FRECUENCIA_VIAJES_LARGOS = {
    "frecuentemente": 60,
    "ocasionalmente": 25,
    "esporádicamente": 8
}

MAPA_REALIZA_VIAJES_LARGOS_KM = {
    "sí": 300,  # 'n' - km promedio por viaje largo
    "no": 0
}

