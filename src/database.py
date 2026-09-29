import json
import psycopg2
import os
from psycopg2.extras import execute_values
from pathlib import Path
from typing import List
from src.models import MeasurementRecord

DB_HOST = os.getenv("UBA_DB_HOST", "localhost")
DB_PORT = os.getenv("UBA_DB_PORT", "5432")
DB_NAME = os.getenv("UBA_DB_NAME", "uba_air_quality")
DB_USER = os.getenv("UBA_DB_USER", "uba_user")
DB_PASS = os.getenv("UBA_DB_PASS", "uba_password")

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def save_to_timescaledb(records: List[MeasurementRecord]):
    """Save normalized and validated records to TimescaleDB idempotently."""
    if not records:
        return

    stations_data = {}
    for r in records:
        stations_data[r.station_id] = (
            r.station_id, r.station_code, r.station_name, r.city,
            r.latitude, r.longitude, r.network_id, r.network_code,
            r.network_name, r.station_setting, r.station_type
        )
    
    stations_query = """
    INSERT INTO stations (
        station_id, station_code, station_name, city, latitude, longitude,
        network_id, network_code, network_name, station_setting, station_type
    ) VALUES %s
    ON CONFLICT (station_id) DO UPDATE SET
        station_name = EXCLUDED.station_name,
        city = EXCLUDED.city,
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude;
    """
    
    measurements_data = [
        (
            r.timestamp, r.timestamp_end, r.station_id, r.component_id,
            r.component, r.component_symbol, r.component_name, r.value,
            r.unit, r.scope_id, r.scope_code, r.scope, r.uba_index,
            r.source, r.ingested_at
        ) for r in records
    ]
    
    measurements_query = """
    INSERT INTO measurements (
        timestamp, timestamp_end, station_id, component_id, component,
        component_symbol, component_name, value, unit, scope_id,
        scope_code, scope, uba_index, source, ingested_at
    ) VALUES %s
    ON CONFLICT (station_id, component_id, timestamp) DO NOTHING;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, stations_query, list(stations_data.values()))
            execute_values(cur, measurements_query, measurements_data)
        conn.commit()

def save_to_json(records: List[MeasurementRecord], output_path: str):
    """Save normalized and validated records to JSON."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    records_dict = [record.model_dump(mode='json') for record in records]
    with output.open("w", encoding="utf-8") as file:
        json.dump(records_dict, file, ensure_ascii=False, indent=2)
    print(f"Saved {len(records)} records → {output}")

