from datetime import datetime
from typing import Any, Dict, List
from pydantic import Field
from beanie import Document
from pymongo import IndexModel, ASCENDING, GEOSPHERE

class GridCell(Document):
    cell_id: str
    bounds: Dict[str, Any]  # GeoJSON Polygon
    center: Dict[str, Any]  # GeoJSON Point
    overlapping_event_ids: List[str] = Field(default_factory=list)
    total_population_exposed: int = 0
    total_building_count: int = 0
    max_alert_level: str = "Unknown"
    resource_count_nearby: int = 0
    severity_score: float = 0.0
    last_calculated: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "grid_cells"
        indexes = [
            IndexModel([("cell_id", ASCENDING)], unique=True),
            IndexModel([("center", GEOSPHERE)])
        ]
