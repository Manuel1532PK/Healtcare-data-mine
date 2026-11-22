# Guía de despliegue interactivo

Todo lo necesario para publicar los resultados vive en esta carpeta. No tocamos `src/`, `outputs/`, `docs/` ni el `README.md` principal.

## Arquitectura

```
Navegador (Netlify)
   ↓ peticiones HTTP
API FastAPI (Render)
   ↓ descarga archivos
Azure Blob Storage
```

- **Azure** guarda copias de los CSV, tablas, imagen y modelos.
- **Render** ejecuta la API. Solo lee datos.
- **Netlify** publica la página interactiva.

## Estructura

```text
deployment/
├── backend/
│   ├── main.py              # API FastAPI
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── config.js            # URL del backend
├── azure/
│   ├── exportar_modelo.py   # genera los artefactos
│   ├── subir_datos.ps1      # sube copias a Azure
│   └── artefactos/          # generado, no editar a mano
└── GUIA.md
```

## 1. Prueba en la computadora, sin Azure

El modo local lee los archivos del repositorio. No necesita credenciales.

```powershell
cd deployment/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:MODO_LOCAL="1"
$env:FRONTEND_URL="*"
uvicorn main:app --reload --port 8000
```

En otra terminal:

```powershell
cd deployment/frontend
python -m http.server 8080
```

Abrimos `http://localhost:8080`. La URL del backend ya viene en `config.js`.

Si cambiamos `config.js` para una IP distinta, recargamos la página.

### Pruebas rápidas de la API

```powershell
curl http://localhost:8000/health
curl "http://localhost:8000/datos/conteo?grupo=2&etiqueta=1"
curl "http://localhost:8000/clustering/corte?altura=100"
curl "http://localhost:8000/clasificacion/desacuerdos?k=1&limit=5"
```

## 2. Preparar los artefactos

Si aún no existen:

```powershell
python deployment/azure/exportar_modelo.py
```

Eso crea modelos, columnas, enlaces del dendrograma y copias de los reportes dentro de `deployment/azure/artefactos/`. Los originales no se tocan.

## 3. Subir los datos a Azure

Necesitamos Azure CLI y una cuenta con permisos.

```powershell
az login

.\deployment\azure\subir_datos.ps1 -AccountName stnhanesdemoTUDI
```

El nombre del storage account debe ser único en el mundo, minúsculas, entre 3 y 24 caracteres, sin guiones.

El script imprime al final la cadena de conexión. La copiamos para Render.

## 4. Publicar el backend en Render

1. **New → Web Service** y conectamos el repositorio de GitHub.
2. Root Directory: `deployment/backend`
3. Runtime: Python 3.11 o superior.
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Plan: Free.
7. Variables de entorno:
   - `MODO_LOCAL=0`
   - `AZURE_STORAGE_CONNECTION_STRING=` (la del paso anterior)
   - `AZURE_CONTAINER=nhanes`
   - `FRONTEND_URL=` (la URL que nos dé Netlify)

Render se duerme tras inactividad en el plan gratuito. Abrimos la página unos minutos antes de la exposición.

## 5. Publicar el frontend en Netlify

Antes de subir, cambiamos `deployment/frontend/config.js`:

```javascript
window.BACKEND_URL = "https://TU-BACKEND.onrender.com";
```

Luego, en `app.netlify.com/drop`, arrastramos la carpeta `deployment/frontend`. Netlify devuelve una URL con HTTPS. Esa URL la ponemos en `FRONTEND_URL` dentro de Render y guardamos.

## 6. Cómo usar la página

- **En simple:** cifras grandes, frases claras, filtros y formularios.
- **Con números:** tablas exactas, métricas, matrices de confusión y descargas.
- **Filtros:** grupo, respuesta, sexo y rango de edad. Las tarjetas y la tabla se actualizan mientras se mueve el control, sin recargar.
- **Clasificación:** cada opción de "cuántos parecidos mira" tiene sus propios números guardados en `clasificacion_detalle_k.csv`. Al cambiarla se actualizan el acierto, la tabla, la matriz, los desacuerdos y la predicción del formulario. El formulario también responde al mover los deslizadores, sin necesidad de hacer clic.
- **Agrupamiento:** elegimos un grupo, cortamos el árbol a distintas alturas y probamos una persona.
- **Descarga:** el botón entrega un CSV con exactamente lo que estamos viendo.

## Endpoints

```text
GET  /health
GET  /resumen
GET  /metricas
GET  /clasificacion/desacuerdos?k=51&limit=20
POST /clasificacion/predecir
GET  /clustering/perfil?grupo=0
GET  /clustering/muestra?grupo=0&etiqueta=1&limit=20
GET  /datos/conteo?grupo=0&etiqueta=1&edad_min=-2&edad_max=2&sexo=1
POST /clustering/predecir
GET  /clustering/comparacion
GET  /clustering/corte?altura=100
GET  /figura/dendrograma
GET  /datos/descarga?grupo=0&etiqueta=1
```

## Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| La página no carga datos | `config.js` apunta a la URL equivocada | Poner la URL real de Render |
| Error de CORS | Falta la URL de Netlify en Render | Actualizar `FRONTEND_URL` y reiniciar |
| `No encontramos archivo` | Faltan artefactos en Azure | Correr `exportar_modelo.py` y `subir_datos.ps1` |
| Primera llamada muy lenta | Render gratuito se durmió | Abrir la página antes |

## Reglas que seguimos

- No modificamos los CSV de entrada.
- No hacemos commit ni push sin confirmación.
- Azure guarda copias; el repositorio sigue siendo la fuente.
- El backend nunca escribe en Azure.

## En palabras simples

Dejamos todo el despliegue en una carpeta aparte. Primero lo probamos en la computadora sin Azure. Después subimos copias de los datos a Azure, levantamos la API en Render y arrastramos la carpeta de la página a Netlify. La página permite mover filtros, probar valores y descargar lo que se está viendo. Nada de esto toca el trabajo que ya estaba terminado.
