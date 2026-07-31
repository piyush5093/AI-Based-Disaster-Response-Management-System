from datetime import datetime
from typing import Any, Dict, List
from pydantic import Field
from beanie import Document
from pymongo import IndexModel, ASCENDING, GEOSPHERE

class DisasterEvent(Document):
    source: str
    event_type: str
    title: str
    description: str
    alert_level: str
    location: Dict[str, Any]  # GeoJSON Point: {"type": "Point", "coordinates": [lon, lat]}
    event_date: datetime
    external_id: str
    raw_data: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    normalized: bool = False
    normalization_warnings: List[str] = Field(default_factory=list)
    impact_extent: Dict[str, Any] | None = None
    estimated_population_exposed: int | None = None
    building_count: int | None = None
    critical_infrastructure_count: int | None = None

    class Settings:
        name = "disaster_events"
        indexes = [
            IndexModel([("location", GEOSPHERE)]),
            IndexModel([("external_id", ASCENDING)], unique=True)
        ]
