# # utils/bigquery_tool.py
# Situación Actual: Tu función finalizar_y_presentar_node ahora calcula y guarda en el estado filtros_inferidos uno de estos dos escenarios para el Modo 1:
# modo_adquisicion_recomendado = "Contado" y un valor en precio_max_contado_recomendado.
# modo_adquisicion_recomendado = "Financiado" y un valor en cuota_max_calculada.
# En utils/bigquery_search.py

# import logging
# logging.basicConfig(level=logging.DEBUG) 
from typing import Optional, List, Dict, Any 
from google.cloud import bigquery
from graph.perfil.state import FiltrosInferidos 


FiltrosDict = Dict[str, Any] 
PesosDict = Dict[str, float]

def buscar_coches_bq(
    filtros: Optional[FiltrosDict], 
    pesos: Optional[PesosDict],   # Recibe pesos NORMALIZADOS
    k: int = 5
) -> list[dict]:
    """
    Busca coches en BigQuery aplicando filtros y ordenando por score ponderado
    con Min-Max Scaling aplicado a las características numéricas en SQL.
    """
    if not filtros or not pesos:
        #logging.warning("Faltan filtros o pesos para la búsqueda en BigQuery.")
        return []
        
    # Asegurar valores por defecto 0.0 para pesos si no vienen
    # Se asume que el dict 'pesos' contiene todas las claves necesarias después de compute/normalize
    pesos_completos = {
        "estetica": pesos.get("estetica", 0.0),
        "premium": pesos.get("premium", 0.0),
        "singular": pesos.get("singular", 0.0),
        "altura_libre_suelo": pesos.get("altura_libre_suelo", 0.0),
        "batalla": pesos.get("batalla", 0.0), # <-- Nuevo Peso
        "indice_altura_interior": pesos.get("indice_altura_interior", 0.0), # <-- Nuevo Peso
        "traccion": pesos.get("traccion", 0.0),
        "reductoras": pesos.get("reductoras", 0.0),
    }

    try:
        client = bigquery.Client() 
    except Exception as e_auth:
       # logging.error(f"Error al inicializar cliente BigQuery: {e_auth}")
        return []

    # --- Construcción de la Query ---
    sql = """
    SELECT
      -- Columnas que quieres devolver ...
      nombre, ID, marca, modelo, cambio_automatico, tipo_mecanica, 
      tipo_carroceria, indice_altura_interior, batalla, estetica, premium, 
      singular, altura_libre_suelo, traccion, reductoras, precio_compra_contado,
      
      -- --- INICIO CÁLCULO SCORE CON MIN-MAX SCALING ---
      (
        -- Estética (Rango Asumido: 1-10)
        COALESCE(SAFE_DIVIDE(COALESCE(estetica, 1.0) - 1.0, 10.0 - 1.0), 0) * @peso_estetica 
        
        -- Premium (Rango Asumido: 1-10)
        + COALESCE(SAFE_DIVIDE(COALESCE(premium, 1.0) - 1.0, 10.0 - 1.0), 0) * @peso_premium
        
        -- Singular (Rango Asumido: 1-10)
        + COALESCE(SAFE_DIVIDE(COALESCE(singular, 1.0) - 1.0, 10.0 - 1.0), 0) * @peso_singular
        
        -- Altura Libre Suelo (Ej: 67.0 - 438.0) <-- ¡USA TUS VALORES!
        + COALESCE(SAFE_DIVIDE(COALESCE(altura_libre_suelo, 67.0) - 67.0, 438.0 - 67.0), 0) * @peso_altura
        
        -- Batalla (Ej: 1650.0 -4078) <-- ¡USA TUS VALORES!
        + COALESCE(SAFE_DIVIDE(COALESCE(batalla, 1650.0) - 1650.0, 4078.0 - 1650.0), 0) * @peso_batalla 
        
        -- Índice Altura Interior (Ej: 0.9 - 2.7) <-- ¡PENDIENTE CAMBIAR ESTE VALOR,VALIDAR TEO!
        + COALESCE(SAFE_DIVIDE(COALESCE(indice_altura_interior, 0.9) - 0.9, 2.7 - 0.9), 0) * @peso_indice_altura
        
        -- Tracción (Mapeo 0-1, se mantiene igual)
        + CASE WHEN traccion = 'ALL' THEN 1.0 WHEN traccion = 'RWD' THEN 0.5 ELSE 0.0 END * @peso_traccion
        
        -- Reductoras (Mapeo 0-1, se mantiene igual)
        + (CASE WHEN COALESCE(reductoras, FALSE) THEN 1.0 ELSE 0.0 END) * @peso_reductoras
        
      ) AS score_total
      -- --- FIN CÁLCULO SCORE ---
      
    FROM `thecarmentor-mvp2.web_cars.match_coches_pruebas` -- Reemplaza con tu tabla
    WHERE 1=1 
    """

    # Lista para parámetros (Añadir nuevos pesos)
    params = [
        bigquery.ScalarQueryParameter("peso_estetica",   "FLOAT64", pesos_completos["estetica"]),
        bigquery.ScalarQueryParameter("peso_premium",    "FLOAT64", pesos_completos["premium"]),
        bigquery.ScalarQueryParameter("peso_singular",   "FLOAT64", pesos_completos["singular"]),
        bigquery.ScalarQueryParameter("peso_altura",     "FLOAT64", pesos_completos["altura_libre_suelo"]),
        bigquery.ScalarQueryParameter("peso_batalla",    "FLOAT64", pesos_completos["batalla"]), # <-- Nuevo
        bigquery.ScalarQueryParameter("peso_indice_altura","FLOAT64", pesos_completos["indice_altura_interior"]), # <-- Nuevo
        bigquery.ScalarQueryParameter("peso_traccion",   "FLOAT64", pesos_completos["traccion"]),
        bigquery.ScalarQueryParameter("peso_reductoras", "FLOAT64", pesos_completos["reductoras"]),
    ]

    # --- Aplicar Filtros Dinámicamente ---
    
    # Transmisión (igual que antes)
    transmision_val = filtros.get("transmision_preferida")
    if isinstance(transmision_val, str):
        # ... (lógica para añadir AND cambio_automatico = TRUE/FALSE) ...
        transmision_lower = transmision_val.lower()
        if transmision_lower == 'automático':
            sql += "\n      AND cambio_automatico = TRUE"
        elif transmision_lower == 'manual':
            sql += "\n      AND cambio_automatico = FALSE"


    # Filtros Numéricos Mínimos 
    # --- ¡CAMBIO! Quitar batalla_min e indice_altura_interior_min de aquí ---
    numeric_filters_map = {
        # "batalla_min": ("batalla", "FLOAT64"), # <-- ELIMINADO
        # "indice_altura_interior_min": ("indice_altura_interior", "FLOAT64"), # <-- ELIMINADO
        "estetica_min": ("estetica", "FLOAT64"),
        "premium_min": ("premium", "FLOAT64"),
        "singular_min": ("singular", "FLOAT64"),
    }
    # -----------------------------------------------------------------------
    for key, (column, dtype) in numeric_filters_map.items():
        value = filtros.get(key)
        if value is not None:
            param_name = key 
            # Usar COALESCE en BQ es seguro para >=, pero opcional si la columna no tiene NULLs
            sql += f"\n      AND COALESCE({column}, 0) >= @{param_name}" 
            params.append(bigquery.ScalarQueryParameter(param_name, dtype, float(value)))

    # Tipo Mecanica (igual que antes)
    tipos_mecanica_str = filtros.get("tipo_mecanica")
    if isinstance(tipos_mecanica_str, list) and tipos_mecanica_str:
        # ... (añadir AND ... IN UNNEST(@tipos_mecanica) y el parámetro) ...
        sql += "\n      AND tipo_mecanica IN UNNEST(@tipos_mecanica)"
        params.append(bigquery.ArrayQueryParameter("tipos_mecanica", "STRING", tipos_mecanica_str))


    # Tipo Carroceria (igual que antes)
    tipos_carroceria = filtros.get("tipo_carroceria")
    if isinstance(tipos_carroceria, list) and tipos_carroceria:
        # ... (añadir AND ... IN UNNEST(@tipos_carroceria) y el parámetro) ...
        sql += "\n      AND tipo_carroceria IN UNNEST(@tipos_carroceria)"
        params.append(bigquery.ArrayQueryParameter("tipos_carroceria", "STRING", tipos_carroceria))


    # Filtro Económico Condicional (igual que antes)
     # --- Filtro Económico Condicional (REVISADO Y AMPLIADO) ---
    print("DEBUG (BQ Search) ► Aplicando Filtro Económico Condicional...")
    
    modo_adq_rec = filtros.get("modo_adquisicion_recomendado") # Recomendación de Modo 1
    
    # Variables para el filtro final
    aplicar_filtro_precio = False
    valor_precio_max = None
    aplicar_filtro_cuota = False
    valor_cuota_max = None

    if modo_adq_rec == "Contado":
        # Caso 1: Modo 1 recomendó Contado
        precio_max_rec = filtros.get("precio_max_contado_recomendado")
        if precio_max_rec is not None:
            print(f"DEBUG (BQ Search) ► Detectado Modo 1 Rec. Contado. Límite Precio: {precio_max_rec}")
            aplicar_filtro_precio = True
            valor_precio_max = precio_max_rec
            
    elif modo_adq_rec == "Financiado":
        # Caso 2: Modo 1 recomendó Financiado
        cuota_max_calc = filtros.get("cuota_max_calculada")
        if cuota_max_calc is not None:
            print(f"DEBUG (BQ Search) ► Detectado Modo 1 Rec. Financiado. Límite Cuota: {cuota_max_calc}")
            aplicar_filtro_cuota = True
            valor_cuota_max = cuota_max_calc
            
    else:
        # Caso 3: No es recomendación de Modo 1 (podría ser Modo 2 directo)
        # Leemos modo y submodo directamente de los filtros (deben estar presentes)
        modo_directo = filtros.get("modo")
        submodo_directo = filtros.get("submodo")
        print(f"DEBUG (BQ Search) ► No hay Rec. Modo 1. Verificando Modo directo: modo={modo_directo}, submodo={submodo_directo}")

        if modo_directo == 2: # Es Modo 2 definido por usuario
            if submodo_directo == 1:
                # Modo 2, Submodo 1: Usar pago_contado del usuario como límite de precio
                pago_contado_directo = filtros.get("pago_contado")
                if pago_contado_directo is not None:
                    print(f"DEBUG (BQ Search) ► Detectado Modo 2 Contado. Límite Precio: {pago_contado_directo}")
                    aplicar_filtro_precio = True
                    valor_precio_max = pago_contado_directo
            elif submodo_directo == 2:
                # Modo 2, Submodo 2: Usar cuota_max del usuario como límite de cuota
                cuota_max_directa = filtros.get("cuota_max")
                if cuota_max_directa is not None:
                    print(f"DEBUG (BQ Search) ► Detectado Modo 2 Cuotas. Límite Cuota: {cuota_max_directa}")
                    aplicar_filtro_cuota = True
                    valor_cuota_max = cuota_max_directa

    # Ahora APLICAR el filtro SQL que corresponda (solo uno debería activarse)
    if aplicar_filtro_precio and valor_precio_max is not None:
        print(f"DEBUG (BQ Search) ► Añadiendo SQL: Precio Contado <= {valor_precio_max}")
        sql += "\n      AND COALESCE(precio_compra_contado, 999999999) <= @precio_maximo"
        params.append(bigquery.ScalarQueryParameter("precio_maximo", "FLOAT64", float(valor_precio_max)))
    elif aplicar_filtro_cuota and valor_cuota_max is not None:
        print(f"DEBUG (BQ Search) ► Añadiendo SQL: Cuota Estimada <= {valor_cuota_max}")
        sql += "\n      AND COALESCE(precio_compra_contado, 0) * 1.35 / 96.0 <= @cuota_maxima" # OJO: Nombre param @cuota_maxima
        params.append(bigquery.ScalarQueryParameter("cuota_maxima", "FLOAT64", float(valor_cuota_max))) # OJO: Nombre param
    else:
        print("DEBUG (BQ Search) ► No se aplicará filtro económico específico (ni precio ni cuota).")

    # --- Orden y Límite (igual que antes) ---
    # Orden y Límite (igual que antes)
    sql += "\n    ORDER BY score_total DESC"
    # --- AÑADIR DESEMPATE --- (Opcional pero recomendado)
    sql += ", precio_compra_contado ASC" 
    # -----------------------
    sql += "\n    LIMIT @k"
    params.append(bigquery.ScalarQueryParameter("k", "INT64", k))

    # --- Ejecución (igual que antes) ---
    # ... (logging, prints, try/except para client.query) ...
    log_params = [(p.name, getattr(p, 'value', getattr(p, 'values', None))) for p in params]
    #logging.debug("🔎 BigQuery SQL:\n%s", sql)
    #logging.debug("🔎 BigQuery params: %s", log_params)
    print("--- 🧠 SQL Query ---\n", sql) 
    print("\n--- 📦 Parameters ---\n", log_params) 

    try:
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        query_job = client.query(sql, job_config=job_config)
        df = query_job.result().to_dataframe() 
       # logging.info(f"✅ BigQuery query ejecutada, {len(df)} resultados obtenidos.")
        return df.to_dict(orient="records")
    except Exception as e:
        #logging.error(f"❌ Error al ejecutar la query en BigQuery: {e}")
        return []