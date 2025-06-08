# CARMENTOR - Motor de Recomendación RAG Híbrido de Dos Etapas

Este proyecto implementa un sistema avanzado de **Generación Aumentada por Recuperación (RAG)**, diseñado para actuar como el cerebro de un agente de IA conversacional. Su objetivo es ayudar a los usuarios a encontrar el tipo de carrocería de coche ideal, interpretando sus necesidades complejas y proporcionando recomendaciones precisas y razonadas.

La arquitectura ha evolucionado a un sistema híbrido de **dos etapas (Recuperación y Re-Ranking)**, que combina la velocidad de la búsqueda vectorial con la profunda capacidad de razonamiento de los Modelos de Lenguaje Grandes (LLM).

---

## 📚 El Concepto: La Audición de Dos Fases

Para entender el sistema, usemos la analogía de un casting para una película:

### Fase 1: La Audición Abierta (Recuperación Rápida)

Un asistente de casting (nuestro **Modelo de Embeddings de Google**) revisa rápidamente a los 12 actores (las 12 carrocerías) y crea una primera lista de 8 finalistas que *"parecen"* adecuados para el papel basándose en una descripción general (la query de búsqueda).  
Este proceso es rápido y su objetivo es **la cobertura**: asegurarse de que ningún buen candidato se quede fuera.

### Fase 2: El Callback con el Director (Re-Ranking de Precisión)

Los 8 finalistas pasan a una audición privada con el director (**LLM Juez - Gemini de Google**).  
El director los evalúa uno por uno, les entrega el guion completo (el **contexto consolidado del usuario**) y les pide que interpreten el papel. Luego, les asigna una **puntuación numérica del 1 al 10**.

Este proceso es más lento, pero de una **precisión quirúrgica**.

> Al final, el papel se lo llevan los actores con las puntuaciones más altas del director.  
> Esta separación de tareas garantiza tanto velocidad como una calidad de decisión excepcional.

---

## ⚙️ Arquitectura y Flujo de Trabajo

El sistema está diseñado para ser **modular** y sigue un flujo de trabajo claro desde los datos hasta la recomendación final.

### 1. Fuente de Conocimiento y Parseo  
**Archivos**: `utils/tipos_carrocería.pdf`, `rag_reader.py`

- Extrae el texto de forma robusta.
- Interpreta el lenguaje natural de descripciones y tags.
- Genera metadatos estructurados (clave-valor) para cada carrocería, que serán cruciales para el juicio del LLM.

---

### 2. Vector Store Híbrido  
**Tecnologías**: FAISS + Google Cloud Embeddings (modelo `text-multilingual-embedding-002`)

Cada documento en el índice contiene:

- **Vector Semántico**: Para búsqueda por similitud.
- **Metadatos Estructurados**: Para evaluación detallada por el LLM Juez.

---

### 3. Lógica RAG  
**Archivo**: `utils/rag_carroceria.py`

Contiene la lógica principal:

- `get_recommended_carrocerias()`: Orquesta el flujo completo.
- `_crear_contexto_para_llm_juez()`: Reúne toda la información del usuario y genera un contexto limpio.
- `puntuar_candidato_con_llm()`: Usa el LLM Juez para evaluar cada candidato y devolver una puntuación y justificación en JSON.

---

## 🔁 Flujo de una Consulta

1. **Construcción de Query Inteligente**  
   Se crea una query dinámica a partir de preferencias del usuario  
   (ej. "aventura extrema", "bajo consumo", "urbano").

2. **Búsqueda de Candidatos (Recall)**  
   Se realiza una búsqueda semántica en FAISS → se obtienen los 12 tipos de coche más relevantes.

3. **Selección de Finalistas**  
   Se eligen los 8 candidatos con mayor puntuación para re-ranking.

4. **Re-Ranking Paralelo (Precisión)**  
   - Se construye el contexto consolidado del usuario.  
   - Se realizan llamadas **paralelas** a Gemini vía `concurrent.futures`.  
   - Cada llamada evalúa un solo candidato y reduce la latencia.

5. **Ordenamiento Final**  
   Candidatos puntuados se ordenan por calificación.

6. **Retorno**  
   Se devuelve el **top k** final reordenado.

---

## 🌐 Estrategia Multi-LLM (OpenAI + Google Vertex AI)

Este proyecto usa el mejor modelo para cada tarea:

- **OpenAI** (LLM Principal del Agente): Maneja la conversación y el razonamiento general.
- **Google Vertex AI (Gemini 1.5 Flash)**: Actúa como LLM Juez para el re-ranking.

> Esta arquitectura híbrida optimiza el rendimiento, reduce costes y aumenta la resiliencia del sistema.

---

## 🛠️ Cómo Usar y Probar el Sistema

### ✅ Prerrequisitos

- Python 3.10+
- Credenciales de Google Cloud configuradas
- API de Vertex AI habilitada
- Clave de API de OpenAI

---

### 💾 Instalación

```bash
pip install langchain-google-vertexai langchain-community faiss-cpu pdfplumber python-dotenv google-cloud-aiplatform
