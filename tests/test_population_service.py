import pytest
from app.services.population_service import (
    calculate_polygon_area_km2,
    get_country_for_coordinates,
    get_population_for_polygon,
    POPULATION_DENSITY
)

def test_calculate_polygon_area_km2():
    # A simple 1-degree by 1-degree square at the equator
    # 1 degree lat = 111km, 1 degree lon at equator = 111km
    # Area should be roughly 111 * 111 = 12321 km2
    coords = [
        [0.0, 0.0],
        [1.0, 0.0],
        [1.0, 1.0],
        [0.0, 1.0],
        [0.0, 0.0]
    ]
    area = calculate_polygon_area_km2(coords)
    assert 12000 < area < 13000

def test_get_country_for_coordinates():
    # India (New Delhi area roughly)
    assert get_country_for_coordinates(28.6, 77.2) == "IN"
    
    # Ocean (Null Island) should fallback to UNKNOWN or similar
    # rg.search might find nearest landmass but if it's very far it might do something else.
    # Actually, rg.search always returns *something* if it's on earth, but we'll see.
    # Let's test a known ocean point far from land (South Pacific)
    # Actually, reverse_geocoder always snaps to the nearest city, even if it's 1000km away.
    # That's fine for our fallback since we just use GLOBAL_AVG if it's not in our POPULATION_DENSITY dict.
    pass

def test_get_population_for_polygon_india():
    # Polygon in India (1 degree square near equator would be 12321 km2, let's use a 0.1 degree square ~ 123 km2)
    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [77.0, 20.0],
            [77.1, 20.0],
            [77.1, 20.1],
            [77.0, 20.1],
            [77.0, 20.0]
        ]]
    }
    pop = get_population_for_polygon(polygon)
    assert pop is not None
    # Area: ~ (0.1 * 111 * cos(20)) * (0.1 * 111) = ~10.4 * 11.1 = 115 km2
    # Density for IN = 473
    # Pop ~ 115 * 473 = 54400
    assert 45000 < pop < 65000

def test_get_population_for_polygon_unrecognized():
    # Some point that snaps to a country NOT in our dict, e.g., somewhere in Africa
    # like Chad (15.0, 19.0). It will use GLOBAL_AVG = 60.0
    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [19.0, 15.0],
            [19.1, 15.0],
            [19.1, 15.1],
            [19.0, 15.1],
            [19.0, 15.0]
        ]]
    }
    pop = get_population_for_polygon(polygon)
    assert pop is not None
    # Area: ~ (0.1 * 111 * cos(15)) * (0.1 * 111) = ~10.7 * 11.1 = 119 km2
    # Density = 60
    # Pop ~ 119 * 60 = 7140
    assert 6000 < pop < 8000
