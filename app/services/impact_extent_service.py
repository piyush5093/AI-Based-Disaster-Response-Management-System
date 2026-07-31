import math
from typing import Dict, Any
from app.models.disaster_event import DisasterEvent

def create_circular_polygon(lon: float, lat: float, radius_km: float) -> Dict[str, Any]:
    points = 32
    coordinates = []
    
    # 1 degree lat ≈ 111 km, 1 degree lon ≈ 111 km * cos(lat)
    lat_deg_per_km = 1 / 111.0
    # Guard against division by zero at poles
    cos_lat = math.cos(math.radians(lat))
    if abs(cos_lat) < 1e-6:
        cos_lat = 1e-6
    lon_deg_per_km = 1 / (111.0 * cos_lat)
    
    for i in range(points):
        angle = (i * 360 / points)
        angle_rad = math.radians(angle)
        
        dx = radius_km * math.cos(angle_rad)
        dy = radius_km * math.sin(angle_rad)
        
        pt_lon = lon + (dx * lon_deg_per_km)
        pt_lat = lat + (dy * lat_deg_per_km)
        
        # Clamp coordinates to valid ranges
        pt_lon = max(-180.0, min(180.0, pt_lon))
        pt_lat = max(-90.0, min(90.0, pt_lat))
        
        coordinates.append([pt_lon, pt_lat])
        
    # Close the ring
    coordinates.append(coordinates[0])
    
    return {
        "type": "Polygon",
        "coordinates": [coordinates]
    }

def estimate_earthquake_extent(magnitude: float, epicenter: dict) -> dict:
    radius_km = 10 ** (0.5 * magnitude - 1.8)
    radius_km = max(5.0, min(500.0, radius_km))
    
    lon, lat = epicenter.get("coordinates", [0.0, 0.0])
    return create_circular_polygon(lon, lat, radius_km)

def estimate_generic_extent(event_type: str, alert_level: str, center: dict) -> dict:
    radii = {
        "Green": 10.0,
        "Yellow": 25.0,
        "Orange": 50.0,
        "Red": 100.0,
        "Unknown": 15.0
    }
    # Ensure Title Case mapping
    alert_level = alert_level.title() if alert_level else "Unknown"
    radius_km = radii.get(alert_level, 15.0)
    
    lon, lat = center.get("coordinates", [0.0, 0.0])
    return create_circular_polygon(lon, lat, radius_km)

def calculate_impact_extent(event: dict) -> dict:
    event_type = event.get("event_type", "Other")
    location = event.get("location") or {"type": "Point", "coordinates": [0.0, 0.0]}
    alert_level = event.get("alert_level", "Unknown")
    
    if event_type == "Earthquake":
        raw_data = event.get("raw_data", {})
        magnitude = None
        if "properties" in raw_data and "mag" in raw_data["properties"]:
            try:
                magnitude = float(raw_data["properties"]["mag"])
            except (ValueError, TypeError):
                pass
        
        if magnitude is not None:
            return estimate_earthquake_extent(magnitude, location)
            
    return estimate_generic_extent(event_type, alert_level, location)

async def run_impact_extent_pass() -> dict:
    summary = {
        "processed": 0,
        "updated": 0,
        "earthquake_based": 0,
        "generic_based": 0
    }
    
    all_events = await DisasterEvent.find_all().to_list()
    events_to_process = [e for e in all_events if getattr(e, "impact_extent", None) is None]
    
    for event in events_to_process:
        summary["processed"] += 1
        
        event_dict = event.model_dump()
        extent = calculate_impact_extent(event_dict)
        
        if extent:
            event.impact_extent = extent
            await event.save()
            summary["updated"] += 1
            
            is_eq = False
            if event.event_type == "Earthquake":
                raw_data = event.raw_data or {}
                if "properties" in raw_data and "mag" in raw_data["properties"]:
                    try:
                        float(raw_data["properties"]["mag"])
                        is_eq = True
                    except (ValueError, TypeError):
                        pass
            
            if is_eq:
                summary["earthquake_based"] += 1
            else:
                summary["generic_based"] += 1
                
    return summary
