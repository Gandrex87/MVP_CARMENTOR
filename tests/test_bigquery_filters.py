# tests/test_bigquery_filters.py
import pytest
import pandas as pd
from google.cloud import bigquery
from utils.bigquery_tools import buscar_producto_bd_solo_filtros

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
        self.captured['sql'] = sql
        self.captured['params'] = job_config.query_parameters
        return DummyJob(self._df)

@pytest.fixture(autouse=True)
def patch_bigquery(monkeypatch):
    # DataFrame de ejemplo
    dummy_df = pd.DataFrame([
        {
            'nombre':'TestCar', 'ID': 1, 'marca':'X', 'modelo':'Y',
            'cambio_automatico':True, 'reductoras':False, 'tipo_mecanica':'BEV',
            'indice_altura_interior':1500, 'batalla':2600,
            'estetica':7.0, 'premium':8.0, 'singular':6.0
        }
    ])
    client = DummyClient(dummy_df)
    monkeypatch.setattr(bigquery, 'Client', lambda project=None: client)
    return client


def test_return_format_and_content(patch_bigquery):
    filtros = {'solo_electricos':'sí'}
    pesos = {'estetica':1,'premium':1,'singular':1,'altura':1,'batalla':1}
    res = buscar_producto_bd_solo_filtros(filtros, pesos, k=3)
    assert isinstance(res, list)
    assert res and res[0]['nombre']=='TestCar'


def test_sql_and_parameters(patch_bigquery):
    filtros = {'solo_electricos':'no'}
    pesos = {'estetica':2,'premium':3,'singular':4,'altura':5,'batalla':6}
    buscar_producto_bd_solo_filtros(filtros, pesos, k=2)
    client = patch_bigquery
    sql = client.captured['sql']
    params = {p.name:p for p in client.captured['params']}

    # Hard filter en WHERE
    assert 'cambio_automatico = TRUE' in sql
    assert '@solo_electricos = FALSE' in sql

    # Soft weights en SELECT
    assert '* @peso_estetica' in sql
    assert 'indice_altura_interior/1000 * @peso_altura' in sql
    
    # Parámetros correctos
    assert params['peso_estetica'].value == 2
    assert params['peso_batalla'].value == 6
    assert params['k'].value == 2
