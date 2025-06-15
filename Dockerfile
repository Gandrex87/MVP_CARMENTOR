# Dockerfile

# --- ETAPA 1: Builder ---
# Usamos una imagen completa de Python para instalar las dependencias.
# Esto incluye herramientas de compilación que podrían ser necesarias.
FROM python:3.11-slim as builder

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias
# Copiamos solo el archivo de requerimientos primero para aprovechar el caché de Docker.
# Si requirements.txt no cambia, Docker no volverá a ejecutar este paso.
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# --- ETAPA 2: Final ---
# Usamos la misma imagen base, que es ligera y optimizada.
FROM python:3.11-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar las dependencias pre-compiladas de la etapa 'builder'.
# Esto hace que la imagen final sea más pequeña porque no incluye las herramientas de compilación.
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Copiar TODO el código de tu aplicación al directorio de trabajo en el contenedor.
# El .dockerignore se encargará de excluir los archivos y carpetas que no queremos.
COPY . .

# Indicar al contenedor que escuche en el puerto 8080.
# Cloud Run espera por defecto que los contenedores escuchen en este puerto.
EXPOSE 8080

# Comando para ejecutar la aplicación cuando se inicie el contenedor.
# - "api.main:app": Apunta al objeto 'app' en tu archivo 'api/main.py'. ¡Ajusta la ruta si es diferente!
# - "--host 0.0.0.0": MUY IMPORTANTE. Hace que el servidor escuche en todas las interfaces de red dentro del contenedor.
# - "--port 8080": Coincide con el puerto que hemos expuesto.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]