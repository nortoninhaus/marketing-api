import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.models.benchmarking import (
    BenchmarkingRequest,
    BenchmarkingResponse,
    InstagramCompetitorData,
    FacebookCompetitorData,
)
from app.services.benchmarking import BenchmarkingService


@pytest.fixture
def client():
    return TestClient(app)


def test_benchmarking_models():
    ig_data = InstagramCompetitorData(
        username="parmalatecuador",
        name="Parmalat Ecuador",
        followers=52430,
        follows=120,
        media_count=350,
        posts_count=5,
        reels_count=10,
        total_likes=1500,
        total_comments=300,
        avg_likes=100.0,
        avg_comments=20.0,
        engagement_rate=0.2289,
    )
    assert ig_data.username == "parmalatecuador"
    assert ig_data.followers == 52430
    assert ig_data.reels_count == 10

    fb_data = FacebookCompetitorData(
        page_id_or_username="ParmalatEcuador",
        name="Parmalat Ecuador",
        followers=643720,
        fan_count=643720,
        talking_about_count=1200,
        active_ads_count=12,
    )
    assert fb_data.followers == 643720
    assert fb_data.active_ads_count == 12


def test_benchmarking_service_sorts_by_followers_desc():
    service = BenchmarkingService()

    # Mock analyze methods
    def mock_analyze_ig(client, ig_user_id, username, token, limit_media=25):
        counts = {
            "small_brand": (1000, 50, 10),
            "big_brand": (500000, 2000, 400),
            "mid_brand": (50000, 500, 100),
        }
        f_count, likes, comms = counts.get(username, (0, 0, 0))
        return InstagramCompetitorData(
            username=username,
            name=username.title(),
            followers=f_count,
            total_likes=likes,
            total_comments=comms,
            engagement_rate=1.2,
        )

    def mock_analyze_fb(client, page, token, countries):
        counts = {
            "fb_small": 5000,
            "fb_big": 800000,
            "fb_mid": 120000,
        }
        return FacebookCompetitorData(
            page_id_or_username=page,
            name=page.title(),
            followers=counts.get(page, 0),
            active_ads_count=4,
        )

    with patch.object(service, "get_token", return_value="fake_token"), \
         patch.object(service, "get_connected_ig_user_id", return_value="17841400000000000"), \
         patch.object(service, "analyze_instagram_competitor", side_effect=mock_analyze_ig), \
         patch.object(service, "analyze_facebook_competitor", side_effect=mock_analyze_fb):

        req = BenchmarkingRequest(
            instagram_competitors=["small_brand", "big_brand", "mid_brand"],
            facebook_competitors=["fb_small", "fb_big", "fb_mid"],
        )
        res = service.run_benchmarking(req)

        assert res.status == "success"
        # Must be sorted by followers descending
        assert [x.username for x in res.instagram] == ["big_brand", "mid_brand", "small_brand"]
        assert [x.followers for x in res.instagram] == [500000, 50000, 1000]

        assert [x.page_id_or_username for x in res.facebook] == ["fb_big", "fb_mid", "fb_small"]
        assert [x.followers for x in res.facebook] == [800000, 120000, 5000]

        # Check share of voice
        assert "big_brand" in res.share_of_voice
        assert res.share_of_voice["big_brand"] > res.share_of_voice["small_brand"]


def test_benchmarking_endpoint(client, auth_headers):
    with patch("app.services.benchmarking.benchmarking_service.run_benchmarking") as mock_run:
        mock_run.return_value = BenchmarkingResponse(
            status="success",
            instagram=[
                InstagramCompetitorData(username="brand1", followers=100000),
                InstagramCompetitorData(username="brand2", followers=20000),
            ],
            facebook=[
                FacebookCompetitorData(page_id_or_username="page1", followers=500000),
            ],
            share_of_voice={"brand1": 80.0, "brand2": 20.0},
        )

        response = client.post(
            "/api/v1/benchmarking",
            headers=auth_headers,
            json={
                "instagram_competitors": ["brand2", "brand1"],
                "facebook_competitors": ["page1"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["instagram"]) == 2
        assert data["instagram"][0]["username"] == "brand1"
        assert data["instagram"][0]["followers"] == 100000
        assert data["instagram"][1]["username"] == "brand2"
        assert data["instagram"][1]["followers"] == 20000
