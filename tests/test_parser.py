import pytest
from src.parser import parse_components, parse_stations, parse_scopes, normalize_measurements
from src.models import Component, Station, Scope
from src.validation import validate_records

def test_parse_components():
    raw_data = {
        "1": ["1", "PM10", "PM10", "µg/m³", "Particulate matter PM10"],
        "non_digit": ["ignore"]
    }
    components = parse_components(raw_data)
    assert len(components) == 1
    assert "1" in components
    comp = components["1"]
    assert comp.id == "1"
    assert comp.code == "PM10"

def test_parse_stations():
    raw_data = {
        "indices": ["station id", "station code", "station name", "station city", "station longitude", "station latitude", "network id", "network code", "network name", "station setting name", "station type name", "station street", "station street nr", "station zip code", "station active from", "station active to"],
        "data": {
            "123": ["123", "DE0001", "Test Station", "Test City", "10.0", "50.0", "1", "DE", "Network", "urban", "background", "Street", "1", "12345", "2000-01-01", ""]
        }
    }
    stations = parse_stations(raw_data)
    assert len(stations) == 1
    assert "123" in stations
    station = stations["123"]
    assert station.station_code == "DE0001"
    assert station.city == "Test City"
    assert station.latitude == 50.0

def test_parse_scopes():
    raw_data = {
        "2": ["2", "1SMW", "hour", "3600", "0", "One hour average"]
    }
    scopes = parse_scopes(raw_data)
    assert len(scopes) == 1
    assert scopes["2"].name == "One hour average"
    assert scopes["2"].time_scope_seconds == 3600

def test_normalize_and_validate_measurements():
    stations = {
        "123": Station(
            station_id="123", station_code="DE0001", station_name="Test Station",
            city="Test City", longitude=10.0, latitude=50.0, network_id="1",
            network_code="DE", network_name="Network", station_setting="urban",
            station_type="background"
        )
    }
    components = {
        "1": Component(id="1", code="PM10", symbol="PM10", unit="µg/m³", name="PM10")
    }
    scopes = {
        "6": Scope(id="6", code="1TMWGL", time_base="hour", time_scope_seconds=3600, is_max=False, name="Rolling daily average")
    }
    
    raw_data = {
        "data": {
            "123": {
                "2023-01-01 12:00:00": [1, 6, 15.5, "2023-01-01 13:00:00", 0]
            }
        }
    }
    
    records = normalize_measurements(raw_data, stations, components, scopes)
    assert len(records) == 1
    assert records[0]["value"] == 15.5
    assert records[0]["station_name"] == "Test Station"
    
    validated = validate_records(records)
    assert len(validated) == 1
    assert validated[0].value == 15.5
    assert validated[0].unit == "µg/m³"
