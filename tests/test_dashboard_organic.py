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


def test_clean_post_title():
    from dashboard.views.organic import _clean_post_title

    # Strips raw ID prefixes
    raw1 = "Post_1217240028141214_122121881985395366_Cuando las cosas est"
    assert _clean_post_title(raw1) == "Cuando las cosas est"

    # Handles bare IDs
    raw2 = "Post_1217240028141214_122121881985395366"
    assert _clean_post_title(raw2) == "Publicación"

    # Prefers message content if available
    raw3 = "Post_1217240028141214_122121881985395366_Cuando las cosas est"
    msg = "Cuando las cosas están difíciles, recuerda por qué empezaste tu camino."
    assert _clean_post_title(raw3, message=msg) == msg

    # Handles IG prefixes
    raw_ig = "IG_Post_17841463473447753_998877_Foto playa"
    assert _clean_post_title(raw_ig) == "Foto playa"


def test_process_api_response_preserves_post_image_and_message():
    sample_data = [
        {
            "campaign_name": "Post_1217240028141214_122121881985395366_Test",
            "date": "2026-09-15",
            "metrics": {
                "page_media_view": 344,
                "clicks": 5,
                "page_post_engagements": 2,
            },
            "dimensions": {
                "post_id": "1217240028141214_122121881985395366",
                "permalink": "https://www.facebook.com/1217240028141214/posts/122121881985395366",
                "image_url": "https://scontent.facebook.com/photo.jpg",
                "message": "Cuando las cosas están difíciles",
            }
        }
    ]

    df = process_api_response(sample_data, "meta_organic", "client_1", "user_1")
    assert not df.empty
    row = df.iloc[0]
    assert row["image_url"] == "https://scontent.facebook.com/photo.jpg"
    assert row["message"] == "Cuando las cosas están difíciles"
    assert row["post_id"] == "1217240028141214_122121881985395366"


def test_fetch_meta_post_preview(monkeypatch):
    from unittest.mock import MagicMock
    from dashboard.api import fetch_meta_post_preview
    import dashboard.api as api_mod

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "122121881985395366",
        "message": "Mensaje de prueba",
        "permalink_url": "https://facebook.com/post/123",
        "full_picture": "https://facebook.com/img.jpg"
    }

    monkeypatch.setattr(api_mod, "_meta_proxy_get", lambda *args, **kwargs: mock_resp)

    # Invalidate cache if wrapped
    if hasattr(fetch_meta_post_preview, "clear"):
        fetch_meta_post_preview.clear()

    res = fetch_meta_post_preview("client_1", "1217240028141214", "122121881985395366", "test_key")
    assert res is not None
    assert res["message"] == "Mensaje de prueba"
    assert res["permalink"] == "https://facebook.com/post/123"
    assert res["image_url"] == "https://facebook.com/img.jpg"


def test_fetch_meta_post_preview_og_fallback(monkeypatch):
    from unittest.mock import MagicMock
    from dashboard.api import fetch_meta_post_preview
    import dashboard.api as api_mod
    import requests

    # Mock proxy to fail
    mock_proxy_resp = MagicMock()
    mock_proxy_resp.status_code = 400
    monkeypatch.setattr(api_mod, "_meta_proxy_get", lambda *args, **kwargs: mock_proxy_resp)

    # Mock requests.get for OG scrape
    html_content = '''
    <html>
      <head>
        <meta property="og:image" content="https://lookaside.fbsbx.com/test.jpg" />
        <meta property="og:description" content="Descripción OG de prueba" />
      </head>
    </html>
    '''
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.text = html_content
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_get_resp)

    if hasattr(fetch_meta_post_preview, "clear"):
        fetch_meta_post_preview.clear()

    res = fetch_meta_post_preview(
        "client_1",
        "1217240028141214",
        "122121881985395366",
        "test_key",
        permalink="https://facebook.com/post/123"
    )
    assert res is not None
    assert res["image_url"] == "https://lookaside.fbsbx.com/test.jpg"
    assert res["message"] == "Descripción OG de prueba"


