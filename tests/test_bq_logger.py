# tests/test_bq_logger.py (o tests/test_utils.py)

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Asume que tus modelos y la función de log están en estas rutas
# Ajusta las rutas según tu estructura
from utils.bq_logger import log_busqueda_a_bigquery, TABLE_FULL_ID # Importar también TABLE_FULL_ID
from graph.perfil.state import PerfilUsuario, FiltrosInferidos, EconomiaUsuario 
# Importar tus Enums si los usas para crear los objetos Pydantic de prueba
from utils.enums import Transmision, NivelAventura, TipoMecanica

# --- Pruebas para log_busqueda_a_bigquery ---

@pytest.fixture
def mock_datetime_now():
    """Fixture para mockear datetime.now() y devolver un valor fijo."""
    fixed_datetime = datetime(2024, 5, 15, 10, 30, 0, tzinfo=timezone.utc)
    with patch('utils.bq_logger.datetime') as mock_dt: # Asegúrate que el path sea donde se usa datetime
        mock_dt.now.return_value = fixed_datetime
        yield fixed_datetime

@pytest.fixture
def mock_bigquery_client():
    """Fixture para mockear el cliente BigQuery y su método insert_rows_json."""
    with patch('utils.bq_logger.bigquery.Client') as mock_client_constructor:
        mock_client_instance = MagicMock()
        mock_client_constructor.return_value = mock_client_instance
        mock_client_instance.insert_rows_json.return_value = [] # Simula éxito (sin errores)
        yield mock_client_instance

def test_log_busqueda_happy_path(mock_bigquery_client, mock_datetime_now):
    """Prueba el camino feliz con todos los datos presentes."""
    thread_id_test = "test_thread_123"
    
    # Crear objetos Pydantic de ejemplo
    prefs_obj = PerfilUsuario(
        altura_mayor_190="sí", peso_mayor_100="no", uso_profesional="no",
        coche_principal_hogar="sí", valora_estetica="sí", prefiere_diseno_exclusivo="no",
        solo_electricos="no", transmision_preferida=Transmision.AUTOMATICO,
        apasionado_motor="no", aventura=NivelAventura.ocasional
    )
    filtros_obj = FiltrosInferidos(
        estetica_min=5.0, tipo_mecanica=[TipoMecanica.GASOLINA, TipoMecanica.PHEVD],
        premium_min=1.0, singular_min=1.0, plazas_min=5,
        tipo_carroceria=["SUV"], modo_adquisicion_recomendado="Contado",
        precio_max_contado_recomendado=30000.0
    )
    econ_obj = EconomiaUsuario(
        modo=1, ingresos=60000, ahorro=20000, anos_posesion=5
    )
    pesos_dict = {"estetica": 0.5, "aventura": 0.3, "precio_calidad": 0.2}
    tabla_md = "### Resumen de Criterios\n| Pref | Valor |\n|---|---|\n"
    coches_list = [{"nombre": "Coche A", "precio": 25000}, {"nombre": "Coche B", "precio": 28000}]
    sql_query = "SELECT * FROM coches WHERE precio < @precio;"
    sql_params = [{"name": "precio", "value": 30000, "type": "FLOAT64"}]

    log_busqueda_a_bigquery(
        id_conversacion=thread_id_test,
        preferencias_usuario_obj=prefs_obj,
        filtros_aplicados_obj=filtros_obj,
        economia_usuario_obj=econ_obj,
        pesos_aplicados_dict=pesos_dict,
        tabla_resumen_criterios_md=tabla_md,
        coches_recomendados_list=coches_list,
        num_coches_devueltos=len(coches_list),
        sql_query_ejecutada=sql_query,
        sql_params_list=sql_params
    )

    # Verificar que se llamó a insert_rows_json
    mock_bigquery_client.insert_rows_json.assert_called_once()
    # Verificar los argumentos de la llamada
    args, _ = mock_bigquery_client.insert_rows_json.call_args
    assert args[0] == TABLE_FULL_ID # Verificar el table_id
    
    # Verificar el contenido de la fila insertada
    inserted_row = args[1][0] # Es una lista de filas, tomamos la primera
    assert inserted_row["id_conversacion"] == thread_id_test
    assert inserted_row["timestamp_busqueda"] == mock_datetime_now.isoformat()
    assert json.loads(inserted_row["preferencias_usuario_json"]) == prefs_obj.model_dump(mode='json')
    assert json.loads(inserted_row["filtros_aplicados_json"]) == filtros_obj.model_dump(mode='json')
    assert json.loads(inserted_row["economia_usuario_json"]) == econ_obj.model_dump(mode='json')
    assert json.loads(inserted_row["pesos_aplicados_json"]) == pesos_dict
    assert inserted_row["tabla_resumen_criterios_md"] == tabla_md
    assert json.loads(inserted_row["coches_recomendados_json"]) == coches_list
    assert inserted_row["num_coches_devueltos"] == 2
    assert inserted_row["sql_query_ejecutada"] == sql_query
    assert json.loads(inserted_row["sql_params_json"]) == sql_params

def test_log_busqueda_datos_opcionales_none(mock_bigquery_client, mock_datetime_now):
    """Prueba que maneja bien cuando algunos datos opcionales son None."""
    thread_id_test = "test_thread_456"
    prefs_obj = PerfilUsuario(solo_electricos="sí") # Mínimo
    
    log_busqueda_a_bigquery(
        id_conversacion=thread_id_test,
        preferencias_usuario_obj=prefs_obj,
        filtros_aplicados_obj=None, # <--- Filtros es None
        economia_usuario_obj=None,  # <--- Economía es None
        pesos_aplicados_dict=None,
        tabla_resumen_criterios_md="Resumen sin filtros ni econ.",
        coches_recomendados_list=[], # Búsqueda sin resultados
        num_coches_devueltos=0,
        sql_query_ejecutada="SELECT * WHERE 1=0",
        sql_params_list=[]
    )
    
    mock_bigquery_client.insert_rows_json.assert_called_once()
    args, _ = mock_bigquery_client.insert_rows_json.call_args
    inserted_row = args[1][0]
    
    assert inserted_row["id_conversacion"] == thread_id_test
    assert json.loads(inserted_row["preferencias_usuario_json"]) == prefs_obj.model_dump(mode='json')
    assert "filtros_aplicados_json" not in inserted_row # Se limpió porque era None
    assert "economia_usuario_json" not in inserted_row
    assert "pesos_aplicados_json" not in inserted_row
    assert json.loads(inserted_row["coches_recomendados_json"]) == []
    assert inserted_row["num_coches_devueltos"] == 0