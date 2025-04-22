from utils.rag_carroceria import get_recommended_carrocerias

def test_rag_suv_para_aventura_occasional():
    prefs = {"solo_electricos":"no", "aventura":"ocasional", "uso_profesional":"no", "valora_estetica":"no"}
    filtros = {}
    tipos = get_recommended_carrocerias(prefs, filtros, k=3)
    assert "SUV" in tipos


def test_rag_comercial_para_uso_profesional():
    prefs = {"solo_electricos":"no",
             "aventura":"ninguna",
             "uso_profesional":"sí",
             "valora_estetica":"no"}
    filtros = {}
    tipos = get_recommended_carrocerias(prefs, filtros, k=3)
    assert "COMERCIAL" in tipos
