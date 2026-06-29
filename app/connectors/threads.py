"""
Threads connector — Insights, media metrics, and comments via the Threads API.

Endpoints used:
  - GET /v1.0/{user-id}/threads            — list user's Threads posts
  - GET /v1.0/{media-id}/insights          — per-post engagement metrics
  - GET /v1.0/{user-id}/threads_insights   — account-level aggregate metrics
  - GET /v1.0/{media-id}/replies           — replies on a specific Thread
"""

from typing import List, Dict, Any, Optional
import logging
import httpx
from datetime import datetime, time, timezone

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData, CommentData
from app.config import settings

logger = logging.getLogger(__name__)

THREADS_GRAPH_BASE = "https://graph.threads.net/v1.0"

# Metrics available at the media level
MEDIA_METRICS = ["views", "likes", "replies", "reposts", "quotes", "shares"]

# Metrics available at the user/account level
USER_METRICS = ["views", "likes", "replies", "reposts", "quotes", "followers_count"]


class ThreadsConnector(BaseConnector):
    platform_name = "threads"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)

        access_token = creds.get("access_token") if creds else None
        if not access_token:
            access_token = settings.threads_access_token

        threads_user_id = request.account_id if request else creds.get("threads_user_id", "me")

        return {
            "access_token": access_token,
            "threads_user_id": threads_user_id,
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        access_token = creds["access_token"]
        user_id = creds["threads_user_id"]

        since_dt = datetime.combine(request.start_date, time.min)
        until_dt = datetime.combine(request.end_date, time.max)
        since_ts = int(since_dt.replace(tzinfo=timezone.utc).timestamp())
        until_ts = int(until_dt.replace(tzinfo=timezone.utc).timestamp())

        # Determine which metrics the caller wants
        requested_media_metrics = [m for m in request.metrics if m in MEDIA_METRICS]
        requested_user_metrics = [m for m in request.metrics if m in USER_METRICS]

        # Determine if they want media (post) level insights:
        # 1. They provided request.post_id
        # 2. Dimensions contains "post_id" or "post.id"
        # 3. They request shares (exclusive to media metrics)
        # 4. Otherwise, if requested_user_metrics is present, default to user insights unless they specifically want media.
        is_post_level = False
        if request.post_id:
            is_post_level = True
        elif request.dimensions and ("post_id" in request.dimensions or "post.id" in request.dimensions):
            is_post_level = True
        elif "shares" in request.metrics:
            is_post_level = True
        elif "followers_count" in request.metrics:
            is_post_level = False
        elif requested_user_metrics and not requested_media_metrics:
            is_post_level = False
        elif requested_media_metrics and not requested_user_metrics:
            is_post_level = True

        if not is_post_level and requested_user_metrics:
            return self._fetch_user_insights(
                access_token, user_id, requested_user_metrics,
                since_ts, until_ts, request
            )

        # Otherwise fetch per-post media insights
        return self._fetch_media_insights(
            access_token, user_id, requested_media_metrics or MEDIA_METRICS,
            since_ts, until_ts, request
        )

    def _fetch_user_insights(
        self, access_token: str, user_id: str,
        metrics: List[str], since_ts: int, until_ts: int,
        request: DataRequest
    ) -> List[CampaignData]:
        """Fetch account-level aggregate Threads insights."""
        url = f"{THREADS_GRAPH_BASE}/{user_id}/threads_insights"
        results: List[CampaignData] = []
        daily_data: Dict[str, Dict[str, Any]] = {}

        with httpx.Client(timeout=30.0) as client:
            res = client.get(url, params={
                "metric": ",".join(metrics),
                "since": since_ts,
                "until": until_ts,
                "access_token": access_token,
            })
            self._record_rate_limit(dict(res.headers))
            if res.status_code != 200:
                logger.error(f"Threads user insights error: {res.text}")
                return []

            for item in res.json().get("data", []):
                metric_name = item.get("name")
                for val_entry in item.get("values", []):
                    end_time = val_entry.get("end_time", "")
                    day = end_time[:10] if end_time else request.start_date.strftime("%Y-%m-%d")
                    if day not in daily_data:
                        daily_data[day] = {}
                    daily_data[day][metric_name] = val_entry.get("value", 0)

        for day, metrics_dict in sorted(daily_data.items()):
            results.append(CampaignData(
                campaign_name="Threads_Account_Insights",
                date=day,
                metrics=metrics_dict,
            ))

        return results

    def _fetch_media_insights(
        self, access_token: str, user_id: str,
        metrics: List[str], since_ts: int, until_ts: int,
        request: DataRequest
    ) -> List[CampaignData]:
        """Fetch per-post media insights for each Thread."""
        results: List[CampaignData] = []

        with httpx.Client(timeout=30.0) as client:
            # If a specific post_id is provided, query only that media
            if request.post_id:
                media_ids = [request.post_id]
            else:
                # List user's Threads posts
                list_url = f"{THREADS_GRAPH_BASE}/{user_id}/threads"
                list_res = client.get(list_url, params={
                    "fields": "id,text,timestamp",
                    "since": since_ts,
                    "until": until_ts,
                    "limit": 100,
                    "access_token": access_token,
                })
                self._record_rate_limit(dict(list_res.headers))
                if list_res.status_code != 200:
                    logger.error(f"Threads media list error: {list_res.text}")
                    return []
                media_ids = [m["id"] for m in list_res.json().get("data", [])]

            # Fetch insights for each media
            for media_id in media_ids:
                insights_url = f"{THREADS_GRAPH_BASE}/{media_id}/insights"
                ins_res = client.get(insights_url, params={
                    "metric": ",".join(metrics),
                    "access_token": access_token,
                })
                self._record_rate_limit(dict(ins_res.headers))
                if ins_res.status_code != 200:
                    logger.warning(f"Threads media insights error for {media_id}: {ins_res.text}")
                    continue

                metrics_dict: Dict[str, Any] = {}
                for item in ins_res.json().get("data", []):
                    name = item.get("name")
                    values = item.get("values", [])
                    if values:
                        metrics_dict[name] = values[0].get("value", 0)

                results.append(CampaignData(
                    campaign_name=f"Thread_{media_id}",
                    date=request.start_date.strftime("%Y-%m-%d"),
                    metrics=metrics_dict,
                ))

        return results

    def fetch_comments(self, post_id: str, access_token: str) -> List[CommentData]:
        """Fetch replies (comments) on a specific Thread post."""
        url = f"{THREADS_GRAPH_BASE}/{post_id}/replies"
        comments: List[CommentData] = []

        with httpx.Client(timeout=30.0) as client:
            params: Dict[str, Any] = {
                "fields": "id,text,username,timestamp",
                "limit": 50,
                "access_token": access_token,
            }
            while True:
                res = client.get(url, params=params)
                if res.status_code != 200:
                    logger.error(f"Threads replies error: {res.text}")
                    break

                data = res.json()
                for item in data.get("data", []):
                    comments.append(CommentData(
                        comment_id=item.get("id", ""),
                        text=item.get("text", ""),
                        author=item.get("username", ""),
                        timestamp=item.get("timestamp", ""),
                    ))

                # Cursor-based pagination
                paging = data.get("paging", {})
                next_url = paging.get("next")
                if not next_url:
                    break
                url = next_url
                params = {}  # next URL already contains params

        return comments

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": [
                {"name": "views", "description": "Number of times the Thread was viewed"},
                {"name": "likes", "description": "Total likes"},
                {"name": "replies", "description": "Total replies"},
                {"name": "reposts", "description": "Number of reposts"},
                {"name": "quotes", "description": "Number of quote posts"},
                {"name": "shares", "description": "Number of direct shares"},
                {"name": "followers_count", "description": "Total follower count (user-level)"},
            ],
            "dimensions": ["post_id", "date"],
            "metadata": {
                "api_version": "v1.0",
                "platform": "Threads",
                "comment_support": True,
            },
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            with httpx.Client(timeout=10.0) as client:
                res = client.get(
                    f"{THREADS_GRAPH_BASE}/me",
                    params={
                        "fields": "id",
                        "access_token": creds["access_token"],
                    },
                )
                return res.status_code == 200
        except Exception:
            return False
