from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header
from typing import Annotated
from models.schemas import AnalysisResponse, Impact, NearestCenter
from services import firebase_auth, gemini
from data.centers import find_nearest

router = APIRouter()

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}


async def _get_user(authorization: Annotated[str, Header()]) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Formato de token inválido. Usa: Bearer <token>")
    token = authorization.split(" ", 1)[1]
    try:
        return firebase_auth.verify_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Token inválido o expirado: {exc}")


@router.post("/analyze-image", response_model=AnalysisResponse)
async def analyze_image(
    image: UploadFile = File(...),
    authorization: Annotated[str, Header()] = "",
    lat: float | None = Form(None),
    lng: float | None = Form(None),
):
    # Auth
    user = await _get_user(authorization)

    # Validate file
    content_type = (image.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Tipo de imagen no soportado: {content_type}. Usa JPEG, PNG o WEBP.",
        )

    image_bytes = await image.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Imagen demasiado grande (máx 10 MB).")
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="El archivo de imagen está vacío.")

    # Analyze with Gemini
    try:
        result = gemini.analyze_waste_image(image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error al analizar con IA: {exc}")

    material = result.get("material", "Desconocido")
    center = find_nearest(material, lat, lng)

    return AnalysisResponse(
        material=material,
        object=result.get("object", "Objeto no identificado"),
        recyclable=bool(result.get("recyclable", False)),
        instructions=result.get("instructions", []),
        impact=Impact(
            co2_kg=float(result.get("impact", {}).get("co2_kg", 0.0)),
            water_l=float(result.get("impact", {}).get("water_l", 0.0)),
        ),
        nearest_center=NearestCenter(
            name=center["name"],
            distance_km=center["distance_km"],
        ),
        points=int(result.get("points", 5)),
    )
