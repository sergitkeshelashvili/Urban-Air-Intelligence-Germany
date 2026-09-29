import os
import psycopg2
from src.database import save_to_timescaledb, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
from src.models import MeasurementRecord
from datetime import datetime, timezone

def test_db_insertion():
    # Provide one fake MeasurementRecord
    record1 = MeasurementRecord(
        timestamp="2026-09-29 10:00:00",
        timestamp_end="2026-09-29 11:00:00",
        station_id="test_station_1",
        station_code="TEST01",
        station_name="Test Station 1",
        city="Test City",
        latitude=50.0,
        longitude=10.0,
        network_id="1",
        network_code="DE",
        network_name="Network",
        station_setting="urban",
        station_type="background",
        component_id="1",
        component="PM10",
        component_symbol="PM10",
        component_name="PM10",
        value=15.5,
        unit="µg/m³",
        scope_id="2",
        scope_code="1SMW",
        scope="One hour average",
        uba_index="0",
        source="UBA",
        ingested_at=datetime.now(timezone.utc)
    )

    # Insert it twice to test idempotency
    save_to_timescaledb([record1, record1])

    # Connect and verify
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    
    with conn.cursor() as cur:
        # Check hypertable
        cur.execute("SELECT hypertable_name FROM timescaledb_information.hypertables WHERE hypertable_name = 'measurements';")
        assert cur.fetchone()[0] == 'measurements', "Measurements is not a hypertable!"

        # Check records
        cur.execute("SELECT value, station_name FROM measurements m JOIN stations s ON m.station_id = s.station_id WHERE m.station_id = 'test_station_1';")
        rows = cur.fetchall()
        assert len(rows) == 1, "Idempotency failed or insert failed."
        assert rows[0][0] == 15.5
        assert rows[0][1] == "Test Station 1"
        
        print("Integration test passed successfully!")

    conn.close()

if __name__ == "__main__":
    test_db_insertion()
