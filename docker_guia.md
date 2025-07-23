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
#### Guía Esencial de Comandos Docker para Desarrolladores

Docker es una herramienta que te permite empaquetar tu aplicación y sus dependencias en una unidad estandarizada llamada "contenedor". Esto asegura que tu aplicación funcione de la misma manera en cualquier entorno. Aquí tienes los comandos clave que necesitas para trabajar con Docker.

---

#### 1. Construir una Imagen (`docker build`)

Este es el primer y más importante paso. Toma las instrucciones de tu `Dockerfile` y crea una "imagen" de tu aplicación. Una imagen es como una plantilla o un plano para tus contenedores.

**Comando Básico:**
```bash
docker build -t nombre-de-tu-imagen:tag .
```

Desglose:
```bash
docker build: El comando para construir.
```

```bash
-t o --tag: Permite "etiquetar" tu imagen con un nombre y una versión (el tag). Es una muy buena práctica usarlo siempre.
```

nombre-de-tu-imagen: Un nombre descriptivo, por ejemplo, `carblau-agent-api`.

`:tag:` Una versión, como `:v1`, :`latest`, o :0.1.0. Si la omites, por defecto será :`latest`.

`.`: El punto al final es crucial. Le dice a Docker que el "contexto de construcción" (donde se encuentra tu Dockerfile y el código fuente) es el directorio actual.

Ejemplo para tu proyecto:

```bash
docker build -t carblau-agent:v1 .
```

(Ejecuta este comando desde la carpeta raíz de tu proyecto MVP_CARMENTOR).

2. Gestionar Imágenes
Una vez construidas, puedes ver y eliminar las imágenes que tienes en tu máquina.

Listar imágenes locales:

```bash
docker images
```

Esto te mostrará una tabla con todas las imágenes que has construido o descargado, su tag, su ID, cuándo se crearon y su tamaño.

Eliminar una imagen:

```bash
docker rmi [ID_DE_LA_IMAGEN_O_NOMBRE:TAG]
```

Ejemplo: docker rmi carblau-agent:v1

3. Ejecutar un Contenedor (docker run)
Este comando toma una imagen y crea una instancia ejecutable de ella: un contenedor. Es el comando con más opciones útiles.

Comando Básico:
```bash
docker run nombre-de-tu-imagen:tag

Opciones más Importantes:

-d o --detach: Ejecuta el contenedor en segundo plano (modo "detached"). 
Tu terminal quedará libre. Es casi siempre lo que quieres para un servidor.

-p o --publish [PUERTO_HOST]:[PUERTO_CONTENEDOR]: Publica (o "mapea") un puerto del contenedor a un puerto de tu máquina local (host). Es esencial para poder acceder a tu API desde el navegador o Postman.

Ejemplo: -p 8000:8080 mapea el puerto 8080 del contenedor (donde Uvicorn está escuchando) al puerto 8000 de tu máquina. Podrás acceder a la API en http://localhost:8000.
```

--name [NOMBRE_DEL_CONTENEDOR]: Asigna un nombre fácil de recordar a tu contenedor. Si no lo haces, Docker le asignará uno aleatorio (ej: frosty_newton).

Ejemplo: `--name carblau-api-container`

-e o --env [VARIABLE]="[VALOR]": Pasa una variable de entorno al contenedor. Muy útil para no usar un archivo `.env` en producción.

Ejemplo:` -e DB_USER="mi_usuario"`

--env-file ./mi.env: Carga variables de entorno desde un archivo.

--rm: Elimina automáticamente el contenedor cuando se detiene. Muy útil para pruebas rápidas, para no dejar contenedores parados ocupando espacio.

Ejemplo Completo para tu API:

```
docker run -d -p 8000:8080 --name carblau-api-container --env-file ./.env carblau-agent:v1
```

Este comando:

Crea un contenedor a partir de la imagen carblau-agent:v1.

Lo ejecuta en segundo plano (-d).

Mapea el puerto 8080 del contenedor al puerto 8000 de tu máquina (-p 8000:8080).

Le da el nombre carblau-api-container (--name).

Carga las variables de entorno de tu archivo .env (--env-file).

4. Gestionar Contenedores en Ejecución
Listar contenedores en ejecución:

```bash
docker ps
```

Listar TODOS los contenedores (en ejecución y parados):
```bash
docker ps -a
```

Detener un contenedor en ejecución:

```bash
docker stop [ID_DEL_CONTENEDOR_O_NOMBRE]
```
Ejemplo: docker stop carblau-api-container

Iniciar un contenedor parado:

```bash
docker start [ID_DEL_CONTENEDOR_O_NOMBRE]
```

Eliminar un contenedor parado:

```bash
docker rm [ID_DEL_CONTENEDOR_O_NOMBRE]
```
5. Ver Logs de un Contenedor
Para ver la salida de tu aplicación (los print y logging de tu FastAPI), que ahora están dentro del contenedor.

```bash
docker logs [ID_DEL_CONTENEDOR_O_NOMBRE]
```

Opción útil:
```bash
-f o --follow: Sigue los logs en tiempo real, como un tail -f. Muy útil para depurar.
```

```bash
docker logs -f carblau-api-container
```
(Usa Ctrl+C para salir del modo de seguimiento).

6. Interactuar con un Contenedor en Ejecución
A veces necesitas "entrar" en el contenedor para ver qué está pasando, listar archivos, etc.

```bash
docker exec -it [ID_DEL_CONTENEDOR_O_NOMBRE] /bin/bash
```

Desglose:
```bash
docker exec: Ejecuta un comando en un contenedor en ejecución.

-it: Abreviatura de -i (interactivo, mantiene STDIN abierto) y -t (asigna una pseudo-TTY). Juntos te dan una terminal interactiva.
```

/bin/bash: El comando a ejecutar (en este caso, iniciar un shell Bash). Si la imagen base no tiene bash, puedes probar con /bin/sh.

Una vez dentro, tendrás una línea de comandos dentro del contenedor. Puedes usar comandos como ls -la, cat archivo.py, etc. Escribe exit para salir.

7. Interacción con un Registro de Contenedores (como Artifact Registry)
Estos comandos son los que usarías para subir tu imagen a la nube.

Iniciar sesión en el registro:

## Para Artifact Registry (como vimos en la guía de despliegue)

```bash
gcloud auth configure-docker europe-west1-docker.pkg.dev 
```

## Para Docker Hub (el registro público)
docker login

Subir una imagen (Push): Primero debes "taguear" tu imagen con el nombre completo del repositorio.

## 1. Taguear la imagen local (si la construiste con un nombre simple)

```bash
docker tag carblau-agent:v1 europe-west1-docker.pkg.dev/[PROYECTO]/[REPO]/carblau-agent:v1
```

## 2. Subir la imagen

```bash
docker push europe-west1-docker.pkg.dev/[PROYECTO]/[REPO]/carblau-agent:v1
```

Descargar una imagen (Pull):

docker pull ubuntu:latest # Descarga la imagen 'ubuntu' desde Docker Hub
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

* Reemplaza `[TU_ID_DE_PROYECTO]` y `NOMBRE_DEL_REPOSITORIO]`.
    - `carblau-agent:v1` es el nombre y la etiqueta (versión) de tu imagen.
    - El `.` al final es importante, le dice a Docker que use el `Dockerfile` del directorio actual.

3.  **Subir (Push) la Imagen a Artifact Registry:**
```bash
    docker push europe-west1-docker.pkg.dev/[TU_ID_DE_PROYECTO]/[NOMBRE_DEL_REPOSITORIO]/carblau-agent:v1
```

4.  **Desplegar en Cloud Run:** Este es el comando final.
    * **Primero, obtén el Nombre de Conexión de tu Instancia de Cloud SQL:** Ve a la página de tu instancia de Cloud SQL en la consola de GCP y copia el "Nombre de conexión" (ej: `thecarmentor-mvp2:europe-west1:carblau-sql-instance`).
    * Ejecutar comando, reemplazando los placeholders:

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

* Es decir:
  
```bash
gcloud run deploy carblau-agent-api \
  --image="europe-west1-docker.pkg.dev/thecarmentor-mvp2/carblau-repo/carblau-agent-api:debug" \
  --region="europe-west1" \
  --service-account="carblau-run-sa@thecarmentor-mvp2.iam.gserviceaccount.com" \
  --add-cloudsql-instances="thecarmentor-mvp2:europe-west1:carblau-sql-instance" \
  --set-env-vars="DB_HOST=/cloudsql/thecarmentor-mvp2:europe-west1:carblau-sql-instance" \
  --set-secrets="DB_USER=DB_USER:latest,DB_PASSWORD=DB_PASSWORD:latest,DB_NAME=DB_NAME:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest" \
  --memory=2Gi \
  --cpu=2 \
  --port="8000" \
  --timeout=600s
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

## Creacion de la imagen paso a paso

```bash
docker build -t carblau-agent:v1 .
```

Valido la creacion de la imagen

```bash
docker images
```

Pongo a prueba el contenedor

```bash
docker run -d -p 8000:8080 --name carblau-api-container --env-file ./.env carblau-agent:v1
```

Desglosemos este comando:

``` bash
-d: Ejecuta el contenedor en segundo plano (detached).

-p 8000:8080: Publica los puertos. Mapea el puerto 8000 de tu máquina (host) al puerto 8080 del contenedor. Tu Dockerfile expone el 8080, así que ahora podrás acceder a tu API en http://localhost:8000.

--name carblau-api-container: Le da un nombre fácil de recordar a tu contenedor.

--env-file ./.env: Crucial. Carga todas las variables de tu archivo .env dentro del contenedor. Así es como la API dentro del contenedor obtiene las credenciales de la base de datos y la API de OpenAI.

carblau-agent:v1: El nombre de la imagen a usar.
```

Nota: Realizo cambios en el `.env` ya que cuando un contenedor Docker se ejecuta en tu máquina, no puede acceder a localhost o `127.0.0.1` para encontrar el proxy. En su lugar, debes usar un DNS especial que Docker proporciona: `host.docker.internal`

```bash
docker build -t carblau-agent:v1 .
```

```bash
docker build --no-cache -t carblau-agent:v1 .
```

```bash
docker run -d -p 8000:8080 --name carblau-api-container --env-file ./.env carblau-agent:v1
```

```bash
docker logs carblau-api-container / docker logs -f carblau-api-container
```

```bash
docker stop carblau-api-container
```

```bash
docker rm carblau-api-container
```

Este ciclo de `build` -> `run` -> `test` -> `logs` -> `stop/rm` es el flujo de trabajo estándar de Docker y dará confianza alta en lo que voy a subir a Cloud Run funciona.

``` bash
gcloud secrets versions access latest --secret=DB_PASSWORD
```

``` bash
 gcloud iam service-accounts list
```

#### Construir la imagen con arquitectura linux/amd64:
Docker  construye la imagen no para la arquitectura de tu Mac, sino para la arquitectura de Cloud Run (linux/amd64). La herramienta moderna para esto es docker buildx.

Paso 1: Reconstruir Y Subir la Imagen para la Arquitectura Correcta
Reemplazar el comando docker build y docker push con un solo comando docker buildx que hace ambas cosas y especifica la plataforma correcta.

Este es el único comando que necesitas ejecutar ahora. Reemplaza [TU_ID_DE_PROYECTO] y asegúrate de estar en el directorio MVP_CARMENTOR.

``` bash
 docker buildx build --platform linux/amd64 \
  -t europe-west1-docker.pkg.dev/[TU_ID_DE_PROYECTO]/carblau-repo/carblau-agent-api:v1 \
  --push .
  ``` 

- Ejecutar comando para crear nueva imagen y hacer push al GCP
  
``` bash
docker buildx build --platform linux/amd64 \
  -t europe-west1-docker.pkg.dev/thecarmentor-mvp2/carblau-repo/carblau-agent-api:v1 \
  --push .
  ```

Crear/validar que el repositorio en artifact registry este creado

Valido la creacion:

``` bash
  gcloud artifacts repositories list --location=europe-west1
```

#### ¿Qué es Cloud Build y por qué deberías usarlo?

Piensa en Cloud Build como un robot en la nube que trabaja para ti. En lugar de ejecutar los comandos docker buildx y gcloud run deploy en tu propio ordenador, le das un archivo de instrucciones (`cloudbuild.yaml`) y Cloud Build ejecuta esos pasos por ti en los servidores de Google.

Ventajas Principales:

Rapidez y Consistencia: En lugar de recordar y ejecutar varios comandos, solo ejecutas uno. El proceso es siempre el mismo, reduciendo errores humanos.
No Depende de tu Máquina: La construcción de la imagen Docker ocurre en los servidores de Google (que usan arquitectura amd64). Esto significa que ya no necesitas usar docker buildx. El problema de la arquitectura desaparece para siempre.
CI/CD (Integración Continua / Despliegue Continuo): Este es el primer paso hacia una pipeline de `CI/CD` profesional. En el futuro, podrías configurar Cloud Build para que se ejecute automáticamente cada vez que haces un push a una rama específica en `GitHub`.

**Tu Flujo de Trabajo Automatizado**
El proceso para actualizar la aplicación es tan simple como:

Hacer cambios en tu código (Python, etc.).
Ejecutar:

``` bash
gcloud builds submit --config cloudbuild.yaml .
```

- Comando para ejecutar Cloud Run
``` bash
gcloud run deploy carblau-agent-api \
  --image="europe-west1-docker.pkg.dev/thecarmentor-mvp2/carblau-repo/carblau-agent-api:v1" \
  --region="europe-west1" \
  --platform="managed" \
  --allow-unauthenticated \
  --port="8000" \
  --service-account="carblau-run-sa@thecarmentor-mvp2.iam.gserviceaccount.com" \
  --add-cloudsql-instances="thecarmentor-mvp2:europe-west1:carblau-sql-instance" \
  --set-env-vars="DB_HOST=/cloudsql/thecarmentor-mvp2:europe-west1:carblau-sql-instance" \
  --set-secrets="DB_USER=DB_USER:latest,DB_PASSWORD=DB_PASSWORD:latest,DB_NAME=DB_NAME:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest" \
  --timeout=600s
```

Nota: por ahora omito una mejor maquina   --memory=2Gi \ --cpu=2 y dejo --allow-unauthenticated para que cualquiera pueda usarla api sin autenticarse.

#### Mejorando la maquina

gcloud run deploy carblau-agent-api \
  --image="europe-west1-docker.pkg.dev/thecarmentor-mvp2/carblau-repo/carblau-agent-api:v1" \
  --region="europe-west1" \
  --platform="managed" \
  --allow-unauthenticated \
  --port="8000" \
  --service-account="carblau-run-sa@thecarmentor-mvp2.iam.gserviceaccount.com" \
  --add-cloudsql-instances="thecarmentor-mvp2:europe-west1:carblau-sql-instance" \
  --set-env-vars="DB_HOST=/cloudsql/thecarmentor-mvp2:europe-west1:carblau-sql-instance" \
  --set-secrets="DB_USER=DB_USER:latest,DB_PASSWORD=DB_PASSWORD:latest,DB_NAME=DB_NAME:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest" \
  --timeout=600s \
  --cpu=2 \
  --memory=1Gi
