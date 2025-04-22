import re
import pdfplumber
import warnings
warnings.filterwarnings("ignore", message="CropBox missing from /Page")


def cargar_carrocerias_desde_pdf(ruta_pdf: str) -> list[dict]:
    # 1. Leer todo el PDF en un solo string
    texto = ""
    with pdfplumber.open(ruta_pdf) as pdf:
        for page in pdf.pages:
            texto += page.extract_text() + "\n"

    # 2. Elimina encabezados o líneas previas hasta el primer “1. ”
    #    Buscamos la posición donde arranca la primera entrada
    inicio = re.search(r"\n1\.\s", texto)
    if inicio:
        texto = texto[inicio.start():]
    # 3. Dividir por cada nuevo bloque “<número>. ”
    bloques = re.split(r"\n(?=\d+\.\s)", texto)

    entries = []
    for bloque in bloques:
        bloque = bloque.strip()
        if not bloque:
            continue

        # 4. Extraer el “tipo” (p.ej. “COMERCIAL”) del encabezado
        m_tipo = re.match(r"(\d+)\.\s*([A-ZÁÉÍÓÚÑÜ]+)", bloque)
        if not m_tipo:
            continue
        tipo = m_tipo.group(2).strip()

        # 5. Extraer la descripción entre “Descripción:” y “Tags:”
        m_desc = re.search(
            r"Descripción:\s*(.+?)\nTags:",
            bloque,
            flags=re.IGNORECASE | re.DOTALL
        )
        descripcion = m_desc.group(1).replace("\n", " ").strip() if m_desc else ""

        # 6. Extraer los tags tras “Tags:”
        m_tags = re.search(r"Tags:\s*(.+)", bloque, flags=re.IGNORECASE)
        tags = m_tags.group(1).strip().rstrip(".") if m_tags else ""

        entries.append({
            "tipo": tipo,
            "descripcion": descripcion,
            "tags": tags
        })

    return entries



# Uso:
#DATA = cargar_carrocerias_desde_pdf("./utils/tipos_carroceria.pdf")
#print(DATA) comentarlo para que no lo muestre al grafo.
