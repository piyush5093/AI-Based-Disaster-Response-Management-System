import asyncio
import httpx
from typing import Dict, Any, Optional
from app.models.disaster_event import DisasterEvent

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_TIMEOUT = 25.0

def build_overpass_query(polygon: Dict[str, Any]) -> str:
    """
    Converts a GeoJSON Polygon's coordinates into an Overpass QL poly filter string.
    GeoJSON is [lon, lat], Overpass expects "lat lon lat lon".
    Builds a query that counts buildings and critical infrastructure.
    """
    if not polygon or "coordinates" not in polygon or not polygon["coordinates"]:
        return ""
    
    # Extract the exterior ring of the polygon
    ring = polygon["coordinates"][0]
    
    # Format: "lat1 lon1 lat2 lon2 ..."
    # Note: GeoJSON is (lon, lat), Overpass wants (lat, lon)
    poly_str = " ".join([f"{coord[1]} {coord[0]}" for coord in ring])
    
    query = f"""[out:json];
// Count all buildings
way["building"](poly:"{poly_str}");
out count;

// Count critical infrastructure (hospitals, schools, fire_station, police)
(
  node["amenity"~"hospital|school|fire_station|police"](poly:"{poly_str}");
  way["amenity"~"hospital|school|fire_station|police"](poly:"{poly_str}");
  relation["amenity"~"hospital|school|fire_station|police"](poly:"{poly_str}");
);
out count;
"""
    return query

async def get_building_footprint_data(polygon: Dict[str, Any]) -> Dict[str, Optional[int]]:
    """
    Sends the query to the Overpass API via httpx POST and parses the count response.
    Returns {"building_count": int, "critical_infrastructure_count": int}.
    Returns None values if the query fails or times out.
    """
    result = {
        "building_count": None,
        "critical_infrastructure_count": None
    }
    
    query = build_overpass_query(polygon)
    if not query:
        return result
        
    try:
        async with httpx.AsyncClient(timeout=OVERPASS_TIMEOUT) as client:
            # Overpass accepts POST requests with the query in the request body
            response = await client.post(
                OVERPASS_API_URL, 
                data={"data": query},
                headers={"User-Agent": "DisasterResponseApp/1.0"}
            )
            
            if response.status_code == 200:
                data = response.json()
                elements = data.get("elements", [])
                
                # We have 2 'out count;' statements in our query.
                if len(elements) >= 1:
                    b_tags = elements[0].get("tags", {})
                    result["building_count"] = int(b_tags.get("nodes", 0)) + int(b_tags.get("ways", 0)) + int(b_tags.get("relations", 0))
                
                if len(elements) >= 2:
                    c_tags = elements[1].get("tags", {})
                    result["critical_infrastructure_count"] = int(c_tags.get("nodes", 0)) + int(c_tags.get("ways", 0)) + int(c_tags.get("relations", 0))
            else:
                print(f"Overpass API failed with status {response.status_code}: {response.text}")
    except httpx.RequestError as e:
        print(f"Overpass API request failed: {e}")
    except Exception as e:
        print(f"Error processing Overpass API response: {e}")
        
    return result

async def run_building_footprint_pass(limit: int = 20) -> dict:
    """
    Queries the `limit` most recent DisasterEvent documents that have impact_extent set 
    AND building_count is None.
    Calls get_building_footprint_data() with a 1-second delay between requests.
    """
    summary = {
        "processed": 0,
        "updated": 0,
        "failed": 0,
        "sample_failures": []
    }
    
    # Find events with impact_extent but no building footprint calculated yet
    # Sort by created_at DESC to get the most recent events
    events = await DisasterEvent.find(
        {"impact_extent": {"$ne": None}, "building_count": None}
    ).sort("-created_at").limit(limit).to_list()
    
    for event in events:
        summary["processed"] += 1
        
        try:
            data = await get_building_footprint_data(event.impact_extent)
            
            if data["building_count"] is not None and data["critical_infrastructure_count"] is not None:
                event.building_count = data["building_count"]
                event.critical_infrastructure_count = data["critical_infrastructure_count"]
                await event.save()
                summary["updated"] += 1
            else:
                summary["failed"] += 1
                if len(summary["sample_failures"]) < 5:
                    summary["sample_failures"].append(f"Failed to fetch building data for event {event.id}")
        except Exception as e:
            summary["failed"] += 1
            if len(summary["sample_failures"]) < 5:
                summary["sample_failures"].append(f"Error on event {event.id}: {str(e)}")
                
        # Be nice to the Overpass API
        await asyncio.sleep(1.0)
        
    return summary
