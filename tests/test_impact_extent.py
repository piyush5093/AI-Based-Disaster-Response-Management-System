import pytest
from app.services.impact_extent_service import (
    estimate_earthquake_extent,
    estimate_generic_extent,
    calculate_impact_extent
)

def test_earthquake_radius_6_0():
    # mag 6.0: 10 ** (0.5 * 6.0 - 1.8) = 10 ** 1.2 = 15.84 km
    epicenter = {"type": "Point", "coordinates": [0.0, 0.0]}
    polygon = estimate_earthquake_extent(6.0, epicenter)
    
    assert polygon["type"] == "Polygon"
    coords = polygon["coordinates"][0]
    # Check ring is closed
    assert coords[0] == coords[-1]
    
    # Radius check approximation by taking max distance in degrees (approx)
    max_lon = max(c[0] for c in coords)
    # 15.84 km / 111 km/deg ~ 0.142 degrees
    assert 0.13 < max_lon < 0.15

def test_earthquake_min_radius():
    # mag 2.0 would be 10 ** (0.5*2 - 1.8) = 10 ** -0.8 ~ 0.15 km
    # should be clamped to 5.0 km
    epicenter = {"type": "Point", "coordinates": [0.0, 0.0]}
    polygon = estimate_earthquake_extent(2.0, epicenter)
    
    coords = polygon["coordinates"][0]
    max_lon = max(c[0] for c in coords)
    # 5.0 km / 111 km/deg ~ 0.045 degrees
    assert 0.04 < max_lon < 0.05

def test_earthquake_max_radius():
    # mag 9.5 would be 10 ** (4.75 - 1.8) = 10 ** 2.95 ~ 891 km
    # should be clamped to 500.0 km
    epicenter = {"type": "Point", "coordinates": [0.0, 0.0]}
    polygon = estimate_earthquake_extent(9.5, epicenter)
    
    coords = polygon["coordinates"][0]
    max_lon = max(c[0] for c in coords)
    # 500.0 km / 111 km/deg ~ 4.5 degrees
    assert 4.4 < max_lon < 4.6

def test_generic_orange_flood():
    # Orange should be 50.0 km
    center = {"type": "Point", "coordinates": [0.0, 0.0]}
    polygon = estimate_generic_extent("Flood", "Orange", center)
    
    coords = polygon["coordinates"][0]
    max_lon = max(c[0] for c in coords)
    # 50.0 km / 111 km/deg ~ 0.45 degrees
    assert 0.44 < max_lon < 0.46

def test_calculate_impact_extent_earthquake_with_mag():
    event = {
        "event_type": "Earthquake",
        "location": {"type": "Point", "coordinates": [0.0, 0.0]},
        "raw_data": {"properties": {"mag": 6.0}}
    }
    polygon = calculate_impact_extent(event)
    coords = polygon["coordinates"][0]
    max_lon = max(c[0] for c in coords)
    # matches mag 6.0 logic (15.84 km)
    assert 0.13 < max_lon < 0.15

def test_calculate_impact_extent_earthquake_no_mag():
    event = {
        "event_type": "Earthquake",
        "alert_level": "Red",
        "location": {"type": "Point", "coordinates": [0.0, 0.0]},
        "raw_data": {} # No mag available
    }
    polygon = calculate_impact_extent(event)
    coords = polygon["coordinates"][0]
    max_lon = max(c[0] for c in coords)
    # Fallbacks to generic Red (100 km)
    assert 0.85 < max_lon < 0.95
