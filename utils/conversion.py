import unicodedata
import re

# Función es transformar datos (de Enums a strings).
# Otras funciones de transformación como normalize_text_sql().
# Tiene una única responsabilidad clara: conversión.


def get_enum_names(lista_enum) -> list[str]:
    return [item.value if hasattr(item, "value") else str(item) for item in lista_enum]



def normalizar_texto(texto: str) -> str:
    return unicodedata.normalize('NFKD', texto.lower()).encode('ascii', 'ignore').decode('utf-8')


#Esta la uso en bigquery
def normalize_text_sql(text: str) -> str:
    text = text.lower().replace('-', ' ')  # Minúsculas y reemplazo de guiones
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')  # Eliminar acentos
    text = re.sub(r'[^a-z0-9\s.]', '', text)  # Solo letras, números y espacios
    text = re.sub(r'\s+', ' ', text).strip()  # Espacios redundantes
    return text

def is_yes(v):
    return isinstance(v, str) and v.strip().lower() in ("sí","si")

