import math
from datetime import datetime
from typing import List, Dict, Any, Optional
from shapely.geometry import shape, Point, Polygon, box
from app.models.disaster_event import DisasterEvent
from app.models.resource_inventory import ResourceItem
from app.models.zone_grid import GridCell

# Approx conversion: 1 degree latitude is ~111 km.
# Longitude degrees shrink by cos(latitude).
KM_PER_DEGREE_LAT = 111.0

def generate_grid_for_bounds(min_lon: float, min_lat: float, max_lon: float, max_lat: float, cell_size_km: float = 10.0) -> List[Dict[str, Any]]:
    """
    Generates a list of rectangular grid cells covering the given bounding box.
    Each cell is approximately cell_size_km x cell_size_km.
    """
    cells = []
    lat_step = cell_size_km / KM_PER_DEGREE_LAT
    
    # We use the average latitude of the bounding box to approximate longitude distance
    avg_lat = (min_lat + max_lat) / 2.0
    lon_step = cell_size_km / (KM_PER_DEGREE_LAT * math.cos(math.radians(avg_lat)))
    
    current_lat = min_lat
    lat_index = 0
    while current_lat < max_lat:
        current_lon = min_lon
        lon_index = 0
        while current_lon < max_lon:
            cell_min_lon = current_lon
            cell_min_lat = current_lat
            cell_max_lon = current_lon + lon_step
            cell_max_lat = current_lat + lat_step
            
            center_lon = cell_min_lon + (lon_step / 2.0)
            center_lat = cell_min_lat + (lat_step / 2.0)
            
            # deterministic ID
            cell_id = f"grid_{lat_index}_{lon_index}"
            
            bounds = {
                "type": "Polygon",
                "coordinates": [[
                    [cell_min_lon, cell_min_lat],
                    [cell_max_lon, cell_min_lat],
                    [cell_max_lon, cell_max_lat],
                    [cell_min_lon, cell_max_lat],
                    [cell_min_lon, cell_min_lat]
                ]]
            }
            
            center = {
                "type": "Point",
                "coordinates": [center_lon, center_lat]
            }
            
            cells.append({
                "cell_id": cell_id,
                "bounds": bounds,
                "center": center,
                "shapely_box": box(cell_min_lon, cell_min_lat, cell_max_lon, cell_max_lat)
            })
            
            current_lon += lon_step
            lon_index += 1
        current_lat += lat_step
        lat_index += 1
        
    return cells

ALERT_LEVEL_WEIGHTS = {
    "Red": 1.0,
    "Orange": 0.7,
    "Yellow": 0.4,
    "Green": 0.2,
    "Unknown": 0.1
}

def get_alert_weight(alert_level: str) -> float:
    return ALERT_LEVEL_WEIGHTS.get(alert_level, 0.1)

async def classify_zones_for_events(event_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    query = {"impact_extent": {"$ne": None}}
    if event_ids:
        query["external_id"] = {"$in": event_ids}
        
    events = await DisasterEvent.find(query).to_list()
    if not events:
        return {
            "events_processed": 0,
            "grid_cells_created_or_updated": 0,
            "highest_severity_cell_id": None,
            "highest_severity_score": 0.0
        }

    # Determine overall bounding box
    min_lon, min_lat, max_lon, max_lat = float('inf'), float('inf'), float('-inf'), float('-inf')
    event_shapes = []
    
    for event in events:
        poly = shape(event.impact_extent)
        event_shapes.append((event, poly))
        b_min_lon, b_min_lat, b_max_lon, b_max_lat = poly.bounds
        min_lon = min(min_lon, b_min_lon)
        min_lat = min(min_lat, b_min_lat)
        max_lon = max(max_lon, b_max_lon)
        max_lat = max(max_lat, b_max_lat)
        
    # Pad the bounding box slightly
    min_lon -= 0.1
    min_lat -= 0.1
    max_lon += 0.1
    max_lat += 0.1
    
    grid_cells_data = generate_grid_for_bounds(min_lon, min_lat, max_lon, max_lat, cell_size_km=10.0)
    
    cells_upserted = 0
    highest_score = -1.0
    highest_cell = None
    
    for cell_data in grid_cells_data:
        cell_box = cell_data["shapely_box"]
        overlapping_events = []
        
        # Check intersections
        for event, poly in event_shapes:
            if cell_box.intersects(poly):
                overlapping_events.append(event)
                
        if not overlapping_events:
            continue
            
        overlapping_event_ids = [e.external_id for e in overlapping_events]
        
        # NOTE on double-counting: since events can overlap the same cell, do NOT 
        # just sum population/buildings naively if multiple events' polygons all 
        # cover the same cell — since a cell is a small fixed area, use the 
        # MAXIMUM population/building figure among overlapping events for that 
        # cell (not the sum), since that's a more defensible approximation than 
        # double/triple counting the same people/buildings.
        max_pop = max([e.estimated_population_exposed or 0 for e in overlapping_events])
        max_bldg = max([e.building_count or 0 for e in overlapping_events])
        
        # Determine max alert level
        best_alert = "Unknown"
        best_weight = -1.0
        for e in overlapping_events:
            w = get_alert_weight(e.alert_level)
            if w > best_weight:
                best_weight = w
                best_alert = e.alert_level
                
        # Count nearby resources (within 25km of cell center)
        lon, lat = cell_data["center"]["coordinates"]
        radius_radians = 25.0 / 6378.1
        nearby_resources = await ResourceItem.find({
            "location": {
                "$geoWithin": {
                    "$centerSphere": [[lon, lat], radius_radians]
                }
            }
        }).count()
        
        # Calculate severity score heuristic for prototype
        # Formula uses normalized factors maxing out at specific real-world values.
        population_exposed_normalized = min(1.0, max_pop / 50000.0)
        alert_level_weight = best_weight
        building_density_normalized = min(1.0, max_bldg / 5000.0)
        
        if nearby_resources == 0:
            resource_scarcity_factor = 1.0
        else:
            resource_scarcity_factor = max(0.1, 1.0 - (nearby_resources * 0.1))
            
        severity_score = min(100.0, (
            (population_exposed_normalized * 40.0) +
            (alert_level_weight * 30.0) +
            (building_density_normalized * 20.0) +
            (resource_scarcity_factor * 10.0)
        ))
        
        # Upsert GridCell
        existing_cell = await GridCell.find_one({"cell_id": cell_data["cell_id"]})
        if existing_cell:
            existing_cell.bounds = cell_data["bounds"]
            existing_cell.center = cell_data["center"]
            existing_cell.overlapping_event_ids = overlapping_event_ids
            existing_cell.total_population_exposed = max_pop
            existing_cell.total_building_count = max_bldg
            existing_cell.max_alert_level = best_alert
            existing_cell.resource_count_nearby = nearby_resources
            existing_cell.severity_score = severity_score
            existing_cell.last_calculated = datetime.utcnow()
            await existing_cell.save()
        else:
            new_cell = GridCell(
                cell_id=cell_data["cell_id"],
                bounds=cell_data["bounds"],
                center=cell_data["center"],
                overlapping_event_ids=overlapping_event_ids,
                total_population_exposed=max_pop,
                total_building_count=max_bldg,
                max_alert_level=best_alert,
                resource_count_nearby=nearby_resources,
                severity_score=severity_score
            )
            await new_cell.insert()
            
        cells_upserted += 1
        
        if severity_score > highest_score:
            highest_score = severity_score
            highest_cell = cell_data["cell_id"]
            
    return {
        "events_processed": len(events),
        "grid_cells_created_or_updated": cells_upserted,
        "highest_severity_cell_id": highest_cell,
        "highest_severity_score": highest_score
    }
