import pytest
from unittest.mock import patch, MagicMock
import requests
from src.uba_client import get_json, UBAAPIError

@patch("src.uba_client.requests.get")
def test_get_json_success(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"key": "value"}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = get_json("http://example.com")
    assert result == {"key": "value"}
    mock_get.assert_called_once()

@patch("src.uba_client.requests.get")
def test_get_json_retry_failure(mock_get):
    mock_get.side_effect = requests.RequestException("Network error")

    with pytest.raises(UBAAPIError):
        # We expect this to fail after retrying
        get_json("http://example.com", timeout=1)
    
    # Check that it retried a few times (3 times as configured in tenacity)
    assert mock_get.call_count == 3
