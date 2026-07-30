import httpx
import logging
from datetime import datetime
from app.models.disaster_event import DisasterEvent

logger = logging.getLogger(__name__)

USGS_FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"

async def fetch_and_store_usgs_events() -> dict:
    summary = {"fetched": 0, "inserted": 0, "skipped": 0}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(USGS_FEED_URL, timeout=10.0)
            response.raise_for_status()
            
        data = response.json()
        features = data.get("features", [])
        summary["fetched"] = len(features)
        
        for feature in features:
            try:
                properties = feature.get("properties", {})
                geometry = feature.get("geometry", {})
                
                external_id = properties.get("url")
                if not external_id:
                    continue
                
                # Check for duplicates
                existing = await DisasterEvent.find_one({"external_id": external_id})
                if existing:
                    summary["skipped"] += 1
                    continue
                
                # Extract coordinates
                coordinates = geometry.get("coordinates", [])
                if len(coordinates) < 2:
                    summary["skipped"] += 1
                    continue
                    
                lon = coordinates[0]
                lat = coordinates[1]
                depth = coordinates[2] if len(coordinates) > 2 else "unknown"
                
                location_dict = {
                    "type": "Point",
                    "coordinates": [float(lon), float(lat)]
                }
                
                mag = properties.get("mag", "Unknown")
                place = properties.get("place", "Unknown Location")
                
                # Parse alert level
                raw_alert = properties.get("alert")
                alert_level = raw_alert.title() if raw_alert else "Unknown"
                
                # Parse event date (USGS time is in milliseconds since epoch)
                time_ms = properties.get("time")
                if time_ms:
                    event_date = datetime.utcfromtimestamp(time_ms / 1000.0)
                else:
                    event_date = datetime.utcnow()

                event = DisasterEvent(
                    source="USGS",
                    event_type="Earthquake",
                    title=f"M{mag} - {place}",
                    description=f"Magnitude {mag} earthquake occurred at {place} with a depth of {depth} km.",
                    alert_level=alert_level,
                    location=location_dict,
                    event_date=event_date,
                    external_id=external_id,
                    raw_data=feature
                )
                
                await event.insert()
                summary["inserted"] += 1
                
            except Exception as e:
                logger.error(f"Error processing USGS entry {external_id}: {e}")
                
        return summary
    
    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred while fetching USGS feed: {e}")
        raise
    except Exception as e:
        logger.error(f"An error occurred in fetch_and_store_usgs_events: {e}")
        raise
