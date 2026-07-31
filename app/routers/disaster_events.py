from fastapi import APIRouter, HTTPException
from typing import List
from beanie import PydanticObjectId
from app.models.disaster_event import DisasterEvent
from app.services.gdacs_service import fetch_and_store_gdacs_events
from app.services.usgs_service import fetch_and_store_usgs_events
from app.services.ndma_service import fetch_and_store_ndma_events
from app.services.normalization_service import run_normalization_pass
from app.services.impact_extent_service import run_impact_extent_pass
from app.services.population_service import run_population_exposure_pass

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

@router.post("/normalize")
async def normalize_events():
    try:
        summary = await run_normalization_pass()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to normalize events: {str(e)}")

@router.post("/calculate-impact-extents")
async def calculate_impact_extents():
    try:
        summary = await run_impact_extent_pass()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate impact extents: {str(e)}")

@router.post("/calculate-population-exposure")
async def calculate_population_exposure():
    try:
        summary = await run_population_exposure_pass()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate population exposure: {str(e)}")

@router.post("/calculate-building-footprints")
async def calculate_building_footprints(limit: int = 20):
    try:
        from app.services.building_footprint_service import run_building_footprint_pass
        summary = await run_building_footprint_pass(limit)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate building footprints: {str(e)}")

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

@router.get("/{event_id}/impact-extent")
async def get_disaster_event_impact_extent(event_id: PydanticObjectId):
    event = await DisasterEvent.get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Disaster event not found")
    if not event.impact_extent:
        raise HTTPException(status_code=404, detail="Impact extent not calculated for this event")
    return event.impact_extent

