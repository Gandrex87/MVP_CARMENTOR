# Ejecutar tu Aplicación FastAPI

Abre tu terminal o línea de comandos.

Navega hasta el directorio donde guardaste main.py. Si lo pusiste en una subcarpeta api, navega a la carpeta que contiene api.

Ejecuta Uvicorn:

Si main.py está en la raíz de donde abriste la terminal:
Bash

```Bash
python -m uvicorn main:app --reload

```

Si main.py está en una subcarpeta api:

```Bash
python -m uvicorn api.main:app --reload
```

## Desglose del Comando

* uvicorn: El comando para iniciar el servidor Uvicorn.
* main:app (o api.main:app): Le dice a Uvicorn dónde encontrar la instancia de FastAPI.
* main: Es el archivo main.py (sin la extensión .py).
* app: Es el objeto app = FastAPI() que creaste dentro de main.py.
--reload: Esta opción es muy útil para desarrollo. Hace que el servidor se reinicie automáticamente cada vez que guardas un cambio en tu código. Para producción, no usarías --reload.