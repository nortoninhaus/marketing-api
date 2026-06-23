"""
Tests for SOTA dashboard backend router endpoints.
"""

def test_analyze_video_endpoint(client, auth_headers):
    payload = {"video_url": "https://tiktok.com/@viral_example/video/12345"}
    response = client.post("/api/v1/sota/analyze-video", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "hook" in data
    assert "narrative_arc" in data
    assert "script_prompt" in data

def test_generate_media_endpoint(client, auth_headers):
    payload = {"prompt": "cinematic product photo", "model": "veo_3"}
    response = client.post("/api/v1/sota/generate-media", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "media_url" in data

def test_social_tickets_endpoint(client, auth_headers):
    response = client.get("/api/v1/sota/social-tickets", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "sentiment" in data[0]

def test_listening_alerts_endpoint(client, auth_headers):
    response = client.get("/api/v1/sota/listening-alerts", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "keyword" in data[0]

def test_campaign_proposals_endpoint(client, auth_headers):
    response = client.get("/api/v1/sota/campaign-proposals", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "proposed_budget" in data[0]

def test_confirm_proposal_endpoint(client, auth_headers):
    payload = {"proposal_id": "987", "approved": True}
    response = client.post("/api/v1/sota/confirm-proposal", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "executed"
    assert "detail" in data
