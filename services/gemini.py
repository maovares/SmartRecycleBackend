import os
import json
import re
import io
import google.generativeai as genai
from PIL import Image

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

_model = genai.GenerativeModel("gemini-2.5-flash")

_PROMPT = """Eres un experto en gestión de residuos y reciclaje. Analiza la imagen adjunta.
Responde ÚNICAMENTE con un objeto JSON válido. Sin markdown, sin texto adicional, sin explicaciones.

Estructura exacta requerida:
{
  "material": "<valor>",
  "object": "<nombre descriptivo del objeto>",
  "recyclable": <true o false>,
  "instructions": ["<paso 1>", "<paso 2>", "<paso 3>"],
  "impact": {
    "co2_kg": <número decimal>,
    "water_l": <número decimal>
  },
  "points": <entero 1-10>
}

Valores permitidos para "material":
PET, HDPE, PP, PS, PVC, Aluminio, Acero, Vidrio, Papel, Cartón, Orgánico, Electrónico, Textil, Compuesto, Desconocido

Reglas:
- instructions: exactamente 3 pasos, específicos y accionables para Costa Rica
- co2_kg: kg de CO2 equivalente evitados al reciclar este objeto (usa valores realistas)
- water_l: litros de agua ahorrados (usa valores realistas)
- points: 1-3 papel/cartón, 4-6 plásticos/aluminio, 7-10 electrónicos/compuestos
- Si la imagen no muestra un residuo reconocible, usa material "Desconocido" y recyclable false
"""

_FALLBACK = {
    "material": "Desconocido",
    "object": "No se pudo identificar el objeto",
    "recyclable": False,
    "instructions": [
        "Intenta tomar la foto con mejor iluminación",
        "Asegúrate de que el residuo ocupe la mayor parte del encuadre",
        "Consulta a tu centro de acopio local",
    ],
    "impact": {"co2_kg": 0.0, "water_l": 0.0},
    "points": 1,
}


def analyze_waste_image(image_bytes: bytes) -> dict:
    image = Image.open(io.BytesIO(image_bytes))

    response = _model.generate_content([_PROMPT, image])
    raw = response.text.strip()

    # Strip markdown code fences if Gemini adds them despite instructions
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try extracting the first {...} block as a last resort
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        return _FALLBACK
