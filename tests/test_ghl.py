"""
Unit tests for GoHighLevel (GHL) connector.
"""

from unittest.mock import MagicMock, patch
import pytest
from datetime import date
from app.models.requests import DataRequest
from app.connectors.ghl import GhlConnector


@patch("app.connectors.ghl.requests.get")
def test_ghl_fetch_data(mock_get):
    # 1. Mock GHL Contacts response
    mock_contacts_resp = MagicMock()
    mock_contacts_resp.status_code = 200
    mock_contacts_resp.headers = {
        "x-ratelimit-remaining": "99"
    }
    mock_contacts_resp.json.return_value = {
        "contacts": [
            {
                "id": "c1",
                "locationId": "test-location",
                "dateAdded": "2026-06-01T10:00:00Z"
            },
            {
                "id": "c2",
                "locationId": "test-location",
                "dateAdded": "2026-06-01T15:30:00Z"
            }
        ],
        "meta": {
            "total": 2
        }
    }

    # 2. Mock GHL Opportunities response
    mock_opps_resp = MagicMock()
    mock_opps_resp.status_code = 200
    mock_opps_resp.json.return_value = {
        "opportunities": [
            {
                "id": "o1",
                "name": "Opportunity 1",
                "status": "won",
                "monetaryValue": 500.0,
                "createdAt": "2026-06-01T11:00:00Z"
            },
            {
                "id": "o2",
                "name": "Opportunity 2",
                "status": "lost",
                "monetaryValue": 250.0,
                "createdAt": "2026-06-01T12:00:00Z"
            },
            {
                "id": "o3",
                "name": "Opportunity 3",
                "status": "won",
                "monetaryValue": 1000.0,
                "createdAt": "2026-06-01T18:00:00Z"
            }
        ]
    }

    # Define side effect for requests.get
    def get_side_effect(url, *args, **kwargs):
        if "contacts" in url:
            return mock_contacts_resp
        elif "opportunities" in url:
            return mock_opps_resp
        return MagicMock(status_code=404)

    mock_get.side_effect = get_side_effect

    connector = GhlConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_token": "fake_ghl_token",
            "location_id": "test-location"
        }

        req = DataRequest(
            platform="ghl",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            metrics=["lead", "conversions", "purchase"],
            client_id="test_client",
            user_id="test_user",
            account_id="test-location"
        )

        results = connector.fetch_data(req)
        assert len(results) == 1
        data_row = results[0]
        assert data_row.campaign_name == "GoHighLevel Location Performance"
        assert data_row.date == "2026-06-01"
        # 2 contacts added
        assert data_row.metrics["lead"] == 2.0
        # 2 won opportunities (opp 1 and opp 3)
        assert data_row.metrics["conversions"] == 2.0
        # sum of won opportunity monetary values: 500.0 + 1000.0 = 1500.0
        assert data_row.metrics["purchase"] == 1500.0


@patch("app.connectors.ghl.requests.get")
def test_ghl_ping(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    connector = GhlConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_token": "fake_ghl_token",
            "location_id": "test-location"
        }
        assert connector.ping() is True

    # Test failure
    mock_resp.status_code = 401
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_token": "fake_ghl_token",
            "location_id": "test-location"
        }
        assert connector.ping() is False
