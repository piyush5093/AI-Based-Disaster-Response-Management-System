import httpx
import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient

async def run_tests():
    print("1. Testing /api/health...")
    async with httpx.AsyncClient() as client:
        r = await client.get('http://localhost:8000/api/health')
        print(r.text)

    print("\n2. Testing GET /api/disaster-events for existing GDACS events...")
    async with httpx.AsyncClient() as client:
        r = await client.get('http://localhost:8000/api/disaster-events')
        data = r.json()
        print(f"Total returned: {len(data)}")
        if len(data) > 0:
            sources = set(item.get('source') for item in data)
            print(f"Sources found: {list(sources)}")
            print("Sample GDACS event:")
            for item in data:
                if item.get('source') == 'GDACS':
                    print(json.dumps({k: item[k] for k in ['title', 'source']}, indent=2))
                    break

    print("\n3. Testing POST /api/disaster-events/sync-usgs...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post('http://localhost:8000/api/disaster-events/sync-usgs')
        print(r.text)
        
    print("\n4. Testing GET /api/disaster-events for USGS events...")
    async with httpx.AsyncClient() as client:
        r = await client.get('http://localhost:8000/api/disaster-events')
        data = r.json()
        usgs_events = [item for item in data if item.get('source') == 'USGS']
        print(f"USGS events in recent 50: {len(usgs_events)}")
        if len(usgs_events) >= 2:
            print("Sample USGS events:")
            print(json.dumps([{
                'source': e['source'],
                'event_type': e['event_type'],
                'title': e['title'],
                'description': e['description'],
                'location': e['location'],
                'event_date': e['event_date'],
                'external_id': e['external_id']
            } for e in usgs_events[:2]], indent=2))
            
    print("\n5. Testing MongoDB aggregation (breakdown by source)...")
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['disaster_response_db']
    
    total_count = await db['disaster_events'].count_documents({})
    print(f"Total documents in DB: {total_count}")
    
    pipeline = [{"$group": {"_id": "$source", "count": {"$sum": 1}}}]
    cursor = db['disaster_events'].aggregate(pipeline)
    breakdown = await cursor.to_list(length=100)
    print("Breakdown by source:")
    print(json.dumps(breakdown, indent=2))

asyncio.run(run_tests())
