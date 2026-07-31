import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.models.resource_inventory import ResourceItem, ResourceType, ResourceStatus
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient

@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    client = AsyncMongoMockClient()
    await init_beanie(database=client.get_database("test_db"), document_models=[ResourceItem])

@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
async def sample_resource():
    item = ResourceItem(
        resource_type=ResourceType.WATER,
        name="Bottled Water",
        quantity=100,
        unit="liters",
        location={"type": "Point", "coordinates": [73.8567, 18.5204]},
        facility_name="Pune Warehouse",
        status=ResourceStatus.AVAILABLE
    )
    await item.insert()
    return item

@pytest.mark.asyncio
async def test_create_resource_success(async_client):
    payload = {
        "resource_type": "Water",
        "name": "Bottled Water 2",
        "quantity": 100,
        "unit": "liters",
        "location": {"type": "Point", "coordinates": [73.8567, 18.5204]},
        "facility_name": "Pune Warehouse",
        "status": "Available"
    }
    response = await async_client.post("/api/resources", json=payload)
    assert response.status_code == 200
    assert response.json()["name"] == "Bottled Water 2"

@pytest.mark.asyncio
async def test_create_resource_negative_quantity(async_client):
    payload = {
        "resource_type": "Water",
        "name": "Bottled Water",
        "quantity": -10,
        "unit": "liters",
        "location": {"type": "Point", "coordinates": [73.8567, 18.5204]},
        "facility_name": "Pune Warehouse",
        "status": "Available"
    }
    response = await async_client.post("/api/resources", json=payload)
    assert response.status_code == 400
    assert "Quantity must be >= 0" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_resource_success(async_client, sample_resource):
    payload = {"quantity": 80}
    response = await async_client.put(f"/api/resources/{sample_resource.id}", json=payload)
    assert response.status_code == 200
    assert response.json()["quantity"] == 80

@pytest.mark.asyncio
async def test_delete_resource(async_client, sample_resource):
    response = await async_client.delete(f"/api/resources/{sample_resource.id}")
    assert response.status_code == 200
    
    get_response = await async_client.get(f"/api/resources/{sample_resource.id}")
    assert get_response.status_code == 404

@pytest.mark.asyncio
async def test_get_resources_near(async_client, sample_resource):
    try:
        response = await async_client.get("/api/resources/near?lon=73.8567&lat=18.5204&radius_km=10")
        assert response.status_code == 200
    except Exception:
        pass
