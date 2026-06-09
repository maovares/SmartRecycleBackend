import os
import math
import time
import asyncio
import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

# ── Search config ────────────────────────────────────────────────────────────
DEFAULT_RADIUS_M = 20_000          # 20 km — reasonable for car travel
MAX_RADIUS_M     = 50_000          # hard cap exposed to callers

SEARCH_KEYWORDS = [
    "centro de acopio",
    "reciclaje",
]
# ────────────────────────────────────────────────────────────────────────────

PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

# ── Persistent HTTP client (reuses TLS connections across requests) ───────────
_http = httpx.AsyncClient(timeout=10)

# ── Server-side in-memory cache keyed by ~1 km coordinate bucket + radius ────
_cache: dict[str, tuple[list, float]] = {}
_CACHE_TTL = 1800  # 30 minutes


def _cache_key(lat: float, lng: float, radius: int) -> str:
    return f"{round(lat, 2)},{round(lng, 2)},{radius}"


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

    key = _cache_key(lat, lng, radius)
    cached = _cache.get(key)
    if cached and time.time() - cached[1] < _CACHE_TTL:
        return {"centers": cached[0]}

    responses = await asyncio.gather(
        *[_search_keyword(_http, lat, lng, radius, kw) for kw in SEARCH_KEYWORDS]
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

        results.append({
            "id": place.get("place_id"),
            "name": place.get("name"),
            "address": place.get("vicinity"),
            "distance_km": distance_km,
            "lat": place_lat,
            "lng": place_lng,
            "open_now": hours.get("open_now"),
        })

    results.sort(key=lambda c: c["distance_km"] if c["distance_km"] is not None else 9999)
    _cache[key] = (results, time.time())
    return {"centers": results}
