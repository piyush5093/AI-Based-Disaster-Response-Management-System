from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "disaster_response_db"
    PORT: int = 8000
    
    # Sentinel Hub API Credentials
    SENTINEL_HUB_CLIENT_ID: str = ""
    SENTINEL_HUB_CLIENT_SECRET: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
