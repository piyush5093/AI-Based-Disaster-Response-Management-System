import pytest
from datetime import datetime
from app.services.normalization_service import normalize_event

def test_normalize_gdacs_wf():
    raw = {
        "event_type": "WF",
        "alert_level": "Red",
        "title": "A big fire",
        "description": "Details here.",
        "location": {"type": "Point", "coordinates": [10.0, 20.0]},
        "event_date": datetime.utcnow()
    }
    cleaned, warnings = normalize_event(raw)
    assert cleaned["event_type"] == "Wildfire"
    assert len(warnings) == 0

def test_normalize_usgs_alert():
    raw = {
        "event_type": "earthquake",
        "alert_level": "green",
        "title": "M4.5 quake",
        "description": "Earthquake details",
        "location": {"type": "Point", "coordinates": [100.0, -10.0]},
        "event_date": datetime.utcnow()
    }
    cleaned, warnings = normalize_event(raw)
    assert cleaned["alert_level"] == "Green"
    assert cleaned["event_type"] == "Earthquake"
    assert len(warnings) == 0

def test_invalid_coordinates():
    raw = {
        "event_type": "Flood",
        "alert_level": "Orange",
        "title": "Flood warning",
        "description": "Flood details",
        "location": {"type": "Point", "coordinates": [200.0, 90.0]},  # longitude out of bounds
        "event_date": datetime.utcnow()
    }
    cleaned, warnings = normalize_event(raw)
    assert any("invalid coordinates" in w for w in warnings)

def test_empty_title_fallback():
    raw = {
        "event_type": "tc",
        "alert_level": "yellow",
        "title": "   ",
        "description": "Cyclone approaching",
        "location": {"type": "Point", "coordinates": [150.0, 20.0]},
        "event_date": datetime.utcnow()
    }
    cleaned, warnings = normalize_event(raw)
    assert cleaned["event_type"] == "Cyclone"
    assert cleaned["title"] == "Cyclone event"
    assert any("empty title defaulted" in w for w in warnings)

def test_string_event_date_converted():
    raw = {
        "event_type": "Drought",
        "alert_level": "Unknown",
        "title": "Dry season",
        "description": "Long dry season",
        "location": {"type": "Point", "coordinates": [10.0, 10.0]},
        "event_date": "2026-07-31T00:00:00Z"
    }
    cleaned, warnings = normalize_event(raw)
    assert isinstance(cleaned["event_date"], datetime)
    assert len(warnings) == 0
