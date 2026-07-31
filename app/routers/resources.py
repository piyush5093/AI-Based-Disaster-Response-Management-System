from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from beanie import PydanticObjectId

from app.models.resource_inventory import (
    ResourceItem, 
    ResourceItemCreate, 
    ResourceItemUpdate,
    ResourceType,
    ResourceStatus
)

router = APIRouter(prefix="/api/resources", tags=["Resource Inventory"])

@router.post("", response_model=ResourceItem)
async def create_resource(item_in: ResourceItemCreate):
    if item_in.quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity must be >= 0")
    
    resource = ResourceItem(**item_in.model_dump() if hasattr(item_in, "model_dump") else item_in.dict())
    await resource.insert()
    return resource

@router.get("", response_model=List[ResourceItem])
async def list_resources(
    resource_type: Optional[ResourceType] = Query(None),
    status: Optional[ResourceStatus] = Query(None),
    skip: int = 0,
    limit: int = 50
):
    query = {}
    if resource_type:
        query["resource_type"] = resource_type
    if status:
        query["status"] = status
        
    resources = await ResourceItem.find(query).skip(skip).limit(limit).to_list()
    return resources

@router.get("/near", response_model=List[ResourceItem])
async def get_resources_near(
    lon: float = Query(..., description="Longitude"),
    lat: float = Query(..., description="Latitude"),
    radius_km: float = Query(..., description="Radius in kilometers")
):
    radius_meters = radius_km * 1000
    
    query = {
        "location": {
            "$nearSphere": {
                "$geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "$maxDistance": radius_meters
            }
        }
    }
    
    resources = await ResourceItem.find(query).to_list()
    return resources

@router.get("/{id}", response_model=ResourceItem)
async def get_resource(id: PydanticObjectId):
    resource = await ResourceItem.get(id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource

@router.put("/{id}", response_model=ResourceItem)
async def update_resource(id: PydanticObjectId, item_update: ResourceItemUpdate):
    resource = await ResourceItem.get(id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    update_data = item_update.model_dump(exclude_unset=True) if hasattr(item_update, "model_dump") else item_update.dict(exclude_unset=True)
    if not update_data:
        return resource
        
    if "quantity" in update_data and update_data["quantity"] < 0:
        raise HTTPException(status_code=400, detail="Quantity must be >= 0")
        
    for key, value in update_data.items():
        setattr(resource, key, value)
        
    resource.last_updated = datetime.utcnow()
    await resource.save()
    return resource

@router.delete("/{id}")
async def delete_resource(id: PydanticObjectId):
    resource = await ResourceItem.get(id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    await resource.delete()
    return {"status": "deleted"}
