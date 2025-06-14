# Guía de Despliegue: Agente CarBlau a Cloud Run

Esta guía te llevará paso a paso a través del proceso de empaquetar tu agente FastAPI en un contenedor Docker y desplegarlo como un servicio escalable en Google Cloud Run.

---

### **Fase 0: Pre-requisitos**

Antes de empezar, asegúrate de tener lo siguiente:

1.  **Un Proyecto de Google Cloud Platform (GCP):**
    * Con la **facturación habilitada**. Cloud Run y otros servicios tienen un nivel gratuito generoso, pero la facturación debe estar activa.
    * Toma nota de tu **ID de Proyecto** (ej: `thecarmentor-mvp2`).

2.  **Herramientas de Línea de Comandos Instaladas:**
    * **Google Cloud CLI (`gcloud`):** Si no la tienes, [instálala y configúrala](https://cloud.google.com/sdk/docs/install). Después de instalar, autentícate:
        ```bash
        gcloud auth login
        gcloud auth application-default login
        gcloud config set project [TU_ID_DE_PROYECTO]
        ```
    * **Docker:** Necesitas Docker para construir la imagen del contenedor. La forma más fácil es instalar [Docker Desktop](https://www.docker.com/products/docker-desktop/).

3.  **Código del Proyecto Funcional:**
    * Asegúrate de que tu agente y tu API FastAPI funcionan correctamente en tu máquina local.

---

### **Fase 1: Preparar tu Código para Producción**

#### 1.1. Archivo de Dependencias (`requirements.txt`)

Es crucial tener un archivo que liste todas las librerías Python que tu proyecto necesita.

* En tu terminal, asegúrate de que tu entorno virtual (`car_env`) esté activado.
* Ejecuta el siguiente comando en la raíz de tu proyecto para generar el archivo:
    ```bash
    pip freeze > requirements.txt
    ```
* Abre `requirements.txt` y verifica que contenga todas las librerías clave, como:
    * `fastapi`
    * `uvicorn`
    * `langchain`, `langchain-core`, `langchain-openai` (o `langchain-google-vertexai`)
    * `langgraph`
    * `langgraph-checkpoint-postgres`
    * `psycopg[binary]` o `psycopg2-binary` y `asyncpg`
    * `google-cloud-bigquery`, `google-cloud-aiplatform`, etc.
    * `pandas`
    * `python-dotenv`

#### 1.2. Archivo `.dockerignore`

Para que tu imagen Docker sea más pequeña y segura, crea un archivo llamado `.dockerignore` en la raíz de tu proyecto. Esto le dice a Docker qué archivos y carpetas **ignorar** al construir la imagen.

* Crea el archivo `.dockerignore` y añade lo siguiente:
    ```
    # Ignorar entorno virtual
    car_env/
    .venv/

    # Ignorar archivos de configuración local y secretos
    .env
    *.env
    
    # Ignorar directorios de Python y caché
    __pycache__/
    *.pyc
    *.pyo
    
    # Ignorar directorios de IDE y sistema operativo
    .vscode/
    .idea/
    .DS_Store
    
    # Ignorar directorios de Git
    .git/
    .gitignore
    ```

---

### **Fase 2: "Dockerizar" tu Aplicación**

Crearemos un archivo `Dockerfile` que contiene las instrucciones para construir una imagen de contenedor de tu aplicación. Usaremos un enfoque "multi-etapa" que es una buena práctica para producción.

* Crea un archivo llamado `Dockerfile` (sin extensión) en la raíz de tu proyecto.
* Pega el siguiente contenido:

    ```dockerfile
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
    ```

---

### **Fase 3: Configurar Google Cloud Platform**

Necesitamos habilitar las APIs necesarias y crear un lugar para almacenar nuestra imagen Docker.

1.  **Habilitar APIs:** En tu terminal (con `gcloud` configurado), ejecuta:
    ```bash
    gcloud services enable run.googleapis.com
    gcloud services enable artifactregistry.googleapis.com
    gcloud services enable sqladmin.googleapis.com
    ```
2.  **Crear un Repositorio en Artifact Registry:** Este es el "almacén" para tus imágenes Docker en GCP.
    ```bash
    gcloud artifacts repositories create [NOMBRE_DEL_REPOSITORIO] \
        --repository-format=docker \
        --location=europe-west1 \
        --description="Repositorio para el agente CarBlau"
    ```
    * Reemplaza `[NOMBRE_DEL_REPOSITORIO]` por un nombre (ej: `carblau-repo`).
    * Asegúrate de que `--location` (ej: `europe-west1`) sea la misma región donde planeas desplegar Cloud Run.

---

### **Fase 4: Construir, Subir y Desplegar la Imagen**

Ahora viene la parte emocionante.

1.  **Configurar Docker para Autenticarse con GCP:** Este comando permite a tu Docker local subir imágenes a tu Artifact Registry.
    ```bash
    gcloud auth configure-docker europe-west1-docker.pkg.dev
    ```
    (Reemplaza `europe-west1` si usaste otra región).

2.  **Construir la Imagen Docker:** Desde la raíz de tu proyecto, ejecuta:
    ```bash
    docker build -t europe-west1-docker.pkg.dev/[TU_ID_DE_PROYECTO]/[NOMBRE_DEL_REPOSITORIO]/carblau-agent:v1 .
    ```
    * Reemplaza `[TU_ID_DE_PROYECTO]` y `[NOMBRE_DEL_REPOSITORIO]`.
    * `carblau-agent:v1` es el nombre y la etiqueta (versión) de tu imagen.
    * El `.` al final es importante, le dice a Docker que use el `Dockerfile` del directorio actual.

3.  **Subir (Push) la Imagen a Artifact Registry:**
    ```bash
    docker push europe-west1-docker.pkg.dev/[TU_ID_DE_PROYECTO]/[NOMBRE_DEL_REPOSITORIO]/carblau-agent:v1
    ```

4.  **Desplegar en Cloud Run:** Este es el comando final.
    * **Primero, obtén el Nombre de Conexión de tu Instancia de Cloud SQL:** Ve a la página de tu instancia de Cloud SQL en la consola de GCP y copia el "Nombre de conexión" (ej: `thecarmentor-mvp2:europe-west1:carblau-sql-instance`).
    * Ejecuta el siguiente comando, reemplazando los placeholders:

    ```bash
    gcloud run deploy carblau-agent-service \
        --image europe-west1-docker.pkg.dev/[TU_ID_DE_PROYECTO]/[NOMBRE_DEL_REPOSITORIO]/carblau-agent:v1 \
        --platform managed \
        --region europe-west1 \
        --allow-unauthenticated \
        --set-env-vars="DB_HOST=/cloudsql/[NOMBRE_CONEXION_INSTANCIA_SQL],DB_USER=[TU_USUARIO_DB],DB_NAME=[TU_NOMBRE_DB]" \
        --set-secrets="OPENAI_API_KEY=openai-api-key:latest,DB_PASSWORD=carblau-db-password:latest" \
        --add-cloudsql-instances=[NOMBRE_CONEXION_INSTANCIA_SQL]
    ```

    **Desglose de las Opciones Clave:**
    * `gcloud run deploy carblau-agent-service`: Inicia el despliegue de un servicio llamado `carblau-agent-service`.
    * `--image ...`: Especifica la imagen que acabas de subir.
    * `--region europe-west1`: La región donde se desplegará.
    * `--allow-unauthenticated`: **IMPORTANTE:** Permite que cualquier persona en internet llame a tu API. Ideal para pruebas. Para producción real, lo quitarías y configurarías autenticación.
    * `--set-env-vars`: Define variables de entorno no sensibles.
        * **`DB_HOST=/cloudsql/[NOMBRE_CONEXION_INSTANCIA_SQL]`**: Esta es la forma MÁGICA de conectar a Cloud SQL desde Cloud Run. No usas una IP. Le dices que se conecte a través de un socket Unix que se crea automáticamente cuando usas la opción `--add-cloudsql-instances`. **El valor de `DB_HOST` en tu `.env` para producción debe ser esta ruta.**
    * `--set-secrets`: La forma **segura** de manejar secretos. Debes haber creado estos secretos previamente en **Secret Manager** de GCP. El formato es `[VARIABLE_DE_ENTORNO_EN_EL_CONTENEDOR]=[NOMBRE_SECRETO_EN_GCP]:[VERSION]`.
    * `--add-cloudsql-instances`: Esta es la opción clave que activa el **Cloud SQL Auth Proxy** automáticamente para tu servicio de Cloud Run, permitiéndole conectarse de forma segura a tu base de datos.

---

### **Fase 5: Probar y Siguientes Pasos**

1.  **Obtener la URL:** Después de un despliegue exitoso, `gcloud` te dará la URL del servicio (ej: `https://carblau-agent-service-xxxx-ew.a.run.app`).
2.  **Probar:** Usa Postman o tu notebook para hacer peticiones a tu API desplegada, usando esta nueva URL en lugar de `http://127.0.0.1:8000`.
3.  **Ver Logs:** Si algo falla, ve a la sección de Cloud Run en la consola de GCP, selecciona tu servicio y ve a la pestaña "Registros" (Logs) para ver la salida de tu aplicación.
4.  **¡Felicidades!** Has desplegado tu agente.

**Próximos Pasos (Producción Real):**
* Configurar un dominio personalizado.
* Implementar autenticación de API (`--no-allow-unauthenticated`).
* Configurar un pipeline de CI/CD para automatizar los despliegues.

Este proceso puede parecer largo, pero es muy robusto. ¡Tómate tu tiempo con cada paso!
