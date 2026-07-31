from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import Field, validator, BaseModel
from beanie import Document
from pymongo import IndexModel, GEOSPHERE

class ResourceType(str, Enum):
    FOOD = "Food"
    WATER = "Water"
    MEDICAL_KIT = "MedicalKit"
    SHELTER = "Shelter"
    VEHICLE = "Vehicle"
    PERSONNEL = "Personnel"
    OTHER = "Other"

class ResourceStatus(str, Enum):
    AVAILABLE = "Available"
    RESERVED = "Reserved"
    DEPLOYED = "Deployed"
    DEPLETED = "Depleted"

class ResourceItem(Document):
    resource_type: ResourceType
    name: str
    quantity: int
    unit: str
    location: Dict[str, Any]  # GeoJSON Point: {"type": "Point", "coordinates": [lon, lat]}
    facility_name: str
    status: ResourceStatus = Field(default=ResourceStatus.AVAILABLE)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None

    class Settings:
        name = "resource_inventory"
        indexes = [
            IndexModel([("location", GEOSPHERE)])
        ]

class ResourceItemCreate(BaseModel):
    resource_type: ResourceType
    name: str
    quantity: int
    unit: str
    location: Dict[str, Any]
    facility_name: str
    status: ResourceStatus = ResourceStatus.AVAILABLE
    notes: Optional[str] = None

class ResourceItemUpdate(BaseModel):
    resource_type: Optional[ResourceType] = None
    name: Optional[str] = None
    quantity: Optional[int] = None
    unit: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    facility_name: Optional[str] = None
    status: Optional[ResourceStatus] = None
    notes: Optional[str] = None
