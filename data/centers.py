CENTERS = [
    {
        "id": "1",
        "name": "EcoRec Sabana",
        "address": "Parque Metropolitano La Sabana, San José",
        "distance_km": 1.3,
        "materials": ["PET", "Aluminio", "Vidrio", "Papel"],
        "schedule": "Lun–Vie 7am–4pm",
        "phone": "+506 2256-1234",
        "lat": 9.9356,
        "lng": -84.1019,
    },
    {
        "id": "2",
        "name": "Centro Verde Desamparados",
        "address": "Av. 8, Desamparados, San José",
        "distance_km": 3.8,
        "materials": ["PET", "Cartón", "Papel", "Aluminio"],
        "schedule": "Lun–Sáb 6am–5pm",
        "phone": "+506 2259-5678",
        "lat": 9.8985,
        "lng": -84.0669,
    },
    {
        "id": "3",
        "name": "ReciclaHeredia",
        "address": "Mercado Central de Heredia, Heredia",
        "distance_km": 6.2,
        "materials": ["Vidrio", "PET", "Aluminio"],
        "schedule": "Mar–Sáb 8am–3pm",
        "phone": "+506 2261-9012",
        "lat": 9.9985,
        "lng": -84.1169,
    },
    {
        "id": "4",
        "name": "Punto Limpio Alajuela",
        "address": "Estadio Morera Soto, Alajuela",
        "distance_km": 9.4,
        "materials": ["PET", "Cartón", "Vidrio", "Papel", "Aluminio"],
        "schedule": "Lun–Vie 7am–5pm",
        "phone": "+506 2440-3456",
        "lat": 10.0162,
        "lng": -84.2141,
    },
    {
        "id": "5",
        "name": "EcoAcopio Cartago",
        "address": "Plaza Mayor, Cartago Centro",
        "distance_km": 12.1,
        "materials": ["Cartón", "Papel", "Aluminio"],
        "schedule": "Mié–Dom 8am–2pm",
        "phone": "+506 2552-7890",
        "lat": 9.8637,
        "lng": -83.9197,
    },
]


def find_nearest(material: str | None = None) -> dict:
    """Retorna el primer centro que acepta el material, o el primero de la lista."""
    if material:
        for c in CENTERS:
            if any(material.upper() in m.upper() for m in c["materials"]):
                return c
    return CENTERS[0]
