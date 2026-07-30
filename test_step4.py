import httpx
import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient

async def run_tests():
    print("1. Testing /api/health...")
    async with httpx.AsyncClient() as client:
        r = await client.get('http://localhost:8000/api/health')
        print(r.text)

    print("\n2. Checking existing documents count in MongoDB...")
    db_client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = db_client['disaster_response_db']
    total_count = await db['disaster_events'].count_documents({})
    print(f"Total documents in DB: {total_count}")

    print("\n3. Testing POST /api/disaster-events/sync-ndma...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post('http://localhost:8000/api/disaster-events/sync-ndma')
            print(f"Status Code: {r.status_code}")
            try:
                print(json.dumps(r.json(), indent=2))
            except json.JSONDecodeError:
                print(r.text)
        except Exception as e:
            print(f"Request failed: {e}")
            
    print("\n4. Testing POST /api/satellite/damage-imagery without credentials...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        payload = {
            "bbox": [72.77, 18.89, 73.0, 19.2], # Rough Mumbai bbox
            "date_from": "2026-07-20",
            "date_to": "2026-07-30"
        }
        r = await client.post('http://localhost:8000/api/satellite/damage-imagery', json=payload)
        print(f"Status Code: {r.status_code}")
        try:
            print(json.dumps(r.json(), indent=2))
        except json.JSONDecodeError:
            print(r.text)

    print("\n5. Testing GET /api/disaster-events for NDMA events...")
    async with httpx.AsyncClient() as client:
        r = await client.get('http://localhost:8000/api/disaster-events')
        data = r.json()
        ndma_events = [item for item in data if item.get('source') == 'NDMA']
        print(f"NDMA events in recent 50: {len(ndma_events)}")
        if len(ndma_events) > 0:
            print("Sample NDMA events:")
            print(json.dumps([{
                'source': e['source'],
                'event_type': e['event_type'],
                'title': e['title'],
                'description': e['description'],
                'location': e['location'],
                'event_date': e['event_date'],
                'external_id': e['external_id']
            } for e in ndma_events[:2]], indent=2))

asyncio.run(run_tests())
