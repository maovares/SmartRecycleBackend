from pydantic import BaseModel
from typing import Optional


class Impact(BaseModel):
    co2_kg: float
    water_l: Optional[float] = None


class AnalysisResponse(BaseModel):
    material: str
    object: str
    recyclable: bool
    instructions: list[str]
    impact: Impact
    points: int
