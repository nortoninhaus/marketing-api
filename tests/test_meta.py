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
        assert results[0].metrics["impressions"] == 500
        assert results[0].metrics["clicks"] == 50
        
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
        {"name": "page_media_view", "period": "day", "values": [{"value": 1000, "end_time": "2026-05-02T07:00:00+0000"}]},
        {"name": "page_post_engagements", "period": "day", "values": [{"value": 200, "end_time": "2026-05-02T07:00:00+0000"}]}
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
            metrics=["page_media_view", "page_post_engagements"],
            client_id="test_client",
            user_id="test_user",
            account_id="1033741419822859"
        )
        
        results = connector.fetch_data(req)
        assert len(results) == 1
        assert results[0].campaign_name == "Page_Insights"
        assert results[0].date == "2026-05-02"
        assert results[0].metrics["page_media_view"] == 1000
        assert results[0].metrics["page_post_engagements"] == 200
        
        # Verify Session / API setup
        mock_session.assert_called_once()
        args, kwargs = mock_session.call_args
        assert kwargs["access_token"] == "fake_page_token"
        mock_api.assert_called_once_with(mock_session.return_value)
        mock_page.assert_called_once_with("1033741419822859", api=mock_api.return_value)


@patch("app.connectors.meta.httpx.Client")
def test_instagram_fetch_data(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {
                "name": "views",
                "values": [{"value": 5000, "end_time": "2026-05-02T23:59:59+0000"}]
            },
            {
                "name": "reach",
                "values": [{"value": 3200, "end_time": "2026-05-02T23:59:59+0000"}]
            }
        ]
    }
    mock_client.get.return_value = mock_resp

    connector = MetaOrganicConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_token": "fake_ig_token",
            "page_id": "ig_12345",
            "is_instagram": True
        }

        req = DataRequest(
            platform="meta_organic",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 7),
            metrics=["views", "reach"],
            client_id="test_client",
            user_id="test_user",
            account_id="ig_12345"
        )

        results = connector.fetch_data(req)
        assert len(results) == 1
        assert results[0].campaign_name == "Instagram_Organic_Insights"
        assert results[0].metrics["views"] == 5000
        assert results[0].metrics["reach"] == 3200


@patch("app.connectors.meta.httpx.Client")
def test_instagram_fetch_comments(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {
                "id": "c_1",
                "text": "Great photo!",
                "username": "user_a",
                "timestamp": "2026-05-02T12:00:00+0000",
                "like_count": 5,
                "replies": {
                    "data": [
                        {
                            "id": "r_1",
                            "text": "Thanks!",
                            "username": "author_user",
                            "timestamp": "2026-05-02T12:05:00+0000",
                            "like_count": 1
                        }
                    ]
                }
            }
        ],
        "paging": {}
    }
    mock_client.get.return_value = mock_resp

    connector = MetaOrganicConnector()
    comments = connector.fetch_comments("post_123", "fake_token", is_instagram=True)
    assert len(comments) == 1
    assert comments[0].comment_id == "c_1"
    assert comments[0].text == "Great photo!"
    assert comments[0].author == "user_a"
    assert comments[0].like_count == 5
    assert comments[0].reply_count == 1
    assert len(comments[0].replies) == 1
    assert comments[0].replies[0].comment_id == "r_1"
    assert comments[0].replies[0].text == "Thanks!"


@patch("app.connectors.meta.httpx.Client")
def test_page_fetch_comments(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {
                "id": "c_page_1",
                "message": "Nice page post",
                "from": {"name": "Page Fan", "id": "fan_1"},
                "created_time": "2026-05-02T12:00:00+0000",
                "comment_count": 0,
                "like_count": 2
            }
        ],
        "paging": {}
    }
    mock_client.get.return_value = mock_resp

    connector = MetaOrganicConnector()
    comments = connector.fetch_comments("page_post_123", "fake_token", is_instagram=False)
    assert len(comments) == 1
    assert comments[0].comment_id == "c_page_1"
    assert comments[0].text == "Nice page post"
    assert comments[0].author == "Page Fan"
    assert comments[0].like_count == 2
    assert comments[0].reply_count == 0


@patch("app.connectors.meta.httpx.Client")
def test_meta_ads_fetch_comments(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {
                "id": "c_ad_1",
                "message": "How much does it cost?",
                "from": {"name": "Interested Customer"},
                "created_time": "2026-05-02T12:00:00+0000",
                "comment_count": 0,
                "like_count": 0
            }
        ],
        "paging": {}
    }
    mock_client.get.return_value = mock_resp

    connector = MetaAdsConnector()
    comments = connector.fetch_comments("ad_creative_post_123", "fake_token")
    assert len(comments) == 1
    assert comments[0].comment_id == "c_ad_1"
    assert comments[0].text == "How much does it cost?"
    assert comments[0].author == "Interested Customer"


@patch("app.connectors.meta.FacebookSession")
@patch("app.connectors.meta.FacebookAdsApi")
@patch("app.connectors.meta.Page")
@patch("app.connectors.meta.httpx.Client")
def test_meta_organic_fetch_data_combined(mock_client_class, mock_page, mock_api, mock_session):
    mock_instance = MagicMock()
    mock_page.return_value = mock_instance
    
    mock_instance.get_insights.return_value = [
        {"name": "page_media_view", "period": "day", "values": [{"value": 1200, "end_time": "2026-05-02T07:00:00+0000"}]}
    ]

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {
                "id": "post_1",
                "message": "Hello World",
                "created_time": "2026-05-02T10:00:00+0000",
                "insights": {
                    "data": [
                        {
                            "name": "post_clicks",
                            "values": [{"value": 42}]
                        }
                    ]
                }
            }
        ]
    }
    mock_client.get.return_value = mock_resp

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
            metrics=["page_media_view", "post_clicks"],
            dimensions=["post_id"],
            client_id="test_client",
            user_id="test_user",
            account_id="1033741419822859"
        )
        
        results = connector.fetch_data(req)
        assert len(results) == 2
        
        post_campaign = next(c for c in results if "Post_post_1" in c.campaign_name)
        assert post_campaign.metrics["post_clicks"] == 42
        assert post_campaign.date == "2026-05-02"

        page_campaign = next(c for c in results if c.campaign_name == "Page_Insights")
        assert page_campaign.metrics["page_media_view"] == 1200
        assert page_campaign.date == "2026-05-02"


