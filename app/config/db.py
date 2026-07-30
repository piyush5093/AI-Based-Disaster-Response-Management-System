import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.config.settings import settings

from app.models.disaster_event import DisasterEvent

logger = logging.getLogger(__name__)

async def init_db():
    try:
        client = AsyncIOMotorClient(settings.MONGO_URI)
        # Initialize Beanie with the database and an empty list of document models for now
        await init_beanie(
            database=client[settings.DB_NAME],
            document_models=[DisasterEvent]
        )
        logger.info("MongoDB connected successfully")
        print("MongoDB connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        print(f"Failed to connect to MongoDB: {e}")
