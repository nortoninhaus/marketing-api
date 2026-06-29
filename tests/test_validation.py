"""
Tests for platform parameter and metric validation logic and endpoints.
"""

from datetime import date
import pytest
from unittest.mock import patch, MagicMock
from app.metrics import validate_platform_params
from app.models.requests import DataRequest

def test_validate_platform_params_direct():
    # 1. Test valid configurations
    errors = validate_platform_params("meta_ads", "act_12345", post_id="post_999")
    assert not errors

    errors = validate_platform_params("google_ads", "123-456-7890")
    assert not errors

    errors = validate_platform_params("ga4", "properties/999888")
    assert not errors

    errors = validate_platform_params("google_play", "com.inhaus.marketing")
    assert not errors

    # 2. Test invalid optional parameters (silent error prevention)
    errors = validate_platform_params("meta_ads", "act_12345", video_id="vid_111")
    assert len(errors) == 1
    assert "video_id" in errors[0]

    errors = validate_platform_params("google_ads", "1234567890", post_id="post_123")
    assert len(errors) == 1
    assert "post_id" in errors[0]

    # 3. Test invalid account_id formats
    errors = validate_platform_params("meta_ads", "invalid_format")
    assert len(errors) == 1
    assert "format" in errors[0] or "meta_ads" in errors[0]

    errors = validate_platform_params("google_ads", "12345")
    assert len(errors) == 1
    assert "10" in errors[0] or "google_ads" in errors[0]


def test_data_request_pydantic_validation():
    # Valid model
    req = DataRequest(
        platform="meta_ads",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
        metrics=["impressions"],
        client_id="c_1",
        user_id="u_1",
        account_id="act_12345",
        post_id="post_123"
    )
    assert req.account_id == "act_12345"

    # Invalid model due to invalid parameter (video_id in meta_ads)
    with pytest.raises(ValueError) as exc:
        DataRequest(
            platform="meta_ads",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 5),
            metrics=["impressions"],
            client_id="c_1",
            user_id="u_1",
            account_id="act_12345",
            video_id="vid_123"
        )
    assert "video_id" in str(exc.value)


def test_validate_endpoint_unauthorized(client):
    payload = {
        "platform": "meta_ads",
        "metrics": ["impressions"],
        "account_id": "act_123"
    }
    resp = client.post("/api/v1/validate", json=payload)
    assert resp.status_code in (401, 403)


def test_validate_endpoint_authorized(client, auth_headers):
    # Valid
    payload = {
        "platform": "meta_ads",
        "metrics": ["impressions"],
        "use_generic_names": True,
        "account_id": "act_12345"
    }
    resp = client.post("/api/v1/validate", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert "impressions" in data["valid_metrics"]
    assert data["translations"]["impressions"] == "impressions"

    # Invalid metric & parameter
    payload = {
        "platform": "meta_ads",
        "metrics": ["followers"],
        "use_generic_names": True,
        "account_id": "invalid_acc",
        "video_id": "vid_abc"
    }
    resp = client.post("/api/v1/validate", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert len(data["parameter_errors"]) > 0
    assert len(data["invalid_metrics"]) > 0


@patch("app.services.credential_store.credential_store.list_oauth_connections")
@patch("app.services.credential_store.credential_store.get_credentials")
def test_credentials_status_endpoint(mock_get, mock_list, client, auth_headers):
    # Setup mock returns
    mock_list.return_value = [{"account_name": "Test Account"}]
    mock_get.return_value = None

    resp = client.get("/api/v1/credentials/status?client_id=client_test", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["client_id"] == "client_test"
    assert "platforms" in data
    # Check meta_ads status
    assert data["platforms"]["meta_ads"]["has_credentials"] is True
    assert data["platforms"]["meta_ads"]["credential_type"] == "oauth"


def test_campaign_data_dry_run(client, auth_headers):
    payload = {
        "platform": "meta_ads",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "metrics": ["impressions"],
        "client_id": "test_client",
        "user_id": "test_user",
        "account_id": "act_12345",
        "dry_run": True
    }
    resp = client.post("/api/v1/campaign-data", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["data"] == []
    assert data["metadata"]["dry_run"] is True


@patch("app.services.credential_store.credential_store.list_oauth_connections")
@patch("app.services.credential_store.credential_store.get_credentials")
def test_validate_endpoint_semantic_failure(mock_get, mock_list, client, auth_headers):
    mock_list.return_value = []
    mock_get.return_value = None

    payload = {
        "platform": "meta_ads",
        "metrics": ["impressions"],
        "client_id": "client_without_creds",
        "account_id": "act_12345"
    }
    resp = client.post("/api/v1/validate", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert any("semántica" in err for err in data["parameter_errors"])


def test_base_connector_rate_limit_parsing():
    import requests as _requests
    from app.connectors.base import BaseConnector
    
    class TestConnector(BaseConnector):
        platform_name = "test"
        def fetch_data(self, request): return []
        def get_schema(self): return {}

    response = _requests.Response()
    response.status_code = 429
    response.headers = {"x-rate-limit-remaining": "0"}
    
    error = _requests.exceptions.HTTPError(response=response)
    
    connector = TestConnector()
    detail = connector.handle_error(error)
    
    assert detail.code == "RATE_LIMIT"
    assert detail.rate_limit_remaining == 0


def test_platforms_api_version(client, auth_headers):
    resp = client.get("/api/v1/platforms", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Check that api_version is populated on all items
    for platform in data:
        assert "api_version" in platform
        assert platform["api_version"] is not None


@patch("app.services.dispatcher.dispatcher.get_connector")
@patch("app.services.credential_store.credential_store.resolve_credentials")
def test_campaign_data_pagination_slicing(mock_resolve, mock_get_connector, client, auth_headers):
    from app.models.responses import CampaignData
    mock_resolve.return_value = {"access_token": "mock_token"}
    
    mock_connector = MagicMock()
    mock_connector.platform_name = "meta_ads"
    # Return 5 items
    mock_connector.fetch_with_retry.return_value = [
        CampaignData(campaign_name=f"Campaign {i}", date="2026-06-01", metrics={})
        for i in range(5)
    ]
    mock_get_connector.return_value = mock_connector

    # Request first page of 2 items
    payload = {
        "platform": "meta_ads",
        "start_date": "2026-06-01",
        "end_date": "2026-06-05",
        "metrics": ["impressions"],
        "client_id": "test_client",
        "user_id": "test_user",
        "account_id": "act_12345",
        "limit": 2
    }
    resp = client.post("/api/v1/campaign-data", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 2
    assert data["data"][0]["campaign_name"] == "Campaign 0"
    assert data["data"][1]["campaign_name"] == "Campaign 1"
    assert data["pagination"]["has_next"] is True
    assert data["pagination"]["next_page_token"] == "2"
    assert data["pagination"]["total_count"] == 5

    # Request second page using next_page_token
    payload["next_page_token"] = "2"
    resp = client.post("/api/v1/campaign-data", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 2
    assert data["data"][0]["campaign_name"] == "Campaign 2"
    assert data["data"][1]["campaign_name"] == "Campaign 3"
    assert data["pagination"]["has_next"] is True
    assert data["pagination"]["next_page_token"] == "4"

    # Request third page
    payload["next_page_token"] = "4"
    resp = client.post("/api/v1/campaign-data", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["campaign_name"] == "Campaign 4"
    assert data["pagination"]["has_next"] is False
    assert data["pagination"]["next_page_token"] is None


@patch("app.services.credential_store.credential_store.resolve_credentials")
@patch("app.connectors.threads.ThreadsConnector.fetch_comments")
def test_comments_pagination_slicing(mock_fetch_comments, mock_resolve, client, auth_headers):
    from app.models.responses import CommentData
    mock_resolve.return_value = {"access_token": "mock_token"}
    mock_fetch_comments.return_value = [
        CommentData(comment_id=f"comment_{i}", text=f"text {i}", author=f"author {i}", timestamp="2026-06-01T12:00:00Z")
        for i in range(5)
    ]

    payload = {
        "platform": "threads",
        "post_id": "post_123",
        "client_id": "test_client",
        "user_id": "test_user",
        "account_id": "threads_acc",
        "limit": 2
    }
    resp = client.post("/api/v1/comments", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["comments"]) == 2
    assert data["comments"][0]["comment_id"] == "comment_0"
    assert data["next_page_token"] == "2"
    assert data["total_comments"] == 5

    payload["next_page_token"] = "2"
    resp = client.post("/api/v1/comments", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["comments"]) == 2
    assert data["comments"][0]["comment_id"] == "comment_2"
    assert data["next_page_token"] == "4"


@patch("app.services.dispatcher.dispatcher.get_connector")
@patch("app.services.credential_store.credential_store.resolve_credentials")
def test_campaign_data_rate_limit_propagation(mock_resolve, mock_get_connector, client, auth_headers):
    mock_resolve.return_value = {"access_token": "mock_token"}
    
    from app.connectors.base import BaseConnector
    
    class DummyConnector(BaseConnector):
        platform_name = "meta_ads"
        def get_schema(self): return {}
        def fetch_data(self, request):
            self._record_rate_limit({"x-rate-limit-remaining": "42"})
            return []
            
    mock_connector = DummyConnector()
    mock_get_connector.return_value = mock_connector

    payload = {
        "platform": "meta_ads",
        "start_date": "2026-06-01",
        "end_date": "2026-06-05",
        "metrics": ["impressions"],
        "client_id": "test_client",
        "user_id": "test_user",
        "account_id": "act_12345"
    }
    resp = client.post("/api/v1/campaign-data", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["rate_limit_remaining"] == 42


import logging
def test_audit_logging(client, auth_headers, caplog):
    caplog.set_level(logging.INFO)
    payload = {
        "platform": "meta_ads",
        "start_date": "2026-06-01",
        "end_date": "2026-06-05",
        "metrics": ["impressions"],
        "client_id": "audit_client_123",
        "user_id": "audit_user_456",
        "account_id": "act_12345",
        "dry_run": True
    }
    # Test campaign-data
    client.post("/api/v1/campaign-data", json=payload, headers=auth_headers)
    assert any("AUDIT LOG: client_id='audit_client_123' user_id='audit_user_456' platform='meta_ads'" in record.message for record in caplog.records)

    caplog.clear()

    # Test batch
    batch_payload = {"requests": [payload]}
    client.post("/api/v1/batch", json=batch_payload, headers=auth_headers)
    assert any("AUDIT LOG: client_id='audit_client_123' user_id='audit_user_456' platform='batch'" in record.message for record in caplog.records)


def test_meta_ads_filters_and_attribution():
    from app.connectors.meta import MetaAdsConnector
    from app.models.requests import DataRequest
    from datetime import date
    
    connector = MetaAdsConnector()
    request = DataRequest(
        platform="meta_ads",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
        metrics=["impressions"],
        client_id="c_1",
        user_id="u_1",
        account_id="act_12345",
        action_attribution_windows=["7d_click", "1d_view"],
        filters={"campaign.name": "BlackFriday"}
    )
    
    with patch("facebook_business.adobjects.adaccount.AdAccount.get_insights") as mock_get_insights:
        mock_get_insights.return_value = []
        connector.fetch_data(request)
        
        args, kwargs = mock_get_insights.call_args
        params = kwargs.get("params", {})
        assert params.get("action_attribution_windows") == ["7d_click", "1d_view"]
        assert params.get("filtering") == [{"field": "campaign.name", "operator": "EQUAL", "value": ["BlackFriday"]}]


def test_google_ads_filters_and_ad_level():
    from app.connectors.google_ads import GoogleAdsConnector
    from app.models.requests import DataRequest
    from datetime import date
    
    connector = GoogleAdsConnector()
    request = DataRequest(
        platform="google_ads",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
        metrics=["impressions"],
        client_id="c_1",
        user_id="u_1",
        account_id="123-456-7890",
        dimensions=["ad_group_ad.ad.name"],
        filters={"campaign.status": "ENABLED"}
    )
    
    with patch.object(GoogleAdsConnector, "_build_client") as mock_build_client:
        mock_client = MagicMock()
        mock_build_client.return_value = mock_client
        mock_service = mock_client.get_service.return_value
        mock_service.search_stream.return_value = []
        
        connector.fetch_data(request)
        
        args, kwargs = mock_service.search_stream.call_args
        query = kwargs.get("query", "")
        # GAQL should contain FROM ad_group_ad and campaign.status = 'ENABLED'
        assert "FROM ad_group_ad" in query
        assert "campaign.status = 'ENABLED'" in query


def test_ga4_filters():
    from app.connectors.ga4 import GA4Connector
    from app.models.requests import DataRequest
    from datetime import date
    
    connector = GA4Connector()
    request = DataRequest(
        platform="ga4",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
        metrics=["sessions"],
        client_id="c_1",
        user_id="u_1",
        account_id="properties/12345",
        filters={"country": "US"}
    )
    
    with patch.object(GA4Connector, "_build_client") as mock_build_client:
        mock_client = MagicMock()
        mock_build_client.return_value = mock_client
        mock_client.run_report.return_value.rows = []
        
        connector.fetch_data(request)
        
        args, kwargs = mock_client.run_report.call_args
        req_arg = args[0]
        # Should have a dimension_filter for country with matching value US
        assert req_arg.dimension_filter.filter.field_name == "country"
        assert req_arg.dimension_filter.filter.string_filter.value == "US"


from unittest.mock import patch, MagicMock

def test_youtube_dimensions_and_filters():
    from app.connectors.youtube import YouTubeConnector
    from app.models.requests import DataRequest
    from datetime import date
    
    connector = YouTubeConnector()
    request = DataRequest(
        platform="youtube",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
        metrics=["views"],
        client_id="c_1",
        user_id="u_1",
        account_id="channel_123",
        dimensions=["deviceType", "country"],
        filters={"country": "US"}
    )
    
    with patch("app.connectors.youtube.build") as mock_build:
        mock_analytics = MagicMock()
        mock_build.return_value = mock_analytics
        mock_query = mock_analytics.reports.return_value.query
        mock_query.return_value.execute.return_value = {
            "columnHeaders": [{"name": "day"}, {"name": "deviceType"}, {"name": "country"}, {"name": "views"}],
            "rows": [["2026-06-01", "MOBILE", "US", 100]]
        }
        
        credentials = {"access_token": "mock-token", "channel_id": "channel_123"}
        with patch.object(YouTubeConnector, "get_credentials", return_value=credentials):
            res = connector.fetch_data(request)
            
            args, kwargs = mock_query.call_args
            assert kwargs.get("dimensions") == "deviceType,country"
            assert "country==US" in kwargs.get("filters", "")
            assert len(res) == 1
            assert res[0].campaign_name == "MOBILE | US"


def test_x_ads_entities_and_stats():
    from app.connectors.x_twitter import XAdsConnector
    from app.models.requests import DataRequest
    from datetime import date
    
    connector = XAdsConnector()
    request = DataRequest(
        platform="x_ads",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
        metrics=["impressions", "spend"],
        client_id="c_1",
        user_id="u_1",
        account_id="act_123",
        dimensions=["line_item_id"]
    )
    
    with patch("app.connectors.x_twitter.requests.get") as mock_get:
        mock_list_resp = MagicMock()
        mock_list_resp.json.return_value = {"data": [{"id": "li_999"}]}
        
        mock_stats_resp = MagicMock()
        mock_stats_resp.json.return_value = {
            "data": {
                "li_999": [
                    {
                        "id": "li_999",
                        "metrics": {
                            "impressions": [1000, 2000],
                            "billed_charge_local_micro": [5000000, 10000000]
                        }
                    }
                ]
            }
        }
        mock_get.side_effect = [mock_list_resp, mock_stats_resp]
        
        credentials = {"access_token": "mock-token", "account_id": "act_123"}
        with patch.object(XAdsConnector, "get_credentials", return_value=credentials):
            res = connector.fetch_data(request)
            
            list_call_args, list_call_kwargs = mock_get.call_args_list[0]
            assert "line_items" in list_call_args[0]
            
            stats_call_args, stats_call_kwargs = mock_get.call_args_list[1]
            assert "stats" in stats_call_args[0]
            assert stats_call_kwargs.get("params", {}).get("entity") == "LINE_ITEM"
            assert stats_call_kwargs.get("params", {}).get("entity_ids") == "li_999"
            
            assert len(res) == 2
            assert res[0].campaign_name == "li_999"
            assert res[0].metrics["impressions"] == 1000
            assert res[0].metrics["spend"] == 5.0
            assert res[1].metrics["spend"] == 10.0


def test_linkedin_rest_api():
    from app.connectors.linkedin import LinkedInAdsConnector
    from app.models.requests import DataRequest
    from datetime import date
    
    connector = LinkedInAdsConnector()
    request = DataRequest(
        platform="linkedin_ads",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
        metrics=["impressions"],
        client_id="c_1",
        user_id="u_1",
        account_id="123",
        dimensions=["creative"]
    )
    
    with patch("app.connectors.linkedin.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "elements": [
                {
                    "creative": "urn:li:sponsoredCreative:888",
                    "dateRange": {
                        "start": {"day": 1, "month": 6, "year": 2026}
                    },
                    "impressions": 500
                }
            ]
        }
        mock_get.return_value = mock_resp
        
        credentials = {"access_token": "mock-token", "ad_account_id": "123"}
        with patch.object(LinkedInAdsConnector, "get_credentials", return_value=credentials):
            res = connector.fetch_data(request)
            
            args, kwargs = mock_get.call_args
            assert "rest/adAnalytics" in args[0]
            assert "pivot=CREATIVE" in args[0]
            assert "accounts=List(urn:li:sponsoredAdAccount:123)" in args[0]
            assert kwargs.get("headers", {}).get("LinkedIn-Version") == "202405"
            
            assert len(res) == 1
            assert res[0].campaign_name == "urn:li:sponsoredCreative:888"
            assert res[0].metrics["impressions"] == 500


def test_apple_search_ads_post_v5():
    from app.connectors.apple import AppleAdsConnector
    from app.models.requests import DataRequest
    from datetime import date
    
    connector = AppleAdsConnector()
    request = DataRequest(
        platform="apple_ads",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
        metrics=["impressions", "taps"],
        client_id="c_1",
        user_id="u_1",
        account_id="org_123"
    )
    
    with patch("app.connectors.apple.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "reportingDataResponse": [
                    {
                        "row": {
                            "campaignName": "Apple Promo Campaign",
                            "granularity": [
                                {"date": "2026-06-01", "impressions": 100, "taps": 5},
                                {"date": "2026-06-02", "impressions": 200, "taps": 10}
                            ]
                        }
                    }
                ]
            }
        }
        mock_post.return_value = mock_resp
        
        credentials = {"access_token": "mock-token", "org_id": "org_123"}
        with patch.object(AppleAdsConnector, "get_credentials", return_value=credentials):
            res = connector.fetch_data(request)
            
            args, kwargs = mock_post.call_args
            assert "v5/reports/campaigns" in args[0]
            payload = kwargs.get("json", {})
            assert payload.get("startTime") == "2026-06-01"
            assert payload.get("selector", {}).get("fields") is not None
            
            assert len(res) == 2
            assert res[0].campaign_name == "Apple Promo Campaign"
            assert res[0].date == "2026-06-01"
            assert res[0].metrics["impressions"] == 100
            assert res[0].metrics["taps"] == 5


def test_spotify_ads_connector():
    from app.connectors.spotify import SpotifyAdsConnector
    from app.models.requests import DataRequest
    from datetime import date
    
    connector = SpotifyAdsConnector()
    request = DataRequest(
        platform="spotify_ads",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
        metrics=["impressions", "spend"],
        client_id="c_1",
        user_id="u_1",
        account_id="spot_123"
    )
    
    with patch("app.connectors.spotify.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "campaign_name": "Spotify Summer Vibes",
                    "date": "2026-06-01",
                    "metrics": {
                        "IMPRESSIONS": 5000,
                        "SPEND": 25.5
                    }
                }
            ]
        }
        mock_get.return_value = mock_resp
        
        credentials = {"access_token": "mock-token", "ad_account_id": "spot_123"}
        with patch.object(SpotifyAdsConnector, "get_credentials", return_value=credentials):
            res = connector.fetch_data(request)
            
            args, kwargs = mock_get.call_args
            assert "reports/aggregate" in args[0]
            assert "IMPRESSIONS,SPEND" in kwargs.get("params", {}).get("metrics")
            
            assert len(res) == 1
            assert res[0].campaign_name == "Spotify Summer Vibes"
            assert res[0].metrics["impressions"] == 5000
            assert res[0].metrics["spend"] == 25.5




