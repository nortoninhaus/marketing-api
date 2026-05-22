"""
Unit tests for Meta connectors with updated FacebookSession initialization.
"""

from unittest.mock import MagicMock, patch
import pytest
from datetime import date
from app.models.requests import DataRequest
from app.connectors.meta import MetaAdsConnector, MetaOrganicConnector

@patch("app.connectors.meta.FacebookSession")
@patch("app.connectors.meta.FacebookAdsApi")
@patch("app.connectors.meta.AdAccount")
def test_meta_ads_fetch_data(mock_ad_account, mock_api, mock_session):
    mock_instance = MagicMock()
    mock_ad_account.return_value = mock_instance
    mock_instance.get_insights.return_value = [
        {"campaign_name": "Test Ads Campaign", "date_start": "2026-05-01", "impressions": "500", "clicks": "50"}
    ]
    
    connector = MetaAdsConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_token": "fake_ads_token",
            "ad_account_id": "act_12345"
        }
        
        req = DataRequest(
            platform="meta_ads",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 7),
            metrics=["impressions", "clicks"],
            client_id="test_client",
            user_id="test_user",
            account_id="act_12345"
        )
        
        results = connector.fetch_data(req)
        assert len(results) == 1
        assert results[0].campaign_name == "Test Ads Campaign"
        assert results[0].metrics["impressions"] == "500"
        assert results[0].metrics["clicks"] == "50"
        
        # Verify Session / API setup
        mock_session.assert_called_once()
        args, kwargs = mock_session.call_args
        assert kwargs["access_token"] == "fake_ads_token"
        mock_api.assert_called_once_with(mock_session.return_value)
        mock_ad_account.assert_called_once_with("act_12345", api=mock_api.return_value)

@patch("app.connectors.meta.FacebookSession")
@patch("app.connectors.meta.FacebookAdsApi")
@patch("app.connectors.meta.Page")
def test_meta_organic_fetch_data(mock_page, mock_api, mock_session):
    mock_instance = MagicMock()
    mock_page.return_value = mock_instance
    # Page Insights API returns one object per metric with name + values
    mock_instance.get_insights.return_value = [
        {"name": "page_impressions", "period": "day", "values": [{"value": 1000, "end_time": "2026-05-02T07:00:00+0000"}]},
        {"name": "page_engagements", "period": "day", "values": [{"value": 200, "end_time": "2026-05-02T07:00:00+0000"}]}
    ]
    
    connector = MetaOrganicConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_token": "fake_page_token",
            "page_id": "1033741419822859"
        }
        
        req = DataRequest(
            platform="meta_organic",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 7),
            metrics=["page_impressions", "page_engagements"],
            client_id="test_client",
            user_id="test_user",
            account_id="1033741419822859"
        )
        
        results = connector.fetch_data(req)
        assert len(results) == 1
        assert results[0].campaign_name == "Page_Insights"
        assert results[0].date == "2026-05-02"
        assert results[0].metrics["page_impressions"] == 1000
        assert results[0].metrics["page_engagements"] == 200
        
        # Verify Session / API setup
        mock_session.assert_called_once()
        args, kwargs = mock_session.call_args
        assert kwargs["access_token"] == "fake_page_token"
        mock_api.assert_called_once_with(mock_session.return_value)
        mock_page.assert_called_once_with("1033741419822859", api=mock_api.return_value)
