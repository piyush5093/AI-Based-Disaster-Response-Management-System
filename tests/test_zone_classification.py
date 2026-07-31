import pytest
import pytest_asyncio
import math
from app.services.zone_classification_service import generate_grid_for_bounds, classify_zones_for_events, KM_PER_DEGREE_LAT
from app.models.disaster_event import DisasterEvent
from app.models.resource_inventory import ResourceItem, ResourceType
from app.models.zone_grid import GridCell
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient
from unittest.mock import patch, AsyncMock

@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    client = AsyncMongoMockClient()
    await init_beanie(database=client.get_database("test_db"), document_models=[DisasterEvent, ResourceItem, GridCell])

def test_generate_grid_for_bounds():
    min_lon, min_lat = 0.0, 0.0
    lat_step_10km = 10.0 / KM_PER_DEGREE_LAT
    lon_step_10km = 10.0 / KM_PER_DEGREE_LAT
    
    max_lon = min_lon + (lon_step_10km * 2.5) 
    max_lat = min_lat + (lat_step_10km * 2.5) 
    
    cells = generate_grid_for_bounds(min_lon, min_lat, max_lon, max_lat, cell_size_km=10.0)
    
    assert len(cells) == 9 # 3x3 grid
    assert cells[0]["cell_id"] == "grid_0_0"
    assert cells[-1]["cell_id"] == "grid_2_2"

@pytest.mark.asyncio
@patch("app.services.zone_classification_service.ResourceItem.find")
async def test_classify_zones_severity_high(mock_find):
    mock_chain = AsyncMock()
    mock_chain.count.return_value = 0
    mock_find.return_value = mock_chain
    
    event = DisasterEvent(
        source="test",
        event_type="Earthquake",
        title="Test EQ",
        description="Test",
        alert_level="Red",
        location={"type": "Point", "coordinates": [0.0, 0.0]},
        event_date="2023-01-01T00:00:00Z",
        external_id="test_high",
        raw_data={},
        impact_extent={
            "type": "Polygon",
            "coordinates": [[
                [-0.01, -0.01],
                [0.01, -0.01],
                [0.01, 0.01],
                [-0.01, 0.01],
                [-0.01, -0.01]
            ]]
        },
        estimated_population_exposed=60000,
        building_count=6000
    )
    await event.insert()
    
    res = await classify_zones_for_events()
    assert res["events_processed"] == 1
    
    cells = await GridCell.find_all().to_list()
    assert len(cells) > 0
    assert cells[0].severity_score >= 99.0
    assert cells[0].max_alert_level == "Red"

@pytest.mark.asyncio
@patch("app.services.zone_classification_service.ResourceItem.find")
async def test_classify_zones_severity_low(mock_find):
    mock_chain = AsyncMock()
    mock_chain.count.return_value = 10
    mock_find.return_value = mock_chain
    
    event = DisasterEvent(
        source="test",
        event_type="Flood",
        title="Test Flood",
        description="Test",
        alert_level="Green",
        location={"type": "Point", "coordinates": [10.0, 10.0]},
        event_date="2023-01-01T00:00:00Z",
        external_id="test_low",
        raw_data={},
        impact_extent={
            "type": "Polygon",
            "coordinates": [[
                [9.99, 9.99],
                [10.01, 9.99],
                [10.01, 10.01],
                [9.99, 10.01],
                [9.99, 9.99]
            ]]
        },
        estimated_population_exposed=1000,
        building_count=100
    )
    await event.insert()
    
    # We no longer need to insert real ResourceItems since we mock .count() to return 10
        
    res = await classify_zones_for_events()
    assert res["events_processed"] == 1
    
    cells = await GridCell.find_all().to_list()
    assert len(cells) > 0
    assert cells[0].severity_score < 10.0
    assert cells[0].max_alert_level == "Green"

@pytest.mark.asyncio
@patch("app.services.zone_classification_service.ResourceItem.find")
async def test_max_alert_level_logic(mock_find):
    mock_chain = AsyncMock()
    mock_chain.count.return_value = 0
    mock_find.return_value = mock_chain
    
    event1 = DisasterEvent(
        source="test",
        event_type="Flood",
        title="Orange Flood",
        description="Test",
        alert_level="Orange",
        location={"type": "Point", "coordinates": [5.0, 5.0]},
        event_date="2023-01-01T00:00:00Z",
        external_id="test_orange",
        raw_data={},
        impact_extent={
            "type": "Polygon",
            "coordinates": [[
                [4.9, 4.9],
                [5.1, 4.9],
                [5.1, 5.1],
                [4.9, 5.1],
                [4.9, 4.9]
            ]]
        }
    )
    await event1.insert()
    
    event2 = DisasterEvent(
        source="test",
        event_type="Earthquake",
        title="Red EQ",
        description="Test",
        alert_level="Red",
        location={"type": "Point", "coordinates": [5.0, 5.0]},
        event_date="2023-01-01T00:00:00Z",
        external_id="test_red",
        raw_data={},
        impact_extent={
            "type": "Polygon",
            "coordinates": [[
                [4.95, 4.95],
                [5.05, 4.95],
                [5.05, 5.05],
                [4.95, 5.05],
                [4.95, 4.95]
            ]]
        }
    )
    await event2.insert()
    
    res = await classify_zones_for_events()
    assert res["events_processed"] == 2
    
    cells = await GridCell.find_all().to_list()
    center_cells = [c for c in cells if "test_red" in c.overlapping_event_ids]
    assert len(center_cells) > 0
    
    cell_with_both = next(c for c in center_cells if "test_orange" in c.overlapping_event_ids)
    assert cell_with_both.max_alert_level == "Red"
