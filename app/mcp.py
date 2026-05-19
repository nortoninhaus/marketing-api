"""
MCP Server Wrapper — Exposes the Marketing API as MCP Tools.
"""

import asyncio
import httpx
from mcp.server.fastmcp import FastMCP
from app.config import settings
from app.models.requests import Platform

# Initialize FastMCP
mcp = FastMCP("Inhaus Marketing API")

# Base URL for the FastAPI app (assuming it runs on 8000)
BASE_URL = "http://localhost:8000"
HEADERS = {"X-API-Key": settings.api_key}

@mcp.tool()
async def list_marketing_platforms():
    """
    Lists all supported marketing platforms and their configuration status.
    Returns: List of platforms with details.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/platforms", headers=HEADERS)
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def get_marketing_data(
    platform: str,
    start_date: str,
    end_date: str,
    metrics: list[str],
    client_id: str,
    user_id: str,
    account_id: str,
    post_id: str = None,
    video_id: str = None,
    app_id: str = None
):
    """
    Fetches campaign data from a specific marketing platform.
    
    Args:
        platform: One of the supported platforms (e.g., 'google_ads', 'meta_ads', 'tiktok_ads').
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        metrics: List of metrics to fetch (e.g., ['clicks', 'impressions', 'spend']).
        client_id: ID of the client/agency.
        user_id: ID of the user making the request.
        account_id: Ad account ID, page ID, or property ID for the platform.
        post_id: Optional specific post/content ID (organic platforms).
        video_id: Optional specific video ID (TikTok/YouTube).
        app_id: Optional app package name or ID (app store platforms).
    """
    payload = {
        "platform": platform,
        "start_date": start_date,
        "end_date": end_date,
        "metrics": metrics,
        "client_id": client_id,
        "user_id": user_id,
        "account_id": account_id,
        "post_id": post_id,
        "video_id": video_id,
        "app_id": app_id
    }
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/campaign-data", 
            json=payload, 
            headers=HEADERS,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def get_batch_marketing_data(requests: list[dict]):
    """
    Fetches marketing data from multiple platforms concurrently.
    
    Args:
        requests: List of data requests, each containing 'platform', 'start_date', 'end_date', 'metrics', 'client_id', 'user_id', and 'account_id'.
    """
    payload = {"requests": requests}
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/batch", 
            json=payload, 
            headers=HEADERS,
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()

if __name__ == "__main__":
    mcp.run()
