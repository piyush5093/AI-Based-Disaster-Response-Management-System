from fastapi import APIRouter, HTTPException
from typing import List
from beanie import PydanticObjectId
from app.models.disaster_event import DisasterEvent
from app.services.gdacs_service import fetch_and_store_gdacs_events
from app.services.usgs_service import fetch_and_store_usgs_events
from app.services.ndma_service import fetch_and_store_ndma_events

router = APIRouter(prefix="/api/disaster-events", tags=["Disaster Events"])

@router.post("/sync-gdacs")
async def sync_gdacs_events():
    try:
        summary = await fetch_and_store_gdacs_events()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync GDACS feed: {str(e)}")

@router.post("/sync-usgs")
async def sync_usgs_events():
    try:
        summary = await fetch_and_store_usgs_events()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync USGS feed: {str(e)}")

@router.post("/sync-ndma")
async def sync_ndma_events():
    try:
        summary = await fetch_and_store_ndma_events()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync NDMA feed: {str(e)}")

@router.get("")
async def get_disaster_events():
    # Return most recent 50 events, sorted by event_date descending
    events = await DisasterEvent.find().sort("-event_date").limit(50).to_list()
    return events

@router.get("/{event_id}")
async def get_disaster_event(event_id: PydanticObjectId):
    event = await DisasterEvent.get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Disaster event not found")
    return event
