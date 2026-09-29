from typing import Dict, List, Any
from datetime import datetime, timezone
from src.models import Component, Station, Scope

TARGET_COMPONENTS = {
    "1": "PM10",
    "2": "CO",
    "3": "O3",
    "4": "SO2",
    "5": "NO2",
    "9": "PM2.5",
}

TARGET_SCOPE_BY_COMPONENT = {
    "1": "6",
    "2": "4",
    "3": "4",
    "4": "2",
    "5": "2",
    "9": "6",
}

def parse_components(data: Dict[str, Any]) -> Dict[str, Component]:
    components = {}
    for component_id, values in data.items():
        if not component_id.isdigit():
            continue
        components[component_id] = Component(
            id=values[0],
            code=values[1],
            symbol=values[2],
            unit=values[3],
            name=values[4],
        )
    return components

def parse_stations(data: Dict[str, Any]) -> Dict[str, Station]:
    indices = data.get("indices", [])
    station_index = {name: i for i, name in enumerate(indices)}
    stations = {}

    for station_id, values in data.get("data", {}).items():
        if not station_id.isdigit():
            continue
        stations[station_id] = Station(
            station_id=values[station_index["station id"]],
            station_code=values[station_index["station code"]],
            station_name=values[station_index["station name"]],
            city=values[station_index["station city"]],
            longitude=float(values[station_index["station longitude"]]),
            latitude=float(values[station_index["station latitude"]]),
            network_id=values[station_index["network id"]],
            network_code=values[station_index["network code"]],
            network_name=values[station_index["network name"]],
            station_setting=values[station_index["station setting name"]],
            station_type=values[station_index["station type name"]],
            street=values[station_index["station street"]],
            street_number=values[station_index["station street nr"]],
            zip_code=values[station_index["station zip code"]],
            active_from=values[station_index["station active from"]],
            active_to=values[station_index["station active to"]],
        )
    return stations

def parse_scopes(data: Dict[str, Any]) -> Dict[str, Scope]:
    scopes = {}
    for scope_id, values in data.items():
        if not scope_id.isdigit():
            continue
        scopes[scope_id] = Scope(
            id=values[0],
            code=values[1],
            time_base=values[2],
            time_scope_seconds=int(values[3]),
            is_max=values[4] == "1",
            name=values[5],
        )
    return scopes

def normalize_measurements(
    raw_data: Dict[str, Any],
    stations: Dict[str, Station],
    components: Dict[str, Component],
    scopes: Dict[str, Scope],
) -> List[Dict[str, Any]]:
    records = []
    measurement_data = raw_data.get("data", {})
    now_utc = datetime.now(timezone.utc)

    for station_id_key, timestamps in measurement_data.items():
        station = stations.get(str(station_id_key))
        if not station:
            continue

        for timestamp, measurement in timestamps.items():
            if len(measurement) < 5:
                continue

            component_id = str(measurement[0])
            scope_id = str(measurement[1])
            value = measurement[2]
            timestamp_end = measurement[3]
            uba_index = str(measurement[4])

            if value is None:
                continue

            if component_id not in TARGET_COMPONENTS:
                continue

            if scope_id != TARGET_SCOPE_BY_COMPONENT.get(component_id):
                continue

            component = components.get(component_id)
            scope = scopes.get(scope_id)

            if not component or not scope:
                continue

            record = {
                "timestamp": timestamp,
                "timestamp_end": timestamp_end,
                "station_id": station.station_id,
                "station_code": station.station_code,
                "station_name": station.station_name,
                "city": station.city,
                "latitude": station.latitude,
                "longitude": station.longitude,
                "network_id": station.network_id,
                "network_code": station.network_code,
                "network_name": station.network_name,
                "station_setting": station.station_setting,
                "station_type": station.station_type,
                "component_id": component.id,
                "component": TARGET_COMPONENTS[component_id],
                "component_symbol": component.symbol,
                "component_name": component.name,
                "value": float(value),
                "unit": component.unit,
                "scope_id": scope.id,
                "scope_code": scope.code,
                "scope": scope.name,
                "uba_index": uba_index,
                "source": "UBA",
                "ingested_at": now_utc,
            }
            records.append(record)
    return records
