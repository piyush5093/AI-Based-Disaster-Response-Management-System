import pytest
from unittest.mock import patch, MagicMock
from app.services.building_footprint_service import (
    build_overpass_query,
    get_building_footprint_data
)

def test_build_overpass_query():
    # GeoJSON polygon: [lon, lat]
    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [-0.1, 51.5],
            [-0.2, 51.5],
            [-0.2, 51.4],
            [-0.1, 51.4],
            [-0.1, 51.5]
        ]]
    }
    
    query = build_overpass_query(polygon)
    
    # Overpass expects "lat lon" format
    expected_poly = "51.5 -0.1 51.5 -0.2 51.4 -0.2 51.4 -0.1 51.5 -0.1"
    
    assert expected_poly in query
    assert "way[\"building\"]" in query
    assert "amenity\"~\"hospital|school|fire_station|police" in query
    assert "out count;" in query

@pytest.mark.asyncio
@patch("app.services.building_footprint_service.httpx.AsyncClient.post")
async def test_get_building_footprint_data_success(mock_post):
    # Mock a successful response with 2 'out count;' elements
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "elements": [
            # First count: buildings (nodes: 0, ways: 120, relations: 2)
            {"type": "count", "id": 0, "tags": {"nodes": "0", "ways": "120", "relations": "2"}},
            # Second count: critical infra (nodes: 5, ways: 1, relations: 0)
            {"type": "count", "id": 1, "tags": {"nodes": "5", "ways": "1", "relations": "0"}}
        ]
    }
    mock_post.return_value = mock_response
    
    polygon = {
        "type": "Polygon",
        "coordinates": [[[-0.1, 51.5], [-0.2, 51.5], [-0.1, 51.5]]]
    }
    
    result = await get_building_footprint_data(polygon)
    
    assert result["building_count"] == 122
    assert result["critical_infrastructure_count"] == 6

@pytest.mark.asyncio
@patch("app.services.building_footprint_service.httpx.AsyncClient.post")
async def test_get_building_footprint_data_timeout(mock_post):
    import httpx
    # Mock a timeout
    mock_post.side_effect = httpx.RequestError("Timeout")
    
    polygon = {
        "type": "Polygon",
        "coordinates": [[[-0.1, 51.5], [-0.2, 51.5], [-0.1, 51.5]]]
    }
    
    result = await get_building_footprint_data(polygon)
    
    # Should gracefully return None values on failure
    assert result["building_count"] is None
    assert result["critical_infrastructure_count"] is None
