from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class Component(BaseModel):
    id: str
    code: str
    symbol: str
    unit: str
    name: str

class Station(BaseModel):
    station_id: str
    station_code: str
    station_name: str
    city: str
    longitude: float
    latitude: float
    network_id: str
    network_code: str
    network_name: str
    station_setting: str
    station_type: str
    street: Optional[str] = None
    street_number: Optional[str] = None
    zip_code: Optional[str] = None
    active_from: Optional[str] = None
    active_to: Optional[str] = None

class Scope(BaseModel):
    id: str
    code: str
    time_base: str
    time_scope_seconds: int
    is_max: bool
    name: str

class MeasurementRecord(BaseModel):
    timestamp: str
    timestamp_end: str

    station_id: str
    station_code: str
    station_name: str
    city: str

    latitude: float
    longitude: float

    network_id: str
    network_code: str
    network_name: str
    station_setting: str
    station_type: str

    component_id: str
    component: str
    component_symbol: str
    component_name: str

    value: float
    unit: str

    scope_id: str
    scope_code: str
    scope: str

    uba_index: str

    source: str = "UBA"
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
