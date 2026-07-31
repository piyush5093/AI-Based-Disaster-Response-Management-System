from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from app.models.zone_grid import GridCell
from app.services.zone_classification_service import classify_zones_for_events

router = APIRouter(prefix="/api/zones", tags=["Zones"])

class ClassifyRequest(BaseModel):
    event_ids: Optional[List[str]] = None

@router.post("/classify")
async def classify_zones(req: ClassifyRequest = None):
    event_ids = req.event_ids if req else None
    result = await classify_zones_for_events(event_ids)
    return result

@router.get("", response_model=List[GridCell])
async def list_zones(
    min_severity: Optional[float] = Query(None, description="Minimum severity score"),
    limit: int = 50
):
    query = {}
    if min_severity is not None:
        query["severity_score"] = {"$gte": min_severity}
        
    cells = await GridCell.find(query).sort("-severity_score").limit(limit).to_list()
    return cells

@router.get("/{cell_id}", response_model=GridCell)
async def get_zone(cell_id: str):
    cell = await GridCell.find_one({"cell_id": cell_id})
    if not cell:
        raise HTTPException(status_code=404, detail="GridCell not found")
    return cell
