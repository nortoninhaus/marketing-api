"""Search Console OAuth and read-only reporting, with no network or real credentials."""
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, quote, urlsplit

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.config import settings
from app.main import app
from app.models.requests import DataRequest, SearchConsoleQueryRequest
from app.connectors.search_console import SearchConsoleConnector, report_response
from app.routers.oauth import _sign_state, google_oauth_callback, get_authorize_url, SEARCH_CONSOLE_SCOPE, ALL_GOOGLE_SCOPES
from app.services.credential_store import CredentialStore

SITE = "https://www.nutri.com.ec/"
BODY = {"account_id": SITE, "start_date": "2026-08-01", "end_date": "2026-08-31"}
REPORT = {"rows": [{"clicks": 10, "impressions": 100, "ctr": .1, "position": 2}], "responseAggregationType": "byProperty"}


@pytest.mark.parametrize("site", [SITE, "sc-domain:nutri.com.ec"])
def test_property_and_total_body(site):
    query = SearchConsoleQueryRequest(**{**BODY, "account_id": site})
    body = query.upstream_body()
    assert body["dimensions"] == []
    assert body["type"] == "web"
    assert body["dataState"] == "final"
    assert "dimensionFilterGroups" not in body


@pytest.mark.parametrize("change", [
    {"account_id": "https://user:secret@nutri.com.ec/"}, {"account_id": "file:///tmp/token"},
    {"account_id": "https://nutri.com.ec/?q=x"}, {"account_id": "sc-domain:bad/path"},
    {"end_date": "2026-07-31"}, {"row_limit": 25001}, {"row_limit": 0}, {"start_row": -1},
    {"dimensions": ["query", "query"]}, {"dimensions": ["organicGoogleSearchQuery"]},
    {"headers": {"Authorization": "bad"}}, {"path": "https://evil.example/"}, {"query": ""},
])
def test_query_rejects_invalid_input(change):
    with pytest.raises(ValidationError):
        SearchConsoleQueryRequest(**{**BODY, **change})


def test_exact_brand_filter_and_top_ten():
    request = SearchConsoleQueryRequest(**BODY, dimensions=["query"], query="Nutri", row_limit=10, start_row=20)
    body = request.upstream_body()
    assert body["rowLimit"] == 10 and body["startRow"] == 20
    assert body["dimensionFilterGroups"] == [{"filters": [{"dimension": "query", "operator": "equals", "expression": "Nutri"}]}]


@pytest.mark.asyncio
async def test_authorize_dedicated_scope_keeps_other_google_scopes():
    with patch.object(settings, "google_client_id", "test-client"):
        result = await get_authorize_url("search_console", redirect_url="https://dashboard.example/")
    params = parse_qs(urlsplit(result["url"]).query)
    assert params["scope"] == [SEARCH_CONSOLE_SCOPE]
    assert params["access_type"] == ["offline"] and params["prompt"] == ["consent"]
    assert SEARCH_CONSOLE_SCOPE not in ALL_GOOGLE_SCOPES
    assert "analytics.readonly" in ALL_GOOGLE_SCOPES


@pytest.mark.asyncio
async def test_callback_rejects_tampered_state():
    with pytest.raises(HTTPException) as error:
        await google_oauth_callback(code="code", state="tampered")
    assert error.value.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize("site", [SITE, "sc-domain:nutri.com.ec"])
async def test_callback_discovers_only_search_console(site):
    client = AsyncMock()
    client.post.return_value = httpx.Response(200, json={"access_token": "test-access", "expires_in": 3600})
    client.get.return_value = httpx.Response(200, json={"siteEntry": [{"siteUrl": site, "permissionLevel": "siteOwner"}]})
    state = _sign_state({"client_id": "client_1", "platform": "search_console", "redirect_url": "https://dashboard.example/?tab=seo"})
    with patch("app.routers.oauth.httpx.AsyncClient") as factory, patch("app.routers.oauth.credential_store.save_oauth_connection", new_callable=AsyncMock) as save:
        factory.return_value.__aenter__.return_value = client
        response = await google_oauth_callback(code="code", state=state)
    client.get.assert_awaited_once()
    assert client.get.call_args.args[0] == "https://www.googleapis.com/webmasters/v3/sites"
    assert save.await_args.kwargs["platform"] == "search_console"
    assert save.await_args.kwargs["account_id"] == site
    assert save.await_args.kwargs["refresh_token"] is None
    assert "&oauth=success" in response.headers["location"]


@pytest.mark.asyncio
@pytest.mark.parametrize("status,body,expected", [(200, {"siteEntry": []}, 404), (403, {"error": "secret"}, 403), (500, {}, 502)])
async def test_callback_empty_and_error(status, body, expected):
    client = AsyncMock()
    client.post.return_value = httpx.Response(200, json={"access_token": "test"})
    client.get.return_value = httpx.Response(status, json=body)
    state = _sign_state({"platform": "search_console"})
    with patch("app.routers.oauth.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = client
        with pytest.raises(HTTPException) as error:
            await google_oauth_callback(code="code", state=state)
    assert error.value.status_code == expected
    assert "secret" not in error.value.detail


def mock_store():
    store = object.__new__(CredentialStore)
    db = MagicMock()
    db.collection.return_value = db
    db.document.return_value = db
    db.set = AsyncMock()
    db.delete = AsyncMock()
    doc = MagicMock()
    doc.exists = True
    doc.to_dict.return_value = {"access_token": "old", "refresh_token": "keep", "token_expires_at": "2000-01-01T00:00:00+00:00"}
    db.get = AsyncMock(return_value=doc)
    store.db = db
    return store, db, doc


@pytest.mark.asyncio
@pytest.mark.parametrize("site", [SITE, "sc-domain:nutri.com.ec"])
async def test_storage_ids_refresh_and_reconnect_preserves_refresh(site):
    store, db, _ = mock_store()
    await store.save_oauth_connection("client_1", "search_console", site, site, "new")
    assert db.set.await_args.kwargs == {"merge": True}
    assert "refresh_token" not in db.set.await_args.args[0]  # merge leaves existing refresh token intact
    with patch.object(store, "_refresh_google_token", new_callable=AsyncMock, return_value={"access_token": "refreshed"}) as refresh:
        assert (await store.resolve_credentials("client_1", "search_console", site))["access_token"] == "refreshed"
        refresh.assert_awaited_once()
    await store.delete_oauth_connection("client_1", "search_console", site)
    ids = [call.args[0] for call in db.document.call_args_list if call.args[0] != "client_1"]
    assert ids == ["search_console_" + quote(site, safe="")] * 3


@pytest.mark.asyncio
async def test_unconnected_property_has_no_general_credential_fallback():
    store, db, doc = mock_store()
    doc.exists = False
    with patch.object(store, "get_credentials", new_callable=AsyncMock) as fallback:
        assert await store.resolve_credentials("client_1", "search_console", SITE) is None
    fallback.assert_not_called()


@pytest.mark.asyncio
async def test_query_route_total_and_fixed_host():
    upstream = AsyncMock()
    upstream.post.return_value = httpx.Response(200, json=REPORT)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.main.credential_store.resolve_credentials", new_callable=AsyncMock, return_value={"access_token": "test-access"}), patch("httpx.AsyncClient") as factory:
            factory.return_value.__aenter__.return_value = upstream
            response = await client.post("/api/v1/search-console/query", json=BODY, headers={"X-API-Key": settings.api_key})
    assert response.status_code == 200 and response.json() == REPORT
    call = upstream.post.await_args
    assert call.args[0] == "https://www.googleapis.com/webmasters/v3/sites/https%3A%2F%2Fwww.nutri.com.ec%2F/searchAnalytics/query"
    assert call.kwargs["json"]["dimensions"] == []


@pytest.mark.asyncio
async def test_query_auth_and_missing_connection():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post("/api/v1/search-console/query", json=BODY)).status_code in {401, 403}
        with patch("app.main.credential_store.resolve_credentials", new_callable=AsyncMock, return_value=None):
            response = await client.post("/api/v1/search-console/query", json=BODY, headers={"X-API-Key": settings.api_key})
        assert response.status_code == 401


@pytest.mark.parametrize("status,expected", [(400, 400), (401, 401), (403, 403), (429, 429), (500, 502)])
def test_upstream_errors_are_sanitized(status, expected):
    with pytest.raises(HTTPException) as error:
        report_response(httpx.Response(status, json={"error": "secret-upstream-token"}))
    assert error.value.status_code == expected
    assert "secret-upstream-token" not in error.value.detail


def test_connector_does_not_force_date_and_preserves_dimensions():
    req = DataRequest(platform="search_console", user_id="test", client_id="client_1", **BODY,
                      metrics=["clicks", "impressions"], credentials={"access_token": "test"},
                      dimensions=["query"], filters={"query": "nutri"}, limit=10)
    with patch("app.connectors.search_console.httpx.post", return_value=httpx.Response(200, json={"rows": [{"keys": ["nutri"], "clicks": 10, "impressions": 100}]})) as post:
        rows = SearchConsoleConnector().fetch_data(req)
    assert rows[0].dimensions == {"query": "nutri"}
    assert rows[0].metrics == {"clicks": 10, "impressions": 100}
    assert post.call_args.kwargs["json"]["dimensions"] == ["query"]


@pytest.mark.asyncio
async def test_callback_invalid_json_is_sanitized():
    client = AsyncMock()
    client.post.return_value = httpx.Response(200, json={"access_token": "test"})
    client.get.return_value = httpx.Response(200, content=b"not-json-secret")
    with patch("app.routers.oauth.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = client
        with pytest.raises(HTTPException) as error:
            await google_oauth_callback(code="code", state=_sign_state({"platform": "search_console"}))
    assert error.value.status_code == 502
    assert "secret" not in error.value.detail


@pytest.mark.asyncio
async def test_delete_url_property_route_and_storage_failure():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.routers.oauth.credential_store.delete_oauth_connection", new_callable=AsyncMock) as delete:
            response = await client.delete("/api/v1/oauth/connections/search_console/" + quote(SITE, safe=""), headers={"X-API-Key": settings.api_key})
            assert response.status_code == 200
            assert delete.await_args.args == ("client_1", "search_console", SITE)
            delete.side_effect = RuntimeError("secret")
            response = await client.delete("/api/v1/oauth/connections/search_console/" + quote(SITE, safe=""), headers={"X-API-Key": settings.api_key})
            assert response.status_code == 502 and "secret" not in response.text


@pytest.mark.asyncio
async def test_campaign_data_does_not_slice_second_page_twice():
    body = {**BODY, "platform": "search_console", "client_id": "client_1", "user_id": "test",
            "metrics": ["clicks"], "dimensions": ["query"], "limit": 1, "next_page_token": "1"}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.main.credential_store.resolve_credentials", new_callable=AsyncMock, return_value={"access_token": "test"}), patch("app.connectors.search_console.httpx.post", return_value=httpx.Response(200, json={"rows": [{"keys": ["nutri"], "clicks": 10}]})) as post:
            response = await client.post("/api/v1/campaign-data", json=body, headers={"X-API-Key": settings.api_key})
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    assert response.json()["pagination"]["next_page_token"] == "2"
    assert post.call_args.kwargs["json"]["startRow"] == 1
