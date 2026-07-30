import httpx
import feedparser
import logging
from datetime import datetime
from time import mktime
from app.models.disaster_event import DisasterEvent

logger = logging.getLogger(__name__)

GDACS_FEED_URL = "https://www.gdacs.org/xml/rss.xml"

async def fetch_and_store_gdacs_events() -> dict:
    summary = {"fetched": 0, "inserted": 0, "skipped": 0}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(GDACS_FEED_URL, timeout=10.0)
            response.raise_for_status()
            
        feed = feedparser.parse(response.content)
        summary["fetched"] = len(feed.entries)
        
        for entry in feed.entries:
            try:
                external_id = entry.get("guid") or entry.get("link")
                if not external_id:
                    continue
                
                # Check for duplicates
                existing = await DisasterEvent.find_one({"external_id": external_id})
                if existing:
                    summary["skipped"] += 1
                    continue
                
                # Parse alert level
                alert_level = entry.get("gdacs_alertlevel", "Unknown")
                
                # Parse event type
                event_type = entry.get("gdacs_eventtype", "Unknown")
                
                # Parse coordinates (feedparser uses geo_lat and geo_long)
                geo_lat = entry.get("geo_lat")
                geo_long = entry.get("geo_long")
                location_dict = None
                if geo_lat and geo_long:
                    location_dict = {
                        "type": "Point",
                        "coordinates": [float(geo_long), float(geo_lat)] # GeoJSON requires [longitude, latitude]
                    }
                
                if not location_dict:
                    # Skip events without location since it's required for our geospatial queries
                    summary["skipped"] += 1
                    continue

                # Parse event date
                event_date = datetime.utcnow()
                if entry.get("published_parsed"):
                    event_date = datetime.fromtimestamp(mktime(entry.published_parsed))

                event = DisasterEvent(
                    source="GDACS",
                    event_type=event_type,
                    title=entry.get("title", "No Title"),
                    description=entry.get("description", ""),
                    alert_level=alert_level,
                    location=location_dict,
                    event_date=event_date,
                    external_id=external_id,
                    raw_data=dict(entry)
                )
                
                await event.insert()
                summary["inserted"] += 1
                
            except Exception as e:
                logger.error(f"Error processing GDACS entry {entry.get('title')}: {e}")
                
        return summary
    
    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred while fetching GDACS feed: {e}")
        raise
    except Exception as e:
        logger.error(f"An error occurred in fetch_and_store_gdacs_events: {e}")
        raise
