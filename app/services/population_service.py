"""
This module calculates population exposure using an approximation method suitable for a demo/prototype.
Because we don't have access to fine-grained gridded population data (due to API limitations), 
we use country-average population density multiplied by the estimated disaster impact area. 
This is not a precise population count.
"""

import math
from typing import Dict, Any, Optional
import reverse_geocoder as rg
from app.models.disaster_event import DisasterEvent

# Approximate population density (people per sq km) based on World Bank / UN data
# These are rough averages for the entire country.
POPULATION_DENSITY = {
    "IN": 473.0,      # India
    "US": 37.0,       # USA
    "CN": 149.0,      # China
    "AU": 3.3,        # Australia
    "ID": 148.0,      # Indonesia
    "PH": 376.0,      # Philippines
    "JP": 345.0,      # Japan
    "GLOBAL_AVG": 60.0 # Global average
}

def get_country_for_coordinates(lat: float, lon: float) -> str:
    """Returns the ISO-3166-1 alpha-2 country code for the given coordinates, or 'UNKNOWN'."""
    try:
        # reverse_geocoder expects (lat, lon)
        # mode=1 forces single-threaded mode to prevent multiprocessing deadlocks in async FastAPI
        results = rg.search((lat, lon), mode=1)
        if results and len(results) > 0:
            return results[0].get('cc', 'UNKNOWN')
        return 'UNKNOWN'
    except Exception:
        return 'UNKNOWN'

def calculate_polygon_area_km2(coordinates: list) -> float:
    """
    Calculates the approximate area in square kilometers of a GeoJSON polygon ring
    using the shoelace formula. Converts degrees to km using a local Cartesian projection
    around the centroid.
    """
    if not coordinates or len(coordinates) < 3:
        return 0.0

    # Calculate centroid
    sum_lon = sum(c[0] for c in coordinates)
    sum_lat = sum(c[1] for c in coordinates)
    centroid_lon = sum_lon / len(coordinates)
    centroid_lat = sum_lat / len(coordinates)

    # Convert coordinates to local Cartesian (x, y) in km relative to centroid
    cos_lat = math.cos(math.radians(centroid_lat))
    if abs(cos_lat) < 1e-6:
        cos_lat = 1e-6

    points_km = []
    for lon, lat in coordinates:
        x = (lon - centroid_lon) * 111.0 * cos_lat
        y = (lat - centroid_lat) * 111.0
        points_km.append((x, y))

    # Shoelace formula
    area = 0.0
    n = len(points_km)
    for i in range(n):
        j = (i + 1) % n
        area += points_km[i][0] * points_km[j][1]
        area -= points_km[j][0] * points_km[i][1]

    return abs(area) / 2.0

def get_population_for_polygon(polygon: Dict[str, Any]) -> Optional[int]:
    """
    Estimates population using a local lookup table of country densities and 
    multiplying by the polygon's approximate area.
    """
    try:
        # GeoJSON polygon coordinates is a list of rings. First ring is exterior.
        if "coordinates" not in polygon or not polygon["coordinates"]:
            return None
            
        ring = polygon["coordinates"][0]
        if not ring:
            return None
            
        # Get centroid to look up country
        sum_lon = sum(c[0] for c in ring)
        sum_lat = sum(c[1] for c in ring)
        centroid_lon = sum_lon / len(ring)
        centroid_lat = sum_lat / len(ring)
        
        country_code = get_country_for_coordinates(centroid_lat, centroid_lon)
        
        # Look up density, fallback to global average
        density = POPULATION_DENSITY.get(country_code, POPULATION_DENSITY["GLOBAL_AVG"])
        
        # Calculate area
        area_km2 = calculate_polygon_area_km2(ring)
        
        # Return estimate
        estimated_pop = area_km2 * density
        return int(round(estimated_pop))
    except Exception as e:
        print(f"Failed to calculate population for polygon: {str(e)}")
        return None

async def run_population_exposure_pass() -> dict:
    summary = {
        "processed": 0,
        "updated": 0,
        "failed": 0,
        "sample_failures": []
    }
    
    # Query all events where impact_extent is calculated but population isn't
    all_events = await DisasterEvent.find_all().to_list()
    events_to_process = [
        e for e in all_events 
        if getattr(e, "impact_extent", None) is not None 
        and getattr(e, "estimated_population_exposed", None) is None
    ]
    
    for event in events_to_process:
        summary["processed"] += 1
        
        pop = get_population_for_polygon(event.impact_extent)
        
        if pop is not None:
            event.estimated_population_exposed = pop
            await event.save()
            summary["updated"] += 1
        else:
            summary["failed"] += 1
            if len(summary["sample_failures"]) < 5:
                summary["sample_failures"].append(f"Failed to fetch population for event {event.id}")
                
    return summary
