import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


BASE_URL = "https://luftdaten.umweltbundesamt.de/api/air-data/v2"

COMPONENTS_URL = f"{BASE_URL}/components/json"
STATIONS_URL = f"{BASE_URL}/stations/json"
SCOPES_URL = f"{BASE_URL}/scopes/json"
MEASURES_URL = f"{BASE_URL}/measures/json"


TARGET_COMPONENTS = {
    "1": "PM10",
    "2": "CO",
    "3": "O3",
    "4": "SO2",
    "5": "NO2",
    "9": "PM2.5",
}

TARGET_SCOPE_ID = "2"


def get_json(url, params=None):
    """Make a GET request and return parsed JSON."""

    response = requests.get(
        url,
        params=params,
        headers={"accept": "application/json"},
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def load_components():
    """Load pollutant/component metadata from UBA."""

    data = get_json(COMPONENTS_URL)

    components = {}

    for component_id, values in data.items():

        if not component_id.isdigit():
            continue

        components[component_id] = {
            "id": values[0],
            "code": values[1],
            "symbol": values[2],
            "unit": values[3],
            "name": values[4],
        }

    return components


def load_stations():
    """Load station metadata from UBA."""

    data = get_json(STATIONS_URL)

    indices = data["indices"]

    station_index = {
        name: i
        for i, name in enumerate(indices)
    }

    stations = {}

    for station_id, values in data.get("data", {}).items():

        if not station_id.isdigit():
            continue

        stations[station_id] = {
            "station_id": values[station_index["station id"]],
            "station_code": values[station_index["station code"]],
            "station_name": values[station_index["station name"]],
            "city": values[station_index["station city"]],

            "longitude": float(
                values[station_index["station longitude"]]
            ),

            "latitude": float(
                values[station_index["station latitude"]]
            ),

            "network_id": values[
                station_index["network id"]
            ],

            "network_code": values[
                station_index["network code"]
            ],

            "network_name": values[
                station_index["network name"]
            ],

            "station_setting": values[
                station_index["station setting name"]
            ],

            "station_type": values[
                station_index["station type name"]
            ],

            "street": values[
                station_index["station street"]
            ],

            "street_number": values[
                station_index["station street nr"]
            ],

            "zip_code": values[
                station_index["station zip code"]
            ],

            "active_from": values[
                station_index["station active from"]
            ],

            "active_to": values[
                station_index["station active to"]
            ],
        }

    return stations


def load_scopes():
    """Load measurement scope metadata from UBA."""

    data = get_json(SCOPES_URL)

    scopes = {}

    for scope_id, values in data.items():

        if not scope_id.isdigit():
            continue

        scopes[scope_id] = {
            "id": values[0],
            "code": values[1],
            "time_base": values[2],
            "time_scope_seconds": int(values[3]),
            "is_max": values[4] == "1",
            "name": values[5],
        }

    return scopes


def fetch_measurements(date_from, date_to):
    """Fetch measurements for the requested date range."""

    params = {
        "use": "airquality",
        "lang": "en",
        "date_from": date_from,
        "date_to": date_to,
        "time_from": "00",
        "time_to": "23",
    }

    return get_json(
        MEASURES_URL,
        params=params,
    )


def normalize_measurements(
    raw_data,
    stations,
    components,
    scopes,
):
    """
    Convert UBA's nested response into normalized records.
    """

    records = []

    measurement_data = raw_data.get("data", {})

    for station_id, timestamps in measurement_data.items():

        station = stations.get(str(station_id))

        if not station:
            continue

        for timestamp, measurement in timestamps.items():

            if len(measurement) < 5:
                continue

            component_id = str(measurement[0])
            scope_id = str(measurement[1])

            value = measurement[2]
            timestamp_end = measurement[3]
            uba_index = measurement[4]

            if component_id not in TARGET_COMPONENTS:
                continue

            if scope_id != TARGET_SCOPE_ID:
                continue

            component = components.get(component_id)
            scope = scopes.get(scope_id)

            if not component or not scope:
                continue

            record = {
                "timestamp": timestamp,
                "timestamp_end": timestamp_end,

                "station_id": station["station_id"],
                "station_code": station["station_code"],
                "station_name": station["station_name"],
                "city": station["city"],

                "latitude": station["latitude"],
                "longitude": station["longitude"],

                "network_id": station["network_id"],
                "network_code": station["network_code"],
                "network_name": station["network_name"],
                "station_setting": station["station_setting"],
                "station_type": station["station_type"],

                "component_id": component["id"],
                "component": component["code"],
                "component_symbol": component["symbol"],
                "component_name": component["name"],

                "value": value,
                "unit": component["unit"],

                "scope_id": scope["id"],
                "scope_code": scope["code"],
                "scope": scope["name"],

                "uba_index": uba_index,

                "source": "UBA",
                "ingested_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            records.append(record)

    return records


def save_json(records, output_path):
    """Save normalized records to JSON."""

    output = Path(output_path)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"Saved {len(records)} records → {output}"
    )


def print_summary(records):
    """Print a small summary of collected data."""

    if not records:
        print("\nNo records found.")
        return

    stations = {
        record["station_id"]
        for record in records
    }

    components = {
        record["component"]
        for record in records
    }

    cities = {
        record["city"]
        for record in records
    }

    print("\nCollection summary")
    print("------------------")
    print(f"Records:    {len(records)}")
    print(f"Stations:   {len(stations)}")
    print(f"Cities:     {len(cities)}")
    print(f"Pollutants: {', '.join(sorted(components))}")

    timestamps = [
        record["timestamp"]
        for record in records
    ]

    print(f"First measurement: {min(timestamps)}")
    print(f"Last measurement:  {max(timestamps)}")


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Collect German air-quality measurements "
            "from the UBA Air Data API."
        )
    )

    parser.add_argument(
        "--date",
        help="Date in YYYY-MM-DD format.",
    )

    parser.add_argument(
        "--output",
        default="data/measurements.json",
        help="Output JSON file.",
    )

    args = parser.parse_args()

    if args.date:

        date_from = args.date
        date_to = args.date

    else:

        yesterday = (
            datetime.now().date()
            - timedelta(days=1)
        )

        date_from = yesterday.isoformat()
        date_to = yesterday.isoformat()

    print(
        f"Collecting UBA data for "
        f"{date_from}"
    )


    print("\nLoading metadata...")

    components = load_components()
    stations = load_stations()
    scopes = load_scopes()

    print(
        f"  Components: {len(components)}"
    )

    print(
        f"  Stations:   {len(stations)}"
    )

    print(
        f"  Scopes:     {len(scopes)}"
    )


    print("\nFetching measurements...")

    raw_data = fetch_measurements(
        date_from=date_from,
        date_to=date_to,
    )

    records = normalize_measurements(
        raw_data=raw_data,
        stations=stations,
        components=components,
        scopes=scopes,
    )

    print(
        f"Normalized records: {len(records)}"
    )


    save_json(
        records=records,
        output_path=args.output,
    )

    print_summary(records)


if __name__ == "__main__":
    main()