from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.services.satellite_service import fetch_damage_imagery

router = APIRouter(prefix="/api/satellite", tags=["Satellite Imagery"])

class ImageryRequest(BaseModel):
    bbox: List[float]
    date_from: str
    date_to: str

@router.post("/damage-imagery")
async def get_damage_imagery(req: ImageryRequest):
    if len(req.bbox) != 4:
        raise HTTPException(status_code=400, detail="bbox must contain exactly 4 coordinates [minLon, minLat, maxLon, maxLat]")
        
    result = await fetch_damage_imagery(req.bbox, req.date_from, req.date_to)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result
