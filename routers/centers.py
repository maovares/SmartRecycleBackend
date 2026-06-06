import os
import math
import asyncio
import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

# ── Search config ────────────────────────────────────────────────────────────
DEFAULT_RADIUS_M = 20_000          # 20 km — reasonable for car travel
MAX_RADIUS_M     = 50_000          # hard cap exposed to callers

# Multiple keywords are searched in parallel and deduplicated.
# Add or remove terms here to tune what Places returns.
SEARCH_KEYWORDS = [
    "centro de acopio",
    "reciclaje",
    "punto limpio",
    "acopio residuos",
]
# ────────────────────────────────────────────────────────────────────────────

PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


async def _search_keyword(client: httpx.AsyncClient, lat: float, lng: float, radius: int, keyword: str) -> list:
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "keyword": keyword,
        "key": PLACES_API_KEY,
    }
    resp = await client.get(NEARBY_URL, params=params)
    if resp.status_code != 200:
        return []
    data = resp.json()
    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        return []
    return data.get("results", [])


@router.get("/nearby")
async def nearby_centers(
    lat: float = Query(...),
    lng: float = Query(...),
    radius: int = Query(default=DEFAULT_RADIUS_M, le=MAX_RADIUS_M),
):
    if not PLACES_API_KEY:
        raise HTTPException(status_code=503, detail="Google Places API key not configured.")

    async with httpx.AsyncClient(timeout=10) as client:
        responses = await asyncio.gather(
            *[_search_keyword(client, lat, lng, radius, kw) for kw in SEARCH_KEYWORDS]
        )

    # Merge and deduplicate by place_id
    seen = set()
    merged = []
    for places in responses:
        for place in places:
            pid = place.get("place_id")
            if pid and pid not in seen:
                seen.add(pid)
                merged.append(place)

    results = []
    for place in merged:
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
