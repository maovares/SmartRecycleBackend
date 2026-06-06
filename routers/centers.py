import os
import math
import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DETAILS_FIELDS = "name,vicinity,geometry,formatted_phone_number,opening_hours"


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


@router.get("/nearby")
async def nearby_centers(
    lat: float = Query(...),
    lng: float = Query(...),
    radius: int = Query(default=10000, le=50000),
):
    if not PLACES_API_KEY:
        raise HTTPException(status_code=503, detail="Google Places API key not configured.")

    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "keyword": "centro de acopio reciclaje",
        "key": PLACES_API_KEY,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(NEARBY_URL, params=params)

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Error al consultar Google Places.")

    data = resp.json()
    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        raise HTTPException(status_code=502, detail=f"Places API: {data.get('status')}")

    results = []
    for place in data.get("results", []):
        loc = place.get("geometry", {}).get("location", {})
        place_lat = loc.get("lat")
        place_lng = loc.get("lng")
        distance_km = round(_haversine(lat, lng, place_lat, place_lng), 1) if place_lat and place_lng else None

        hours = place.get("opening_hours", {})
        schedule = "Horario no disponible"
        if hours.get("weekday_text"):
            schedule = hours["weekday_text"][0]

        results.append({
            "id": place.get("place_id"),
            "name": place.get("name"),
            "address": place.get("vicinity"),
            "distance_km": distance_km,
            "lat": place_lat,
            "lng": place_lng,
            "schedule": schedule,
            "open_now": hours.get("open_now"),
        })

    results.sort(key=lambda c: c["distance_km"] if c["distance_km"] is not None else 9999)
    return {"centers": results}
