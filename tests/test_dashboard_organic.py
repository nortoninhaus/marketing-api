import pandas as pd
import pytest

from dashboard.api import process_api_response
from dashboard.utils import extract_metric


def test_extract_metric_supports_dict_reactions():
    metrics = {
        "page_actions_post_reactions_total": {"like": 4, "love": 2}
    }
    extracted = extract_metric(metrics, ["page_actions_post_reactions_total"])
    assert extracted == 6.0


def test_process_api_response_meta_organic_page_insights():
    sample_data = [
        {
            "campaign_name": "Page_Insights",
            "date": "2026-09-02",
            "metrics": {
                "page_media_view": 270,
                "page_total_media_view_unique": 143,
                "page_post_engagements": 7,
                "page_views_total": 35,
                "page_follows": 60,
                "page_actions_post_reactions_total": {
                    "like": 4
                }
            },
            "dimensions": {
                "page_id": "1217240028141214",
                "permalink": "https://www.facebook.com/1217240028141214",
                "url": "https://www.facebook.com/1217240028141214"
            }
        }
    ]

    df = process_api_response(sample_data, "meta_organic", "client_1", "user_1")
    assert not df.empty
    row = df.iloc[0]

    # Standard metrics
    assert row["impressions"] == 270
    assert row["reach"] == 143
    assert row["post_engagement"] == 7
    assert row["pageviews"] == 35
    assert row["followers"] == 60
    assert row["likes"] == 4
    assert row["engagement"] >= 7

    # Explicit organic columns
    assert row["page_media_view"] == 270
    assert row["page_total_media_view_unique"] == 143
    assert row["page_post_engagements"] == 7
    assert row["page_views_total"] == 35
    assert row["page_follows"] == 60

    # Dimensions
    assert row["permalink"] == "https://www.facebook.com/1217240028141214"
    assert row["page_id"] == "1217240028141214"


def test_process_api_response_meta_organic_instagram():
    sample_data = [
        {
            "campaign_name": "Instagram_Organic_Insights",
            "date": "2026-09-02",
            "metrics": {
                "views": 520,
                "reach": 310,
                "total_interactions": 45,
                "profile_views": 80,
                "follower_count": 1200,
                "likes": 30,
                "comments": 10,
                "shares": 5,
            },
            "dimensions": {
                "account_id": "17841463473447753"
            }
        }
    ]

    df = process_api_response(sample_data, "meta_organic", "client_1", "user_1")
    assert not df.empty
    row = df.iloc[0]

    assert row["impressions"] == 520
    assert row["reach"] == 310
    assert row["engagement"] == 45
    assert row["pageviews"] == 80
    assert row["followers"] == 1200
    assert row["likes"] == 30
    assert row["comments"] == 10
    assert row["shares"] == 5


def test_dashboard_routes_organic_view():
    from pathlib import Path
    dashboard_code = Path("dashboard.py").read_text()
    assert "render_organic_platform_tab" in dashboard_code
    assert "from dashboard.views.organic import render_organic_platform_tab" in dashboard_code
