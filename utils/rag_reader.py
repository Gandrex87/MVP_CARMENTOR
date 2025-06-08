#utils/rag_reader.py
import re
import pdfplumber
import warnings
import logging
warnings.filterwarnings("ignore", message="CropBox missing from /Page")

# Todo este trabajo de preparación de datos tenía un único objetivo: alimentar la nueva y potente lógica de tu función principal.
# Ahora que tienes un Vectorstore con metadatos de alta calidad, el último paso es asegurarte de que tu función get_recommended_carrocerias los está utilizando.

def _parsear_tags_a_metadata(tags_str: str, tipo_str: str = "") -> dict:
    """
    Función auxiliar para convertir una cadena de tags en un diccionario de metadatos estructurados.
    """
    metadata = {}
    tags_lower = tags_str.lower()
    tipo_lower = tipo_str.lower()

    if 'no sirve para transporte de objetos especiales' in tags_lower or 'no sirve si transporte de objetos especiales' in tags_lower:
        metadata['permite_objetos_especiales'] = False
    elif 'autocaravana' in tipo_lower: # Regla especial para Autocaravana
         metadata['permite_objetos_especiales'] = True
    else:
        # CORREGIDO: Buscamos "transporte objetos especiales" (sin 'de') y más keywords
        metadata['permite_objetos_especiales'] = 'transporte objetos especiales' in tags_lower or \
                                                 'transporte de objetos especiales' in tags_lower or \
                                                 'gran maletero' in tags_lower or \
                                                 'caja de carga' in tags_lower or \
                                                 'portón' in tags_lower

    metadata['traccion_4x4_comun'] = 'tracción 4x4' in tags_lower or \
                                     'opción tracción total' in tags_lower or \
                                     'tracción integral' in tags_lower

    metadata['ideal_para_familias_numerosas'] = 'muchos pasajeros' in tags_lower or \
                                                 'siete plazas' in tags_lower

    # REFINADO: Añadimos "imagen elegante"
    metadata['foco_estetica'] = 'llamar la atención' in tags_lower or \
                               'exclusividad' in tags_lower or \
                               'singularidad' in tags_lower or \
                               'estilo' in tags_lower or \
                               'imagen elegante' in tags_lower

    metadata['uso_profesional'] = 'uso profesional' in tags_lower or \
                                 'trabajo' in tags_lower or \
                                 'logística' in tags_lower or \
                                 'comercio' in tags_lower or \
                                 'trabajo rural' in tags_lower
    
    if 'aventura extrema' in tags_lower or 'terrenos difíciles' in tags_lower or 'todoterreno' in tipo_lower:
        metadata['perfil_aventura'] = 'extrema'
    elif 'aventura' in tags_lower or 'excursiones ligeras' in tags_lower or 'campo o zonas rurales' in tags_lower or 'suv' in tipo_lower:
        metadata['perfil_aventura'] = 'ocasional'
    else:
        metadata['perfil_aventura'] = 'ninguna'
    
    if 'siete plazas' in tags_lower:
        metadata['plazas_maximas'] = 7
    elif 'coupe' in tipo_lower:
        metadata['plazas_maximas'] = 4
    else:
        metadata['plazas_maximas'] = 5

    return metadata
   

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

        # --- NUEVA LÓGICA DE EXTRACCIÓN MÁS ROBUSTA ---

        # 1. Extraer el TIPO (todo en la primera línea después del número)
        m_tipo = re.match(r"\d+\.\s*(.+)", bloque)
        if not m_tipo:
            continue
        tipo = m_tipo.group(1).strip()

        # 2. Extraer DESCRIPCIÓN (todo entre "Descripción:" y "Tags:")
        m_desc = re.search(r"Descripción:\s*(.+?)\s*Tags:", bloque, flags=re.IGNORECASE | re.DOTALL)
        descripcion = m_desc.group(1).replace("\n", " ").strip() if m_desc else ""

        # 3. Extraer TAGS (todo desde "Tags:" hasta el final del bloque)
        m_tags = re.search(r"Tags:\s*(.+)", bloque, flags=re.IGNORECASE | re.DOTALL)
        tags = m_tags.group(1).replace("\n", " ").strip() if m_tags else ""

        # El resto de tu lógica para llamar a _parsear_tags_a_metadata y añadir a entries
        # (esta parte no cambia)
        parsed_metadata = _parsear_tags_a_metadata(tags, tipo) # Le pasamos también el tipo
        entry_completa = {
            "tipo": tipo,
            "descripcion": descripcion,
            "tags": tags,
            **parsed_metadata
        }
        entries.append(entry_completa)

    logging.info(f"Parseados {len(entries)} tipos de carrocería con metadatos enriquecidos.")
    return entries



# Uso:
#DATA = cargar_carrocerias_desde_pdf("utils/tipos_carroceria.pdf")
#print(DATA) #comentarlo para que no lo muestre al grafo.
