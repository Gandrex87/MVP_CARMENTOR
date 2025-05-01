import re
from utils.enums import Transmision

def extraer_preferencias_iniciales(texto: str) -> dict:
    prefs = {}
    # familia → uso_profesional=no
    if re.search(r"\bfamilia\b", texto, re.IGNORECASE):
        prefs["uso_profesional"] = "no"
    # altura
    m = re.search(r"(\d+(?:\.\d+)?)\s?m", texto)
    if m:
        altura = float(m.group(1))
        prefs["altura_mayor_190"] = "sí" if altura > 1.90 else "no"
    # peso
    p = re.search(r"(\d+(?:\.\d+)?)\s?kg", texto, re.IGNORECASE)
    if p:
        peso = float(p.group(1))
        prefs["peso_mayor_100"] = "sí" if peso > 100 else "no"
    # dentro de extraer_preferencias_iniciales(texto):
    text = texto.lower()
    if "manual" in text:
        prefs["transmision_preferida"] = Transmision.MANUAL.value
    elif "ambos" in text:
        prefs["transmision_preferida"] = Transmision.AMBOS.value
    elif re.search(r"\bautomát?ico\b", text):
        prefs["transmision_preferida"] = Transmision.AUTOMATICO.value
    return prefs


