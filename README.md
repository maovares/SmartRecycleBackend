# SmartRecycleBackend — API REST

> Servicio REST que provee clasificación inteligente de residuos mediante visión por computadora (Google Gemini 2.5 Flash) y localización de centros de acopio (Google Places API), con autenticación delegada a Firebase.

---

## Tabla de Contenidos

1. [Descripción General](#1-descripción-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Stack Tecnológico](#3-stack-tecnológico)
4. [Requisitos del Entorno](#4-requisitos-del-entorno)
5. [Estructura del Proyecto](#5-estructura-del-proyecto)
6. [Endpoints de la API](#6-endpoints-de-la-api)
7. [Módulos Internos](#7-módulos-internos)
8. [Integración con Gemini 2.5 Flash](#8-integración-con-gemini-25-flash)
9. [Integración con Google Places](#9-integración-con-google-places)
10. [Autenticación y Seguridad](#10-autenticación-y-seguridad)
11. [Modelos de Datos (Schemas)](#11-modelos-de-datos-schemas)
12. [Configuración e Instalación](#12-configuración-e-instalación)
13. [Variables de Entorno](#13-variables-de-entorno)
14. [Despliegue en Render.com](#14-despliegue-en-rendercom)
15. [Manejo de Errores](#15-manejo-de-errores)

---

## 1. Descripción General

**SmartRecycleBackend** es una API REST asíncrona construida con **FastAPI** (Python) que actúa como capa de orquestación entre la aplicación móvil SmartRecycleAI y los servicios de inteligencia artificial y geolocalización.

Sus responsabilidades principales son:

| Responsabilidad | Implementación |
|---|---|
| Verificar la identidad del usuario | Firebase Admin SDK (ID Token JWT) |
| Clasificar imágenes de residuos | Google Gemini 2.5 Flash (Vision AI) |
| Localizar centros de reciclaje cercanos | Google Places API Nearby Search |
| Proveer respuestas tipadas y consistentes | Pydantic v2 schemas |

El backend no persiste datos por sí mismo — la persistencia es responsabilidad exclusiva de Firebase Firestore en el cliente móvil.

---

## 2. Arquitectura del Sistema

### 2.1 Diagrama de Flujo General

```
┌────────────────────┐
│  SmartRecycleAI    │
│  (React Native)    │
│                    │
│  Authorization:    │
│  Bearer {idToken}  │
└─────────┬──────────┘
          │ HTTPS
          ▼
┌─────────────────────────────────────────────────────────┐
│                  SmartRecycleBackend                    │
│                     (FastAPI)                           │
│                                                         │
│  main.py ──▶ CORS Middleware ──▶ Routers                │
│                                                         │
│  ┌─────────────────────┐  ┌────────────────────────┐   │
│  │    /ai Router       │  │   /centers Router      │   │
│  │                     │  │                        │   │
│  │ POST /analyze-image │  │ GET /nearby            │   │
│  │      │              │  │      │                 │   │
│  │      ▼              │  │      ▼                 │   │
│  │ firebase_auth.py    │  │ firebase_auth.py        │   │
│  │ (verifica token)    │  │ (verifica token)        │   │
│  │      │              │  │      │                 │   │
│  │      ▼              │  │      ▼                 │   │
│  │  gemini.py          │  │  Google Places API      │   │
│  │  (Gemini 2.5 Flash) │  │  (Nearby Search)        │   │
│  └─────────────────────┘  └────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
          │                           │
          ▼                           ▼
┌──────────────────┐        ┌──────────────────────┐
│  Google Gemini   │        │  Google Places API   │
│  2.5 Flash       │        │  Nearby Search       │
│  (Vision AI)     │        │  (Geolocalización)   │
└──────────────────┘        └──────────────────────┘
```

### 2.2 Arquitectura de Capas

```
┌──────────────────────────────────────────┐
│         CAPA DE TRANSPORTE               │
│  Uvicorn ASGI Server · TLS en Render     │
├──────────────────────────────────────────┤
│         CAPA DE API (FastAPI)            │
│  Routers: /ai · /centers                 │
│  CORS Middleware                         │
│  Validación automática (Pydantic)        │
├──────────────────────────────────────────┤
│         CAPA DE SERVICIOS                │
│  gemini.py — Orquestación Gemini AI      │
│  firebase_auth.py — Verificación JWT     │
├──────────────────────────────────────────┤
│         CAPA DE INTEGRACIONES            │
│  Google Generative AI SDK                │
│  Firebase Admin SDK                      │
│  httpx (async HTTP client)               │
│  Pillow (procesamiento de imagen)        │
└──────────────────────────────────────────┘
```

### 2.3 Flujo de Análisis de Imagen (Detalle)

```
Cliente envía:
  POST /ai/analyze-image
  Authorization: Bearer {Firebase ID Token}
  Body: multipart/form-data { image: File }
         │
         ▼
  1. Extraer token del header Authorization
         │
         ▼
  2. firebase_auth.verify_token(token)
     ├── Firebase Admin SDK verifica firma JWT
     ├── Comprueba expiración (< 1 hora)
     └── Retorna payload con uid, email
         │
         ▼
  3. Validar imagen:
     ├── Tamaño ≤ 10 MB
     └── MIME: image/jpeg | image/png | image/webp | image/heic
         │
         ▼
  4. gemini.analyze_image(image_bytes)
     ├── Construir prompt estructurado (JSON estricto)
     ├── Llamar a Gemini 2.5 Flash con imagen + texto
     ├── Parsear respuesta JSON
     └── Fallback si el parsing falla
         │
         ▼
  5. Retornar AnalysisResponse (Pydantic)
     {
       material, object, recyclable,
       instructions[3], impact, points
     }
```

---

## 3. Stack Tecnológico

### 3.1 Framework y Servidor

| Tecnología | Versión | Rol |
|---|---|---|
| **Python** | 3.11+ | Lenguaje de programación |
| **FastAPI** | 0.115.5 | Framework web asíncrono (ASGI) |
| **Uvicorn** | 0.32.1 | Servidor ASGI de alta performance |
| **Pydantic** | v2 (incluido en FastAPI) | Validación y serialización de datos |
| **python-multipart** | 0.0.12 | Soporte para form-data y subida de archivos |

### 3.2 Inteligencia Artificial

| Tecnología | Versión | Rol |
|---|---|---|
| **google-generativeai** | 0.8.3 | SDK oficial de Google Gemini |
| **Gemini 2.5 Flash** | modelo | Clasificación multimodal (imagen + texto) |
| **Pillow** | 11.0.0 | Decodificación y validación de imágenes |

### 3.3 Autenticación y Seguridad

| Tecnología | Versión | Rol |
|---|---|---|
| **firebase-admin** | 6.6.0 | Verificación de Firebase ID Tokens (JWT) |

### 3.4 HTTP y Utilidades

| Tecnología | Versión | Rol |
|---|---|---|
| **httpx** | 0.27.2 | Cliente HTTP asíncrono (llamadas a Places API) |
| **python-dotenv** | 1.0.1 | Carga de variables de entorno desde `.env` |

### 3.5 Despliegue

| Tecnología | Rol |
|---|---|
| **Render.com** | Plataforma de hosting (PaaS) |
| **render.yaml** | Infraestructura como código (IaC) |

---

## 4. Requisitos del Entorno

### 4.1 Requisitos de Desarrollo Local

| Requisito | Versión | Notas |
|---|---|---|
| **Python** | 3.11+ | Recomendado: 3.12 |
| **pip** | 23+ | Gestor de paquetes |
| **virtualenv** / **venv** | cualquiera | Entorno aislado |

### 4.2 Cuentas y Claves de API

| Servicio | Clave / Recurso | URL |
|---|---|---|
| **Google AI Studio** | `GEMINI_API_KEY` | aistudio.google.com |
| **Firebase Admin** | Service Account JSON | console.firebase.google.com → Configuración → Cuentas de servicio |
| **Google Cloud Console** | `GOOGLE_PLACES_API_KEY` | console.cloud.google.com → APIs → Places API |

#### Configuración de Firebase Admin

1. Ir a Firebase Console → Configuración del proyecto → Cuentas de servicio.
2. Generar nueva clave privada → descargar JSON.
3. Copiar el contenido del JSON completo como valor de `FIREBASE_SERVICE_ACCOUNT_JSON`.

#### Configuración de Google Places API

1. Habilitar **Places API (New)** en Google Cloud Console.
2. Crear una API Key con restricción de IP (para producción).
3. Habilitar **Maps JavaScript API** si se planea integración web futura.

---

## 5. Estructura del Proyecto

```
SmartRecycleBackend/
├── routers/
│   ├── ai.py              # Endpoint POST /ai/analyze-image
│   └── centers.py         # Endpoint GET /centers/nearby
├── services/
│   ├── gemini.py          # Lógica de análisis con Gemini 2.5 Flash
│   └── firebase_auth.py   # Verificación de Firebase ID Tokens
├── models/
│   └── schemas.py         # Modelos Pydantic de request/response
├── main.py                # Inicialización de FastAPI, CORS, routers
├── requirements.txt       # Dependencias Python
├── render.yaml            # Configuración de despliegue en Render.com
├── .env                   # Variables de entorno (no commitear)
└── .env.example           # Plantilla de variables de entorno
```

---

## 6. Endpoints de la API

### 6.1 Health Check

```http
GET /health
```

**Response 200:**
```json
{
  "status": "ok",
  "service": "smart-recycle-api"
}
```

---

### 6.2 Análisis de Imagen con IA

```http
POST /ai/analyze-image
Authorization: Bearer {Firebase_ID_Token}
Content-Type: multipart/form-data
```

**Body (form-data):**

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `image` | File | Sí | Imagen del residuo (JPEG, PNG, WebP, HEIC) |

**Restricciones:**
- Tamaño máximo: 10 MB
- Tipos MIME soportados: `image/jpeg`, `image/png`, `image/webp`, `image/heic`

**Response 200:**
```json
{
  "material": "PET",
  "object": "Botella de refresco plástica",
  "recyclable": true,
  "instructions": [
    "Enjuaga la botella para eliminar residuos de líquido.",
    "Aplástala para reducir su volumen y retira la tapa.",
    "Deposítala en el contenedor amarillo o llévala al centro de acopio más cercano."
  ],
  "impact": {
    "co2_kg": 0.35,
    "water_l": 12.5
  },
  "points": 7
}
```

**Códigos de Error:**

| Código | Descripción |
|---|---|
| 401 | Token ausente, inválido o expirado |
| 413 | Imagen supera 10 MB |
| 415 | Tipo de archivo no soportado |
| 502 | Error en la API de Gemini |
| 500 | Error interno del servidor |

---

### 6.3 Centros de Acopio Cercanos

```http
GET /centers/nearby?lat={latitude}&lng={longitude}&radius={metros}
Authorization: Bearer {Firebase_ID_Token}
```

**Query Parameters:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `lat` | float | requerido | Latitud del usuario |
| `lng` | float | requerido | Longitud del usuario |
| `radius` | int | 20000 | Radio de búsqueda en metros (máx. 50000) |

**Response 200:**
```json
{
  "centers": [
    {
      "id": "ChIJxxxxxxxxxxxxxxxx",
      "name": "Centro de Acopio CEMPET",
      "address": "Av. 10, San José, Costa Rica",
      "distance_km": 1.23,
      "lat": 9.9341,
      "lng": -84.0875,
      "open_now": true
    }
  ]
}
```

**Deduplicación:** Los resultados de múltiples búsquedas paralelas se combinan y deduplican por `place_id`.  
**Ordenamiento:** Por `distance_km` ascendente (más cercano primero).

---

## 7. Módulos Internos

### 7.1 `main.py`

Punto de entrada de la aplicación FastAPI.

```python
FastAPI(
    title="Smart Recycle AI API",
    version="1.0.0"
)

# CORS: permite cualquier origen (desarrollo/producción)
CORSMiddleware(
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Routers
app.include_router(ai_router,      prefix="/ai")
app.include_router(centers_router, prefix="/centers")
```

### 7.2 `services/firebase_auth.py`

Verifica la autenticidad del Firebase ID Token usando el SDK Admin.

```python
firebase_admin.initialize_app(
    credentials.Certificate(service_account_dict)
)

def verify_token(token: str) -> dict:
    """
    Verifica el token JWT de Firebase.
    Retorna el payload decodificado (uid, email, ...).
    Lanza HTTPException 401 si el token es inválido o expirado.
    """
    return auth.verify_id_token(token)
```

### 7.3 `services/gemini.py`

Orquesta la llamada al modelo Gemini 2.5 Flash con la imagen y el prompt estructurado.

**Categorías de material reconocidas (17 tipos):**

```
PET, HDPE, PVC, LDPE, PP, PS, Aluminio, Vidrio,
Papel, Cartón, Tetra Pak, Electrónico, Orgánico,
Textil, Metal ferroso, Caucho, Residuo no reciclable
```

**Estrategia de Prompt:**
- Respuesta solo en JSON (sin markdown, sin texto libre)
- Campos requeridos con tipos explícitos
- Instrucciones adaptadas al contexto de Costa Rica
- Cálculo de impacto ambiental realista por material
- Asignación de EcoPoints (1–10) por tipo y reciclabilidad
- Fallback JSON si el parsing de la respuesta falla

### 7.4 `routers/ai.py`

```python
@router.post("/analyze-image", response_model=AnalysisResponse)
async def analyze_image(
    image: UploadFile = File(...),
    token_payload: dict = Depends(verify_token_dependency)
):
    # 1. Validar tamaño y tipo MIME
    # 2. Leer bytes de la imagen
    # 3. Llamar a gemini.analyze_image()
    # 4. Retornar AnalysisResponse
```

### 7.5 `routers/centers.py`

```python
@router.get("/nearby", response_model=CentersResponse)
async def get_nearby_centers(
    lat: float, lng: float, radius: int = 20000,
    token_payload: dict = Depends(verify_token_dependency)
):
    # 1. Validar radio (máx. 50000m)
    # 2. Búsquedas paralelas en Places API (4 keywords)
    # 3. Deduplicar por place_id
    # 4. Calcular distancias (fórmula de Haversine)
    # 5. Ordenar por distancia y retornar
```

---

## 8. Integración con Gemini 2.5 Flash

### 8.1 Modelo Utilizado

```
gemini-2.5-flash
```

Características relevantes para este caso de uso:

| Característica | Valor |
|---|---|
| Tipo | Multimodal (texto + imagen) |
| Velocidad | Flash (baja latencia) |
| Entrada de imagen | Bytes en base64 o URL |
| Salida | Texto libre (forzado a JSON por prompt) |
| Contexto máximo | 1M tokens |

### 8.2 Estructura del Prompt

El prompt instruye al modelo a:

1. **Identificar** el material principal de la imagen (entre las 17 categorías).
2. **Describir** el objeto en español (max 50 caracteres).
3. **Determinar** si es reciclable en Costa Rica.
4. **Generar** exactamente 3 instrucciones de disposición, adaptadas a la infraestructura local (centros de acopio, contenedores de color, municipalidades).
5. **Calcular** el impacto ambiental estimado (`co2_kg`, `water_l`).
6. **Asignar** EcoPoints (1–10) basado en la dificultad y valor del reciclaje.
7. **Responder únicamente en JSON** sin envoltura de markdown.

### 8.3 Ejemplo de Llamada al Modelo

```python
model = genai.GenerativeModel("gemini-2.5-flash")

response = model.generate_content([
    {
        "mime_type": "image/jpeg",
        "data": image_bytes
    },
    prompt_text  # instrucción estructurada
])

result = json.loads(response.text)
```

---

## 9. Integración con Google Places

### 9.1 API Utilizada

```
Places API (Nearby Search)
Endpoint: https://maps.googleapis.com/maps/api/place/nearbysearch/json
```

### 9.2 Keywords de Búsqueda (Paralelas)

Se realizan **4 búsquedas simultáneas** con `asyncio.gather()` para maximizar la cobertura:

| Keyword | Tipo de lugar buscado |
|---|---|
| `"centro de acopio"` | Centros formales de acopio de reciclaje |
| `"reciclaje"` | Puntos genéricos de reciclaje |
| `"punto limpio"` | Puntos limpios municipales |
| `"acopio residuos"` | Centros de acopio de residuos sólidos |

### 9.3 Fórmula de Haversine

La distancia entre el usuario y cada centro se calcula con la fórmula de Haversine para obtener la distancia en la superficie esférica de la Tierra:

```python
def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371  # Radio de la Tierra en km
    φ1, φ2 = radians(lat1), radians(lat2)
    Δφ = radians(lat2 - lat1)
    Δλ = radians(lon2 - lon1)
    a = sin(Δφ/2)**2 + cos(φ1)*cos(φ2)*sin(Δλ/2)**2
    return R * 2 * asin(sqrt(a))
```

---

## 10. Autenticación y Seguridad

### 10.1 Flujo de Verificación de Token

```
Request HTTP
    │
    ▼
Header: Authorization: Bearer {idToken}
    │
    ▼
firebase_auth.verify_token(idToken)
    │
    ├── Token válido: retorna payload { uid, email, ... }
    │
    └── Token inválido / expirado:
        HTTPException(status_code=401, detail="Token inválido o expirado")
```

### 10.2 Dependency Injection (FastAPI)

```python
async def verify_token_dependency(
    authorization: str = Header(...)
) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authorization header inválido")
    token = authorization.split(" ")[1]
    return verify_token(token)
```

Todos los endpoints protegidos declaran `Depends(verify_token_dependency)`.

### 10.3 CORS

```python
allow_origins=["*"]  # Abierto para desarrollo
```

En producción se recomienda restringir a los dominios del cliente:

```python
allow_origins=["https://your-app.expo.dev", "exp://..."]
```

---

## 11. Modelos de Datos (Schemas)

### 11.1 `AnalysisResponse`

```python
class ImpactData(BaseModel):
    co2_kg: float
    water_l: Optional[float] = None

class AnalysisResponse(BaseModel):
    material: str       # Tipo de material (ej. "PET")
    object: str         # Descripción del objeto
    recyclable: bool    # True si es reciclable en Costa Rica
    instructions: list[str]   # Exactamente 3 instrucciones
    impact: ImpactData        # Impacto ambiental estimado
    points: int               # EcoPoints asignados (1–10)
```

### 11.2 `CenterItem`

```python
class CenterItem(BaseModel):
    id: str             # Google Places place_id
    name: str           # Nombre del establecimiento
    address: str        # Dirección (vicinity)
    distance_km: float  # Distancia al usuario (Haversine)
    lat: float          # Latitud
    lng: float          # Longitud
    open_now: bool      # Estado actual de apertura
```

### 11.3 `CentersResponse`

```python
class CentersResponse(BaseModel):
    centers: list[CenterItem]
```

---

## 12. Configuración e Instalación

### 12.1 Clonar el Repositorio

```bash
git clone <repo-url>
cd SmartRecycle/SmartRecycleBackend
```

### 12.2 Crear y Activar Entorno Virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar en Linux/macOS
source venv/bin/activate

# Activar en Windows (PowerShell)
.\venv\Scripts\Activate.ps1
```

### 12.3 Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 12.4 Configurar Variables de Entorno

```bash
cp .env.example .env
# Editar .env con los valores reales
```

### 12.5 Ejecutar en Desarrollo

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

La documentación interactiva estará disponible en:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 13. Variables de Entorno

| Variable | Requerida | Descripción |
|---|---|---|
| `GEMINI_API_KEY` | Sí | API Key de Google AI Studio para Gemini |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Sí | JSON completo de la cuenta de servicio de Firebase Admin (como string) |
| `GOOGLE_PLACES_API_KEY` | Sí | API Key de Google Cloud para Places API |

### Ejemplo de `.env`

```env
GEMINI_API_KEY=AIza...

FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"smartrecycle-...","private_key_id":"...","private_key":"-----BEGIN RSA PRIVATE KEY-----\n..."}

GOOGLE_PLACES_API_KEY=AIza...
```

> **Seguridad:** Nunca commitear el archivo `.env`. Está incluido en `.gitignore`. En Render.com, las variables se configuran desde el dashboard con `sync: false`.

---

## 14. Despliegue en Render.com

### 14.1 Configuración (`render.yaml`)

```yaml
services:
  - type: web
    name: smart-recycle-api
    env: python
    region: oregon
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: GEMINI_API_KEY
        sync: false
      - key: FIREBASE_SERVICE_ACCOUNT_JSON
        sync: false
      - key: GOOGLE_PLACES_API_KEY
        sync: false
```

### 14.2 Pasos de Despliegue

1. Hacer fork o push del repositorio a GitHub.
2. Crear un nuevo **Web Service** en [render.com](https://render.com).
3. Conectar el repositorio de GitHub.
4. Render detecta automáticamente `render.yaml`.
5. Configurar las tres variables de entorno en el dashboard de Render.
6. El servicio se despliega automáticamente en cada push a `main`.

### 14.3 Consideraciones del Plan Gratuito

| Limitación | Valor |
|---|---|
| RAM | 512 MB |
| CPU | compartida |
| Sleep tras inactividad | 15 minutos |
| Tiempo de arranque (cold start) | ~30 segundos |
| Ancho de banda mensual | 100 GB |

El cold start puede afectar la primera solicitud tras un período de inactividad. El cliente móvil maneja esto con un timeout extendido en la primera llamada.

---

## 15. Manejo de Errores

### 15.1 Tabla de Códigos HTTP

| Código | Origen | Descripción |
|---|---|---|
| `200` | Todos los endpoints | Éxito |
| `401` | Todos los endpoints | Token ausente, inválido o expirado |
| `413` | `/ai/analyze-image` | Imagen supera 10 MB |
| `415` | `/ai/analyze-image` | Tipo de archivo no soportado |
| `422` | Todos los endpoints | Error de validación de parámetros (Pydantic) |
| `500` | Todos los endpoints | Error interno inesperado |
| `502` | `/ai/analyze-image` | Error en la API de Gemini |

### 15.2 Formato de Error Estándar (FastAPI)

```json
{
  "detail": "Token inválido o expirado"
}
```

### 15.3 Fallback de Gemini

Si la respuesta de Gemini no puede parsearse como JSON válido, el servicio retorna un JSON de fallback estructurado indicando que el ítem no pudo clasificarse, evitando un error 500.

---

## Créditos y Licencia

Desarrollado como proyecto de investigación aplicada para la gestión de residuos sólidos en Costa Rica, integrando técnicas de visión por computadora e inteligencia artificial generativa para el fomento de hábitos de reciclaje.

**Autor:** Miguel Ángel Rodríguez Ovares  
**Correo:** mrodriguezovares@gmail.com  
**Año:** 2025–2026
