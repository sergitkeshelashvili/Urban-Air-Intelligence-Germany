import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

BASE_URL = "https://luftdaten.umweltbundesamt.de/api/air-data/v2"

COMPONENTS_URL = f"{BASE_URL}/components/json"
STATIONS_URL = f"{BASE_URL}/stations/json"
SCOPES_URL = f"{BASE_URL}/scopes/json"
MEASURES_URL = f"{BASE_URL}/measures/json"

class UBAAPIError(Exception):
    """Custom exception for UBA API errors."""
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.RequestException, UBAAPIError)),
    reraise=True
)
def get_json(url: str, params: dict = None, timeout: int = 30) -> dict:
    """Make a GET request and return parsed JSON with retries."""
    try:
        response = requests.get(
            url,
            params=params,
            headers={"accept": "application/json"},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise UBAAPIError(f"API request failed: {e}") from e

def fetch_components() -> dict:
    return get_json(COMPONENTS_URL)

def fetch_stations() -> dict:
    return get_json(STATIONS_URL)

def fetch_scopes() -> dict:
    return get_json(SCOPES_URL)

def fetch_measurements(date_from: str, date_to: str) -> dict:
    params = {
        "use": "airquality",
        "lang": "en",
        "date_from": date_from,
        "date_to": date_to,
        "time_from": "00",
        "time_to": "23",
    }
    return get_json(MEASURES_URL, params=params)
