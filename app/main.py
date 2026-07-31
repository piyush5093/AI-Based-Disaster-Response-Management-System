from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.db import init_db
from app.routers.health import router as health_router
from app.routers.disaster_events import router as disaster_events_router
from app.routers.resources import router as resources_router
from app.routers.zones import router as zones_router

app = FastAPI()

# Add CORSMiddleware allowing all origins for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await init_db()

# Include routers
app.include_router(health_router)
app.include_router(disaster_events_router)
app.include_router(resources_router)
app.include_router(zones_router)

