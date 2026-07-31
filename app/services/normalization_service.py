from datetime import datetime
from typing import Tuple, List, Dict, Any
from app.models.disaster_event import DisasterEvent
from dateutil import parser as date_parser

ALLOWED_EVENT_TYPES = {
    "Earthquake", "Flood", "Cyclone", "Wildfire", "Drought", 
    "VolcanicActivity", "Other"
}

ALLOWED_ALERT_LEVELS = {
    "Green", "Yellow", "Orange", "Red", "Unknown"
}

def map_event_type(raw_type: str) -> str:
    if not raw_type:
        return "Other"
        
    t = raw_type.strip().lower()
    
    # GDACS mappings
    if t == "wf" or "wildfire" in t or "forest fire" in t:
        return "Wildfire"
    if t == "eq" or "earthquake" in t:
        return "Earthquake"
    if t == "tc" or "cyclone" in t or "hurricane" in t or "typhoon" in t:
        return "Cyclone"
    if t == "fl" or "flood" in t:
        return "Flood"
    if t == "dr" or "drought" in t:
        return "Drought"
    if t == "vo" or "volcano" in t or "volcanic" in t:
        return "VolcanicActivity"
        
    # Check if it exactly matches one of the allowed types (case insensitive)
    for allowed in ALLOWED_EVENT_TYPES:
        if t == allowed.lower():
            return allowed
            
    return "Other"

def normalize_event(raw_event: dict) -> Tuple[Dict[str, Any], List[str]]:
    warnings = []
    cleaned = dict(raw_event)
    
    # 1. event_type
    original_type = cleaned.get("event_type", "")
    cleaned_type = map_event_type(original_type)
    cleaned["event_type"] = cleaned_type
    
    # 2. alert_level
    alert = str(cleaned.get("alert_level", "")).strip().title()
    if alert not in ALLOWED_ALERT_LEVELS:
        alert = "Unknown"
    cleaned["alert_level"] = alert
    
    # 3. title
    title = str(cleaned.get("title", "")).strip()
    if not title:
        title = f"{cleaned_type} event"
        warnings.append("empty title defaulted")
    cleaned["title"] = title
    
    # 4. description
    desc = str(cleaned.get("description", "")).strip()
    if len(desc) > 1000:
        desc = desc[:997] + "..."
    cleaned["description"] = desc
    
    # 5. location
    location = cleaned.get("location")
    if isinstance(location, dict) and location.get("type") == "Point":
        coords = location.get("coordinates")
        if isinstance(coords, list) and len(coords) >= 2:
            lon, lat = coords[0], coords[1]
            try:
                lon = float(lon)
                lat = float(lat)
                if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                    warnings.append(f"invalid coordinates: out of bounds ({lon}, {lat})")
            except (ValueError, TypeError):
                warnings.append("invalid coordinates: not numeric")
        else:
            warnings.append("invalid coordinates: missing or incomplete")
    else:
        warnings.append("invalid location format")
        
    # 6. event_date
    event_date = cleaned.get("event_date")
    if isinstance(event_date, str):
        try:
            cleaned["event_date"] = date_parser.parse(event_date)
        except Exception:
            warnings.append("invalid event_date string, defaulted to current time")
            cleaned["event_date"] = datetime.utcnow()
    elif not isinstance(event_date, datetime):
        warnings.append("invalid event_date type, defaulted to current time")
        cleaned["event_date"] = datetime.utcnow()
        
    return cleaned, warnings

async def run_normalization_pass() -> dict:
    summary = {
        "processed": 0,
        "updated": 0,
        "warnings_found": 0,
        "sample_warnings": []
    }
    
    # Query unnormalized events (filter in python since some old records lack the field completely)
    all_events = await DisasterEvent.find_all().to_list()
    unnormalized_events = [e for e in all_events if not getattr(e, "normalized", False)]
    
    for event in unnormalized_events:
        summary["processed"] += 1
        
        # Convert to dict for processing
        event_dict = event.model_dump()
        
        cleaned_dict, warnings = normalize_event(event_dict)
        
        if warnings:
            summary["warnings_found"] += len(warnings)
            if len(summary["sample_warnings"]) < 10:
                summary["sample_warnings"].extend(warnings[:10 - len(summary["sample_warnings"])])
                
        # Update event fields
        event.event_type = cleaned_dict["event_type"]
        event.alert_level = cleaned_dict["alert_level"]
        event.title = cleaned_dict["title"]
        event.description = cleaned_dict["description"]
        event.event_date = cleaned_dict["event_date"]
        
        event.normalized = True
        event.normalization_warnings = warnings
        
        await event.save()
        summary["updated"] += 1
        
    return summary
