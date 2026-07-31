import httpx
import logging
import asyncio
import xmltodict
from datetime import datetime
from app.models.disaster_event import DisasterEvent
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

NDMA_RSS_URL = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"

def get_centroid(area_info) -> list:
    """
    Tries to extract a centroid [lon, lat] from a CAP cap:area block.
    Returns None if no valid geometry is found.
    """
    if not area_info:
        return None
        
    # area_info could be a list if there are multiple areas
    if isinstance(area_info, list):
        area_info = area_info[0]
        
    polygon = area_info.get("cap:polygon")
    circle = area_info.get("cap:circle")
    
    # Try polygon first
    if polygon:
        # cap:polygon is typically "lat,lon lat,lon lat,lon..."
        try:
            points = polygon.split()
            lats = []
            lons = []
            for point in points:
                lat_str, lon_str = point.split(",")
                lats.append(float(lat_str))
                lons.append(float(lon_str))
            if lats and lons:
                return [sum(lons)/len(lons), sum(lats)/len(lats)]
        except Exception as e:
            logger.warning(f"Failed to parse polygon {polygon}: {e}")
            
    # Try circle next
    if circle:
        # cap:circle is typically "lat,lon radius"
        try:
            center, _ = circle.split(" ", 1)
            lat_str, lon_str = center.split(",")
            return [float(lon_str), float(lat_str)]
        except Exception as e:
            logger.warning(f"Failed to parse circle {circle}: {e}")
            
    return None

def map_severity_to_alert_level(severity: str) -> str:
    """
    Maps CAP severity to standard Green/Yellow/Orange/Red.
    CAP severities: Extreme, Severe, Moderate, Minor, Unknown
    """
    mapping = {
        "Extreme": "Red",
        "Severe": "Orange",
        "Moderate": "Yellow",
        "Minor": "Green",
        "Unknown": "Unknown"
    }
    return mapping.get(severity, "Unknown")

async def fetch_and_store_ndma_events() -> dict:
    summary = {
        "fetched": 0, 
        "inserted": 0, 
        "skipped": 0, 
        "skipped_no_location": 0, 
        "errors": []
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # 1. Fetch the main RSS feed
            response = await client.get(NDMA_RSS_URL, timeout=15.0, follow_redirects=True)
            response.raise_for_status()
            
            rss_parsed = xmltodict.parse(response.text)
            
            channel = rss_parsed.get("rss", {}).get("channel", {})
            items = channel.get("item", [])
            
            if isinstance(items, dict):
                items = [items]
                
            summary["fetched"] = len(items)
            
            # 2. Iterate through RSS items and fetch individual CAP XML files
            for item in items:
                cap_url = item.get("link")
                if not cap_url:
                    continue
                    
                try:
                    await asyncio.sleep(0.5)
                    cap_response = await client.get(cap_url, timeout=15.0, follow_redirects=True)
                    if cap_response.status_code != 200:
                        summary["errors"].append(f"Failed to fetch {cap_url}: {cap_response.status_code}")
                        continue
                        
                    cap_parsed = xmltodict.parse(cap_response.text)
                    alert = cap_parsed.get("cap:alert", {})
                    
                    external_id = alert.get("cap:identifier")
                    if not external_id:
                        continue
                        
                    # Check for duplicates
                    existing = await DisasterEvent.find_one({"external_id": external_id})
                    if existing:
                        summary["skipped"] += 1
                        continue
                        
                    info = alert.get("cap:info", {})
                    # If multiple info blocks exist, just take the first one
                    if isinstance(info, list):
                        info = info[0]
                        
                    area = info.get("cap:area", {})
                    
                    # Extract location
                    centroid = get_centroid(area)
                    if not centroid:
                        summary["skipped_no_location"] += 1
                        continue
                        
                    location_dict = {
                        "type": "Point",
                        "coordinates": centroid
                    }
                    
                    # Parse dates
                    effective_str = info.get("cap:effective") or alert.get("cap:sent")
                    try:
                        event_date = date_parser.parse(effective_str) if effective_str else datetime.utcnow()
                    except Exception:
                        event_date = datetime.utcnow()
                        
                    severity = info.get("cap:severity", "Unknown")
                    alert_level = map_severity_to_alert_level(severity)
                    
                    event_type = info.get("cap:event") or info.get("cap:category", "Unknown")
                    title = info.get("cap:headline", "NDMA Alert")
                    description = info.get("cap:description", "")
                    
                    disaster_event = DisasterEvent(
                        source="NDMA",
                        event_type=event_type,
                        title=title,
                        description=description,
                        alert_level=alert_level,
                        location=location_dict,
                        event_date=event_date,
                        external_id=external_id,
                        raw_data=cap_parsed
                    )
                    
                    await disaster_event.insert()
                    summary["inserted"] += 1
                    
                except Exception as item_err:
                    summary["errors"].append(f"Error processing {cap_url}: {str(item_err)}")
                    
        return summary
        
    except Exception as e:
        logger.error(f"Failed to process NDMA feed: {e}")
        summary["errors"].append(f"Failed to fetch or parse main NDMA feed: {str(e)}")
        return summary
