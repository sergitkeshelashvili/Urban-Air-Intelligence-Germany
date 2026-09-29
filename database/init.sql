CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS stations (
    station_id VARCHAR(50) PRIMARY KEY,
    station_code VARCHAR(50),
    station_name VARCHAR(255),
    city VARCHAR(255),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    network_id VARCHAR(50),
    network_code VARCHAR(50),
    network_name VARCHAR(255),
    station_setting VARCHAR(100),
    station_type VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS measurements (
    timestamp TIMESTAMPTZ NOT NULL,
    timestamp_end TIMESTAMPTZ NOT NULL,
    station_id VARCHAR(50) REFERENCES stations(station_id),
    component_id VARCHAR(50) NOT NULL,
    component VARCHAR(50) NOT NULL,
    component_symbol VARCHAR(50),
    component_name VARCHAR(100),
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(50) NOT NULL,
    scope_id VARCHAR(50),
    scope_code VARCHAR(50),
    scope VARCHAR(100),
    uba_index VARCHAR(50),
    source VARCHAR(50),
    ingested_at TIMESTAMPTZ NOT NULL,
    UNIQUE (station_id, component_id, timestamp)
);

SELECT create_hypertable('measurements', by_range('timestamp'));

CREATE INDEX ix_measurements_station_time ON measurements (station_id, timestamp DESC);

CREATE INDEX ix_measurements_component_time ON measurements (component, timestamp DESC);
