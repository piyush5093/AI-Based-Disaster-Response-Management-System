import httpx
import asyncio
import json

async def run_satellite_test():
    print("Testing POST /api/satellite/damage-imagery with real credentials...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "bbox": [72.77, 18.89, 73.0, 19.2], # Rough Mumbai bbox
            "date_from": "2026-07-20",
            "date_to": "2026-07-30"
        }
        try:
            r = await client.post('http://localhost:8000/api/satellite/damage-imagery', json=payload)
            print(f"Status Code: {r.status_code}")
            try:
                print(json.dumps(r.json(), indent=2))
            except json.JSONDecodeError:
                print(r.text)
        except Exception as e:
            print(f"Request failed: {e}")

asyncio.run(run_satellite_test())
