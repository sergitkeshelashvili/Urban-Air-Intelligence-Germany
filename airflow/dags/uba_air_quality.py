import json
import logging
import os
from datetime import timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

import sys
sys.path.insert(0, '/opt/airflow')

from src.uba_client import fetch_components, fetch_stations, fetch_scopes, fetch_measurements
from src.parser import parse_components, parse_stations, parse_scopes, normalize_measurements
from src.validation import validate_records
from src.database import save_to_timescaledb

DATA_DIR = Path('/tmp')
DATA_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("airflow.task")

def extract(**kwargs):
    execution_date = kwargs['data_interval_start']
    date_str = execution_date.strftime('%Y-%m-%d')
    logger.info(f"Extracting data for {date_str}")
    
    raw_components = fetch_components()
    raw_stations = fetch_stations()
    raw_scopes = fetch_scopes()
    
    raw_measurements = fetch_measurements(date_from=date_str, date_to=date_str)
    
    file_prefix = f"uba_{execution_date.strftime('%Y-%m-%dT%H')}"
    
    with open(DATA_DIR / f"{file_prefix}_components.json", "w") as f:
        json.dump(raw_components, f)
    with open(DATA_DIR / f"{file_prefix}_stations.json", "w") as f:
        json.dump(raw_stations, f)
    with open(DATA_DIR / f"{file_prefix}_scopes.json", "w") as f:
        json.dump(raw_scopes, f)
    with open(DATA_DIR / f"{file_prefix}_measurements.json", "w") as f:
        json.dump(raw_measurements, f)
        
    logger.info("Extraction complete. Raw files saved.")

def validate(**kwargs):
    execution_date = kwargs['data_interval_start']
    date_str = execution_date.strftime('%Y-%m-%d')
    file_prefix = f"uba_{execution_date.strftime('%Y-%m-%dT%H')}"
    
    logger.info(f"Validating raw data for {date_str}")
    
    with open(DATA_DIR / f"{file_prefix}_measurements.json", "r") as f:
        raw_measurements = json.load(f)
        
    if "data" not in raw_measurements:
        raise ValueError("Invalid raw data format: missing 'data' key")
    
    logger.info("Raw data validation passed.")

def transform(**kwargs):
    execution_date = kwargs['data_interval_start']
    date_str = execution_date.strftime('%Y-%m-%d')
    file_prefix = f"uba_{execution_date.strftime('%Y-%m-%dT%H')}"
    
    logger.info(f"Transforming data for {date_str}")
    
    with open(DATA_DIR / f"{file_prefix}_components.json", "r") as f:
        raw_components = json.load(f)
    with open(DATA_DIR / f"{file_prefix}_stations.json", "r") as f:
        raw_stations = json.load(f)
    with open(DATA_DIR / f"{file_prefix}_scopes.json", "r") as f:
        raw_scopes = json.load(f)
    with open(DATA_DIR / f"{file_prefix}_measurements.json", "r") as f:
        raw_measurements = json.load(f)
        
    components = parse_components(raw_components)
    stations = parse_stations(raw_stations)
    scopes = parse_scopes(raw_scopes)
    
    records = normalize_measurements(raw_measurements, stations, components, scopes)
    
    valid_records = validate_records(records)
    logger.info(f"Transformed and validated {len(valid_records)} records.")
    
    valid_dicts = [r.model_dump(mode='json') for r in valid_records]
    
    with open(DATA_DIR / f"{file_prefix}_transformed.json", "w") as f:
        json.dump(valid_dicts, f)

def load(**kwargs):
    execution_date = kwargs['data_interval_start']
    date_str = execution_date.strftime('%Y-%m-%d')
    file_prefix = f"uba_{execution_date.strftime('%Y-%m-%dT%H')}"
    
    logger.info(f"Loading data for {date_str}")
    
    with open(DATA_DIR / f"{file_prefix}_transformed.json", "r") as f:
        records_dicts = json.load(f)
        
    from src.models import MeasurementRecord
    records = [MeasurementRecord(**r) for r in records_dicts]
    
    save_to_timescaledb(records)
    logger.info(f"Loaded {len(records)} records to TimescaleDB.")
    
    for suffix in ['_components.json', '_stations.json', '_scopes.json', '_measurements.json', '_transformed.json']:
        file_path = DATA_DIR / f"{file_prefix}{suffix}"
        if file_path.exists():
            file_path.unlink()

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'uba_air_quality_ingestion',
    default_args=default_args,
    description='Extract UBA API data and load to TimescaleDB',
    schedule_interval='@hourly',
    start_date=days_ago(1),
    catchup=False,
    tags=['uba', 'air_quality'],
) as dag:

    extract_task = PythonOperator(
        task_id='extract',
        python_callable=extract,
    )

    validate_task = PythonOperator(
        task_id='validate',
        python_callable=validate,
    )

    transform_task = PythonOperator(
        task_id='transform',
        python_callable=transform,
    )

    load_task = PythonOperator(
        task_id='load',
        python_callable=load,
    )

    extract_task >> validate_task >> transform_task >> load_task
