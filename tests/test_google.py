"""
Unit tests for Google Ads, GA4, YouTube, and Google Play connectors.
"""

from datetime import date
import json
from unittest.mock import MagicMock, patch, ANY

import pytest
from fastapi import HTTPException
from google.api_core.exceptions import ResourceExhausted

from app.models.requests import DataRequest
from app.connectors.google_ads import GoogleAdsConnector
from app.connectors.ga4 import GA4Connector
from app.connectors.youtube import YouTubeConnector
from app.connectors.google_play import GooglePlayConnector


# ═══════════════════════════════════════════════════════════════════
# GOOGLE ADS CONNECTOR TESTS
# ═══════════════════════════════════════════════════════════════════

class MockAdsRow:
    def __init__(self, campaign_name, date_str, impressions, clicks, ad_group_name=None, keyword_text=None):
        self.campaign = MagicMock()
        self.campaign.name = campaign_name
        self.segments = MagicMock()
        self.segments.date = date_str
        self.metrics = MagicMock()
        self.metrics.impressions = impressions
        self.metrics.clicks = clicks
        
        if ad_group_name:
            self.ad_group = MagicMock()
            self.ad_group.name = ad_group_name
        if keyword_text:
            self.ad_group_criterion = MagicMock()
            self.ad_group_criterion.keyword = MagicMock()
            self.ad_group_criterion.keyword.text = keyword_text

class MockAdsBatch:
    def __init__(self, rows):
        self.results = rows

@patch("app.connectors.google_ads.GoogleAdsClient")
def test_google_ads_fetch_data_campaign_level(mock_ads_client_class):
    mock_client = MagicMock()
    mock_ads_client_class.load_from_dict.return_value = mock_client
    
    mock_service = MagicMock()
    mock_client.get_service.return_value = mock_service
    
    # Mock search_stream return value
    rows = [
        MockAdsRow("Campaign Alpha", "2026-05-01", 1000, 100),
        MockAdsRow("Campaign Beta", "2026-05-02", 2000, 150),
    ]
    mock_service.search_stream.return_value = [MockAdsBatch(rows)]
    
    connector = GoogleAdsConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "developer_token": "fake_dev_token",
            "client_id": "fake_client_id",
            "client_secret": "fake_secret",
            "refresh_token": "fake_refresh_token",
            "customer_id": "1234567890",
        }
        
        req = DataRequest(
            platform="google_ads",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 7),
            metrics=["impressions", "clicks"],
            client_id="test_client",
            user_id="test_user",
            account_id="1234567890"
        )
        
        results = connector.fetch_data(req)
        assert len(results) == 2
        assert results[0].campaign_name == "Campaign Alpha"
        assert results[0].date == "2026-05-01"
        assert results[0].metrics["impressions"] == 1000
        assert results[0].metrics["clicks"] == 100
        
        assert results[1].campaign_name == "Campaign Beta"
        assert results[1].date == "2026-05-02"
        assert results[1].metrics["impressions"] == 2000
        assert results[1].metrics["clicks"] == 150
        
        # Verify query table choice was campaign
        mock_service.search_stream.assert_called_once()
        args, kwargs = mock_service.search_stream.call_args
        assert "FROM campaign" in kwargs["query"]

@patch("app.connectors.google_ads.GoogleAdsClient")
def test_google_ads_fetch_data_ad_group_level(mock_ads_client_class):
    mock_client = MagicMock()
    mock_ads_client_class.load_from_dict.return_value = mock_client
    mock_service = MagicMock()
    mock_client.get_service.return_value = mock_service
    
    rows = [
        MockAdsRow("Campaign Alpha", "2026-05-01", 500, 50, ad_group_name="AG One"),
    ]
    mock_service.search_stream.return_value = [MockAdsBatch(rows)]
    
    connector = GoogleAdsConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "developer_token": "fake_dev_token",
            "client_id": "fake_client_id",
            "client_secret": "fake_secret",
            "refresh_token": "fake_refresh_token",
            "customer_id": "1234567890",
        }
        
        req = DataRequest(
            platform="google_ads",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 7),
            metrics=["impressions", "clicks"],
            dimensions=["campaign.name", "ad_group.name"],
            client_id="test_client",
            user_id="test_user",
            account_id="1234567890"
        )
        
        results = connector.fetch_data(req)
        assert len(results) == 1
        assert results[0].campaign_name == "Campaign Alpha | AG One"
        
        args, kwargs = mock_service.search_stream.call_args
        assert "FROM ad_group" in kwargs["query"]


class MockSegmentedAdsRow:
    def __init__(self, campaign_name, date_str, action_name, conversions, conversions_value):
        self.campaign = MagicMock()
        self.campaign.name = campaign_name
        self.segments = MagicMock()
        self.segments.date = date_str
        self.segments.conversion_action = "customers/123/conversionActions/456"
        self.conversion_action = MagicMock()
        self.conversion_action.name = action_name
        self.metrics = MagicMock()
        self.metrics.conversions = conversions
        self.metrics.conversions_value = conversions_value


@patch("app.connectors.google_ads.GoogleAdsClient")
def test_google_ads_custom_conversion_metrics(mock_ads_client_class):
    mock_client = MagicMock()
    mock_ads_client_class.load_from_dict.return_value = mock_client
    
    mock_service = MagicMock()
    mock_client.get_service.return_value = mock_service
    
    seg_rows = [
        MockSegmentedAdsRow("Campaign Alpha", "2026-05-01", "account_created_Sipy_Personas", 12.0, 120.0),
        MockSegmentedAdsRow("Campaign Alpha", "2026-05-01", "account_created_ahorro_futuro", 8.0, 80.0),
    ]
    main_rows = [
        MockAdsRow("Campaign Alpha", "2026-05-01", 1000, 100),
    ]
    
    mock_service.search_stream.side_effect = [
        [MockAdsBatch(seg_rows)],
        [MockAdsBatch(main_rows)],
    ]
    
    connector = GoogleAdsConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "developer_token": "fake_dev_token",
            "client_id": "fake_client_id",
            "client_secret": "fake_secret",
            "refresh_token": "fake_refresh_token",
            "customer_id": "1234567890",
        }
        
        req = DataRequest(
            platform="google_ads",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 7),
            metrics=["impressions", "clicks", "account_created_Sipy_Personas", "account_created_ahorro_futuro_value"],
            client_id="test_client",
            user_id="test_user",
            account_id="1234567890"
        )
        
        results = connector.fetch_data(req)
        assert len(results) == 1
        assert results[0].campaign_name == "Campaign Alpha"
        assert results[0].metrics["impressions"] == 1000
        assert results[0].metrics["clicks"] == 100
        assert results[0].metrics["account_created_Sipy_Personas"] == 12.0
        assert results[0].metrics["account_created_ahorro_futuro_value"] == 80.0



# ═══════════════════════════════════════════════════════════════════
# GA4 CONNECTOR TESTS
# ═══════════════════════════════════════════════════════════════════

class MockGA4DimHeader:
    def __init__(self, name):
        self.name = name

class MockGA4DimValue:
    def __init__(self, value):
        self.value = value

class MockGA4MetricValue:
    def __init__(self, value):
        self.value = value

class MockGA4Row:
    def __init__(self, dim_vals, metric_vals):
        self.dimension_values = [MockGA4DimValue(v) for v in dim_vals]
        self.metric_values = [MockGA4MetricValue(v) for v in metric_vals]

class MockGA4Response:
    def __init__(self, rows, dim_headers):
        self.rows = rows
        self.dimension_headers = [MockGA4DimHeader(h) for h in dim_headers]

@patch("app.connectors.ga4.BetaAnalyticsDataClient")
def test_ga4_fetch_data_success(mock_ga4_client_class):
    mock_client = MagicMock()
    mock_ga4_client_class.return_value = mock_client
    
    # Mock run_report to return 2 rows
    rows = [
        MockGA4Row(["20260501", "google / cpc"], [150, 25.5]),
        MockGA4Row(["20260502", "direct / none"], [80, 0.0]),
    ]
    mock_client.run_report.return_value = MockGA4Response(rows, ["date", "sessionSourceMedium"])
    
    connector = GA4Connector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_token": "fake_ga4_token",
            "refresh_token": "fake_refresh_token",
            "property_id": "987654321",
        }
        
        req = DataRequest(
            platform="ga4",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 7),
            metrics=["sessions", "totalRevenue"],
            dimensions=["sessionSourceMedium"],
            client_id="test_client",
            user_id="test_user",
            account_id="987654321"
        )
        
        results = connector.fetch_data(req)
        assert len(results) == 2
        
        assert results[0].campaign_name == "google / cpc"
        assert results[0].date == "2026-05-01"
        assert results[0].metrics["sessions"] == 150
        assert results[0].metrics["totalRevenue"] == 25.5
        
        assert results[1].campaign_name == "direct / none"
        assert results[1].date == "2026-05-02"
        assert results[1].metrics["sessions"] == 80
        assert results[1].metrics["totalRevenue"] == 0.0

@patch("app.connectors.ga4.BetaAnalyticsDataClient")
def test_ga4_fetch_data_quota_limit(mock_ga4_client_class):
    mock_client = MagicMock()
    mock_ga4_client_class.return_value = mock_client
    mock_client.run_report.side_effect = ResourceExhausted("Resource exhausted")
    
    connector = GA4Connector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_token": "fake_ga4_token",
            "property_id": "987654321",
        }
        
        req = DataRequest(
            platform="ga4",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 7),
            metrics=["sessions"],
            client_id="test_client",
            user_id="test_user",
            account_id="987654321"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            connector.fetch_data(req)
        assert exc_info.value.status_code == 429
        assert "quota exhausted" in exc_info.value.detail


# ═══════════════════════════════════════════════════════════════════
# YOUTUBE CONNECTOR TESTS
# ═══════════════════════════════════════════════════════════════════

@patch("app.connectors.youtube.build")
def test_youtube_fetch_data_analytics_v2(mock_build):
    mock_analytics_service = MagicMock()
    # Chain of mock calls: build("youtubeAnalytics", "v2", ...).reports().query(...).execute()
    mock_build.return_value = mock_analytics_service
    
    mock_reports = MagicMock()
    mock_analytics_service.reports.return_value = mock_reports
    
    mock_query = MagicMock()
    mock_reports.query.return_value = mock_query
    
    mock_query.execute.return_value = {
        "columnHeaders": [{"name": "day"}, {"name": "views"}, {"name": "likes"}],
        "rows": [
            ["2026-05-01", 500, 45],
            ["2026-05-02", 750, 60],
        ]
    }
    
    connector = YouTubeConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_token": "fake_yt_oauth_token",
            "refresh_token": "fake_yt_refresh_token",
            "channel_id": "UC1234567890",
            "api_key": "fake_api_key",
        }
        
        req = DataRequest(
            platform="youtube",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 7),
            metrics=["views", "likes"],
            client_id="test_client",
            user_id="test_user",
            account_id="UC1234567890"
        )
        
        results = connector.fetch_data(req)
        assert len(results) == 2
        assert results[0].campaign_name == "YouTube_Channel"
        assert results[0].date == "2026-05-01"
        assert results[0].metrics["views"] == 500
        assert results[0].metrics["likes"] == 45
        
        assert results[1].date == "2026-05-02"
        assert results[1].metrics["views"] == 750
        assert results[1].metrics["likes"] == 60
        
        # Verify build was called with youtubeAnalytics
        mock_build.assert_called_with("youtubeAnalytics", "v2", credentials=ANY)

@patch("app.connectors.youtube.build")
def test_youtube_fetch_data_public_v3_fallback(mock_build):
    mock_data_service = MagicMock()
    mock_build.return_value = mock_data_service
    
    mock_channels = MagicMock()
    mock_data_service.channels.return_value = mock_channels
    
    mock_list = MagicMock()
    mock_channels.list.return_value = mock_list
    
    mock_list.execute.return_value = {
        "items": [
            {
                "id": "UC1234567890",
                "statistics": {
                    "viewCount": "100000",
                    "likeCount": "5000",
                }
            }
        ]
    }
    
    connector = YouTubeConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        # No access_token -> should trigger public fallback
        mock_get_creds.return_value = {
            "channel_id": "UC1234567890",
            "api_key": "fake_api_key",
        }
        
        req = DataRequest(
            platform="youtube",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 7),
            metrics=["viewCount", "likeCount"],
            client_id="test_client",
            user_id="test_user",
            account_id="UC1234567890"
        )
        
        results = connector.fetch_data(req)
        assert len(results) == 1
        assert results[0].campaign_name == "YouTube_Channel"
        assert results[0].date == "2026-05-01"
        assert results[0].metrics["viewCount"] == 100000
        assert results[0].metrics["likeCount"] == 5000
        
        mock_build.assert_called_with("youtube", "v3", developerKey="fake_api_key")


# ═══════════════════════════════════════════════════════════════════
# GOOGLE PLAY CONNECTOR TESTS
# ═══════════════════════════════════════════════════════════════════

@patch("app.connectors.google_play.build")
@patch("app.connectors.google_play.GooglePlayConnector._load_credentials")
@patch("app.connectors.google_play.httpx.Client")
def test_google_play_fetch_data_gcs(mock_httpx_client_class, mock_load_creds, mock_build):
    # Setup androidpublisher reviews mock (fallback / basic check)
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_reviews = MagicMock()
    mock_service.reviews.return_value = mock_reviews
    mock_list = MagicMock()
    mock_reviews.list.return_value = mock_list
    mock_list.execute.return_value = {
        "reviews": [{"reviewId": "rev1"}, {"reviewId": "rev2"}]
    }
    
    # Setup credentials mock
    mock_credentials = MagicMock()
    mock_credentials.token = "fake_gcs_access_token"
    mock_load_creds.return_value = mock_credentials
    
    # Setup GCS HTTP Response mocks
    mock_client = MagicMock()
    mock_httpx_client_class.return_value.__enter__.return_value = mock_client
    
    # Installs CSV Overview content (UTF-16 LE encoded)
    installs_csv_headers = "Date,Package Name,Daily Installs,Daily Uninstalls,Active Device Installs\n"
    installs_csv_row1 = "2026-05-01,com.example.app,100,10,90\n"
    installs_csv_row2 = "2026-05-02,com.example.app,150,15,225\n"
    installs_csv_data = installs_csv_headers + installs_csv_row1 + installs_csv_row2
    
    # Ratings CSV Overview content
    ratings_csv_headers = "Date,Package Name,Daily Average Rating,Total Average Rating\n"
    ratings_csv_row1 = "2026-05-01,com.example.app,4.5,4.3\n"
    ratings_csv_row2 = "2026-05-02,com.example.app,4.7,4.4\n"
    ratings_csv_data = ratings_csv_headers + ratings_csv_row1 + ratings_csv_row2
    
    # Return 200 for both installs and ratings
    mock_resp_installs = MagicMock()
    mock_resp_installs.status_code = 200
    mock_resp_installs.content = installs_csv_data.encode("utf-16")
    
    mock_resp_ratings = MagicMock()
    mock_resp_ratings.status_code = 200
    mock_resp_ratings.content = ratings_csv_data.encode("utf-16")
    
    def side_effect(url, headers=None, **kwargs):
        url_str = str(url)
        if "installs" in url_str:
            return mock_resp_installs
        elif "ratings" in url_str:
            return mock_resp_ratings
        raise ValueError(f"Unexpected url: {url_str}")
        
    mock_client.get.side_effect = side_effect
    
    connector = GooglePlayConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "service_account_json": "fake_service_account.json",
            "package_name": "com.example.app",
            "google_play_gcs_bucket": "pubsite_prod_rev_12345"
        }
        
        req = DataRequest(
            platform="google_play",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 2),
            metrics=["installs", "uninstalls", "rating", "reviews_count"],
            client_id="test_client",
            user_id="test_user",
            account_id="com.example.app"
        )
        
        results = connector.fetch_data(req)
        
        # We expect daily CampaignData entries for 2026-05-01 and 2026-05-02
        assert len(results) == 2
        
        assert results[0].campaign_name == "com.example.app"
        assert results[0].date == "2026-05-01"
        assert results[0].metrics["installs"] == 100
        assert results[0].metrics["uninstalls"] == 10
        assert results[0].metrics["rating"] == 4.5
        assert results[0].metrics["reviews_count"] == 2  # Reviews count attached to start date
        
        assert results[1].campaign_name == "com.example.app"
        assert results[1].date == "2026-05-02"
        assert results[1].metrics["installs"] == 150
        assert results[1].metrics["uninstalls"] == 15
        assert results[1].metrics["rating"] == 4.7
        assert "reviews_count" not in results[1].metrics

@patch("app.connectors.google_play.build")
@patch("app.connectors.google_play.GooglePlayConnector._load_credentials")
def test_google_play_fetch_data_reviews_fallback(mock_load_creds, mock_build):
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_reviews = MagicMock()
    mock_service.reviews.return_value = mock_reviews
    mock_list = MagicMock()
    mock_reviews.list.return_value = mock_list
    mock_list.execute.return_value = {
        "reviews": [{"reviewId": "rev1"}, {"reviewId": "rev2"}, {"reviewId": "rev3"}]
    }
    
    mock_load_creds.return_value = MagicMock()
    
    connector = GooglePlayConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        # GCS bucket is empty -> should fallback to only reviews
        mock_get_creds.return_value = {
            "service_account_json": "fake_service_account.json",
            "package_name": "com.example.app",
            "google_play_gcs_bucket": ""
        }
        
        req = DataRequest(
            platform="google_play",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 7),
            metrics=["reviews_count"],
            client_id="test_client",
            user_id="test_user",
            account_id="com.example.app"
        )
        
        results = connector.fetch_data(req)
        
        assert len(results) == 1
        assert results[0].campaign_name == "com.example.app"
        assert results[0].date == "2026-05-01"
        assert results[0].metrics["reviews_count"] == 3
