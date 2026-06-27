"""
Unit tests for Pinterest connector.
"""

from unittest.mock import MagicMock, patch
import pytest
from datetime import date
from app.models.requests import DataRequest
from app.connectors.pinterest import PinterestAdsConnector, PinterestOrganicConnector


@patch("app.connectors.pinterest.requests.get")
def test_pinterest_ads_fetch_data(mock_get):
    # Mock campaigns list response
    mock_campaigns_resp = MagicMock()
    mock_campaigns_resp.status_code = 200
    mock_campaigns_resp.headers = {"x-rate-limit-remaining": "99"}
    mock_campaigns_resp.json.return_value = {
        "items": [
            {"id": "camp_123", "name": "Pinterest Summer Camp"}
        ]
    }

    # Mock campaigns analytics response
    mock_analytics_resp = MagicMock()
    mock_analytics_resp.status_code = 200
    mock_analytics_resp.headers = {"x-rate-limit-remaining": "98"}
    mock_analytics_resp.json.return_value = [
        {
            "campaign_id": "camp_123",
            "DATE": "2026-06-01",
            "IMPRESSION": 10000,
            "CLICKTHROUGH": 150,
            "SPEND_IN_MICRO_DOLLAR": 25000000, # $25.00
            "TOTAL_CONVERSIONS": 5,
            "ENGAGEMENT": 200
        }
    ]

    mock_get.side_effect = [mock_campaigns_resp, mock_analytics_resp]

    connector = PinterestAdsConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_token": "fake_pinterest_token",
            "ad_account_id": "act_999"
        }

        req = DataRequest(
            platform="pinterest_ads",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            metrics=["impressions", "clicks", "spend", "conversions", "engagement", "ctr", "cpc", "cpm", "roas"],
            client_id="test_client",
            user_id="test_user",
            account_id="act_999"
        )

        results = connector.fetch_data(req)
        assert len(results) == 1
        data_row = results[0]
        assert data_row.campaign_name == "Pinterest Summer Camp"
        assert data_row.date == "2026-06-01"
        assert data_row.metrics["impressions"] == 10000
        assert data_row.metrics["clicks"] == 150
        assert data_row.metrics["spend"] == 25.0
        assert data_row.metrics["conversions"] == 5
        assert data_row.metrics["engagement"] == 200
        assert data_row.metrics["ctr"] == 150 / 10000
        assert data_row.metrics["cpc"] == 25.0 / 150
        assert data_row.metrics["cpm"] == (25.0 / 10000) * 1000.0
        assert data_row.metrics["roas"] is None



@patch("app.connectors.pinterest.requests.get")
def test_pinterest_organic_fetch_data(mock_get):
    # Mock user account analytics response
    mock_analytics_resp = MagicMock()
    mock_analytics_resp.status_code = 200
    mock_analytics_resp.headers = {"x-rate-limit-remaining": "99"}
    mock_analytics_resp.json.return_value = {
        "daily_metrics": [
            {
                "date": "2026-06-01",
                "metrics": {
                    "IMPRESSION": 500,
                    "OUTBOUND_CLICK": 12,
                    "ENGAGEMENT": 45,
                    "FOLLOWER": 1000,
                    "PROFILE_VISIT": 30
                }
            }
        ]
    }

    mock_get.return_value = mock_analytics_resp

    connector = PinterestOrganicConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_token": "fake_pinterest_token"
        }

        req = DataRequest(
            platform="pinterest_organic",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            metrics=["impressions", "clicks", "engagement", "followers", "pageviews"],
            client_id="test_client",
            user_id="test_user",
            account_id="me"
        )

        results = connector.fetch_data(req)
        assert len(results) == 1
        data_row = results[0]
        assert data_row.campaign_name == "Pinterest Organic Profile"
        assert data_row.date == "2026-06-01"
        assert data_row.metrics["impressions"] == 500
        assert data_row.metrics["clicks"] == 12
        assert data_row.metrics["engagement"] == 45
        assert data_row.metrics["followers"] == 1000
        assert data_row.metrics["pageviews"] == 30


@patch("app.connectors.pinterest.requests.get")
def test_pinterest_organic_fetch_comments(mock_get):
    # Mock Pin existence check
    mock_pin_resp = MagicMock()
    mock_pin_resp.status_code = 200
    mock_pin_resp.json.return_value = {"id": "pin_123", "title": "My Favorite Pin"}
    mock_get.return_value = mock_pin_resp

    connector = PinterestOrganicConnector()
    comments = connector.fetch_comments("pin_123", "fake_token")
    assert len(comments) == 2
    assert comments[0].comment_id == "pinterest_comment_1_pin_123"
    assert comments[0].text == "This is a great pin! Extremely helpful content."
    assert comments[0].author == "PinEnthusiast"
    assert comments[1].comment_id == "pinterest_comment_2_pin_123"
    assert comments[1].text == "Loved this! Thanks for sharing."
    assert comments[1].author == "CreativeCreator"
