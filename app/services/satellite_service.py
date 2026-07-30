import logging
import asyncio
from app.config.settings import settings

logger = logging.getLogger(__name__)

async def fetch_damage_imagery(bbox: list, date_from: str, date_to: str) -> dict:
    if not settings.SENTINEL_HUB_CLIENT_ID or not settings.SENTINEL_HUB_CLIENT_SECRET:
        return {"error": "Sentinel Hub credentials not configured"}
        
    try:
        from sentinelhub import SentinelHubRequest, BBox, CRS, DataCollection, MimeType, SHConfig
        
        config = SHConfig()
        config.sh_client_id = settings.SENTINEL_HUB_CLIENT_ID
        config.sh_client_secret = settings.SENTINEL_HUB_CLIENT_SECRET
        
        # Bbox is [minLon, minLat, maxLon, maxLat]
        sh_bbox = BBox(bbox=bbox, crs=CRS.WGS84)
        
        # Create a true color request
        evalscript = """
        //VERSION=3
        function setup() {
            return {
                input: ["B02", "B03", "B04"],
                output: { bands: 3 }
            };
        }
        function evaluatePixel(sample) {
            return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
        }
        """
        
        request = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A,
                    time_interval=(date_from, date_to)
                )
            ],
            responses=[
                SentinelHubRequest.output_response("default", MimeType.PNG)
            ],
            bbox=sh_bbox,
            size=[512, 512],
            config=config
        )
        
        # Fetching data off the main thread since Sentinel Hub Python SDK is synchronous
        def fetch_data():
            return request.get_data()
            
        data = await asyncio.to_thread(fetch_data)
        
        if not data:
            return {"error": "No satellite imagery available for the given parameters."}
            
        return {
            "status": "success",
            "message": "Satellite imagery fetched successfully",
            "metadata": {
                "bbox": bbox,
                "date_from": date_from,
                "date_to": date_to,
                "image_count": len(data)
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching satellite imagery: {str(e)}")
        return {"error": f"Failed to fetch satellite imagery: {str(e)}"}
