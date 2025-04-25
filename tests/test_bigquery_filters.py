# tests/test_bigquery_filters.py
import pytest
import pandas as pd
from google.cloud import bigquery
from utils.bigquery_tools import buscar_producto_bd_solo_filtros  # ajústalo a tu ruta real

# ——————————————————————————————————————————————————————————————————————————————————————
# Fixtures para simular BigQuery
# ——————————————————————————————————————————————————————————————————————————————————————

class DummyJob:
    def __init__(self, df):
        self._df = df
    def result(self):
        return self
    def to_dataframe(self):
        return self._df

class DummyClient:
    def __init__(self, df):
        self._df = df
        self.captured = {}
    def query(self, sql, job_config=None):
        # Captura la SQL y los parámetros para su comprobación
        self.captured['sql'] = sql
        self.captured['params'] = job_config.query_parameters
        return DummyJob(self._df)

@pytest.fixture(autouse=True)
def patch_bigquery_client(monkeypatch):
    # Un DataFrame de prueba
    dummy_df = pd.DataFrame([{
        'nombre':'TestCar',
        'ID': 1,
        'marca':'X',
        'modelo':'Y',
        'cambio_automatico': True,
        'reductoras': False,
        'tipo_mecanica':'GASOLINA',
        'carroceria':'SUV',
        'indice_altura_interior': 1200,
        'batalla': 2800,
        'estetica': 5.0,
        'premium': 6.0,
        'singular': 7.0,
        'traccion': 'ALL'
    }])
    client = DummyClient(dummy_df)
    # parchea bigquery.Client para devolver nuestro DummyClient
    monkeypatch.setattr(bigquery, 'Client', lambda project=None: client)
    return client

# ——————————————————————————————————————————————————————————————————————————————————————
# Tests
# ——————————————————————————————————————————————————————————————————————————————————————

def test_sin_carroceria_y_sin_ev(patch_bigquery_client):
    filtros = {
        'solo_electricos': 'no',
    }
    pesos = {
        'estetica': 1,
        'premium': 1,
        'singular': 1,
        'altura_libre_suelo': 1,
        'batalla': 1,
        'traccion': 1,
        'reductoras': 1
    }
    # Llamada bajo prueba
    rows = buscar_producto_bd_solo_filtros(filtros, pesos, k=3)
    client = patch_bigquery_client

    # Devuelve el registro simulado
    assert rows[0]['nombre'] == 'TestCar'

    sql = client.captured['sql']
    assert "AND cambio_automatico = TRUE" in sql
    # Dado solo_electricos = False, no debe incluir filtro BEV
    assert "tipo_mecanica = 'BEV'" not in sql
    # No debe incluir carroceria IN
    assert "carroceria IN UNNEST" not in sql

    # Comprueba parámetros:
    param_names = [p.name for p in client.captured['params']]
    assert 'solo_electricos' in param_names
    assert 'peso_estetica'   in param_names
    assert 'k'               in param_names

def test_con_carroceria_y_ev(patch_bigquery_client):
    filtros = {
        'solo_electricos': 'si',
        'tipo_carroceria': ['SUV','PICKUP']
    }
    pesos = {
        'estetica': 0.5,
        'premium': 2.0,
        'singular': 3.0,
        'altura_libre_suelo': 1.5,
        'batalla': 0.8,
        'traccion': 1.2,
        'reductoras': 0.0
    }
    rows = buscar_producto_bd_solo_filtros(filtros, pesos, k=2)
    client = patch_bigquery_client

    sql = client.captured['sql']
    # Debe exigir BEV
    assert "AND (" in sql and "tipo_mecanica = 'BEV'" in sql
    # Debe incluir carrocería IN
    assert "carroceria IN UNNEST(@tipo_carroceria)" in sql

    # Verifica que el parámetro de carrocería fue enviado como lista
    params = {p.name:p for p in client.captured['params']}
    assert params['tipo_carroceria'].values == ['SUV','PICKUP']
    # Verifica pesos
    assert params['peso_estetica'].value   == 0.5
    assert params['peso_premium'].value    == 2.0
    assert params['peso_altura'].value     == 1.5

def test_order_by_score_formula(patch_bigquery_client):
    """Asegura que la fórmula de score_total se haya inyectado correctamente."""
    filtros = {'solo_electricos':'no'}
    pesos   = {'estetica':1,'premium':1,'singular':1,'altura_libre_suelo':2,'batalla':3,'traccion':4,'reductoras':5}
    buscar_producto_bd_solo_filtros(filtros, pesos, k=1)
    client = patch_bigquery_client

    sql = client.captured['sql']
    # Debe contener todos los términos de la fórmula
    assert "* @peso_estetica" in sql
    assert "/1000 * @peso_altura" in sql
    assert "CASE\n            WHEN traccion = 'ALL'" in sql
    assert "CASE WHEN reductoras THEN 1 ELSE 0 END" in sql
