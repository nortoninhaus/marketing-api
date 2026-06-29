"""
YouTube connector.
Supports private channel timeseries analytics via YouTube Analytics API v2
and falls back to public Data API v3 for cumulative stats if OAuth is not configured.
"""

from typing import List, Dict, Any, Optional
import logging
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData
from app.config import settings

logger = logging.getLogger(__name__)


class YouTubeConnector(BaseConnector):
    platform_name = "youtube"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        access_token = creds.get("access_token") if creds else None
        refresh_token = creds.get("refresh_token") if creds else None
        channel_id = request.account_id if request and request.account_id else (creds.get("channel_id") if creds else None)
        api_key = creds.get("api_key", settings.youtube_api_key) if creds else settings.youtube_api_key
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "channel_id": channel_id,
            "api_key": api_key
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        start_str = request.start_date.strftime("%Y-%m-%d")
        end_str = request.end_date.strftime("%Y-%m-%d")

        # ─── YouTube Analytics API Flow (Requires OAuth) ────────────────
        if creds.get("access_token"):
            token_credentials = Credentials(
                token=creds["access_token"],
                refresh_token=creds.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret
            )
            try:
                youtube_analytics = build("youtubeAnalytics", "v2", credentials=token_credentials)
                channel_id = creds["channel_id"]
                
                # Default/fallback dimension is day
                yt_dims = []
                if request.dimensions:
                    supported_dims = {"day", "country", "deviceType", "operatingSystem", "sharingService", "trafficSourceType", "gender", "ageGroup"}
                    for d in request.dimensions:
                        if d in supported_dims:
                            yt_dims.append(d)
                if not yt_dims:
                    yt_dims = ["day"]

                # Parse and build filters
                filter_parts = []
                if request.video_id:
                    filter_parts.append(f"video=={request.video_id}")
                if request.filters:
                    supported_filters = {"video", "country", "province", "continent", "subContinent", "deviceType", "operatingSystem", "trafficSourceType"}
                    for k, v in request.filters.items():
                        if k in supported_filters:
                            if isinstance(v, list):
                                v_str = ",".join(str(item) for item in v)
                            else:
                                v_str = str(v)
                            filter_parts.append(f"{k}=={v_str}")

                params = {
                    "ids": f"channel=={channel_id}",
                    "startDate": start_str,
                    "endDate": end_str,
                    "metrics": ",".join(request.metrics),
                    "dimensions": ",".join(yt_dims)
                }
                if filter_parts:
                    params["filters"] = ";".join(filter_parts)

                logger.info(f"Querying YouTube Analytics API: {params}")
                response = youtube_analytics.reports().query(**params).execute()
                
                headers = [h["name"] for h in response.get("columnHeaders", [])]
                rows = response.get("rows", [])
                
                results = []
                for row in rows:
                    row_dict = dict(zip(headers, row))
                    date_val = row_dict.get("day", start_str)
                    
                    other_dim_vals = []
                    for d in yt_dims:
                        if d != "day" and d in row_dict:
                            other_dim_vals.append(str(row_dict[d]))
                            
                    if request.video_id:
                        other_dim_vals.append(request.video_id)
                        
                    campaign_name = " | ".join(other_dim_vals) if other_dim_vals else "YouTube_Channel"
                    
                    metrics_dict = {}
                    for m in request.metrics:
                        val = row_dict.get(m, 0)
                        try:
                            metrics_dict[m] = float(val) if "." in str(val) else int(val)
                        except Exception:
                            metrics_dict[m] = 0
                            
                    results.append(CampaignData(
                        campaign_name=campaign_name,
                        date=date_val,
                        metrics=metrics_dict
                    ))
                return results

            except Exception as e:
                logger.error(f"YouTube Analytics API query failed, falling back: {e}")

        # ─── Fallback to Public YouTube Data API v3 ────────────────────
        youtube = build("youtube", "v3", developerKey=creds.get("api_key"))
        if request.video_id:
            yt_request = youtube.videos().list(part="statistics,snippet", id=request.video_id)
            response = yt_request.execute()
            if not response.get("items"):
                return []
            item = response["items"][0]
            
            metrics_dict = {}
            for m in request.metrics:
                val = item["statistics"].get(m, 0)
                metrics_dict[m] = int(val) if str(val).isdigit() else val
                
            return [CampaignData(
                campaign_name=item["snippet"]["title"],
                date=start_str,
                metrics=metrics_dict
            )]
        else:
            channel_id = creds["channel_id"]
            yt_request = youtube.channels().list(part="statistics", id=channel_id)
            response = yt_request.execute()
            if not response.get("items"):
                return []
            item = response["items"][0]
            
            metrics_dict = {}
            for m in request.metrics:
                val = item["statistics"].get(m, 0)
                metrics_dict[m] = int(val) if str(val).isdigit() else val
                
            return [CampaignData(
                campaign_name="YouTube_Channel",
                date=start_str,
                metrics=metrics_dict
            )]

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": [
                "views",
                "likes",
                "comments",
                "shares",
                "watchTimeMinutes",
                "subscribersGained",
                "subscribersLost",
                "averageViewDuration",
                "viewCount",
                "likeCount",
                "commentCount"
            ],
            "dimensions": ["video_id", "title", "date"],
            "metadata": {
                "comment_support": True,
            },
        }

    def fetch_comments(self, video_id: str, api_key_or_token: str, is_oauth: bool = False) -> list:
        """Fetch comment threads on a YouTube video using Data API v3."""
        from app.models.responses import CommentData

        if is_oauth:
            from google.oauth2.credentials import Credentials as OAuthCreds
            token_creds = OAuthCreds(
                token=api_key_or_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
            )
            youtube = build("youtube", "v3", credentials=token_creds)
        else:
            youtube = build("youtube", "v3", developerKey=api_key_or_token)

        comments: list = []
        page_token: Optional[str] = None

        try:
            while True:
                request_params = {
                    "part": "snippet,replies",
                    "videoId": video_id,
                    "maxResults": 50,
                    "textFormat": "plainText",
                    "order": "time",
                }
                if page_token:
                    request_params["pageToken"] = page_token

                response = youtube.commentThreads().list(**request_params).execute()

                for item in response.get("items", []):
                    snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})

                    # Parse replies
                    replies_data = item.get("replies", {}).get("comments", [])
                    reply_list = []
                    for r in replies_data:
                        r_snippet = r.get("snippet", {})
                        reply_list.append(CommentData(
                            comment_id=r.get("id", ""),
                            text=r_snippet.get("textDisplay", ""),
                            author=r_snippet.get("authorDisplayName", ""),
                            timestamp=r_snippet.get("publishedAt", ""),
                            like_count=r_snippet.get("likeCount", 0),
                        ))

                    comments.append(CommentData(
                        comment_id=item.get("id", ""),
                        text=snippet.get("textDisplay", ""),
                        author=snippet.get("authorDisplayName", ""),
                        timestamp=snippet.get("publishedAt", ""),
                        like_count=snippet.get("likeCount", 0),
                        reply_count=item.get("snippet", {}).get("totalReplyCount", 0),
                        replies=reply_list,
                    ))

                page_token = response.get("nextPageToken")
                if not page_token or len(comments) >= 200:
                    break

        except Exception as e:
            logger.error(f"YouTube comments fetch error for video {video_id}: {e}")

        return comments

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            if creds.get("access_token"):
                token_credentials = Credentials(token=creds["access_token"])
                youtube_analytics = build("youtubeAnalytics", "v2", credentials=token_credentials)
                # Just call a minimal metadata/query check
                youtube_analytics.reports().query(
                    ids=f"channel=={creds['channel_id']}",
                    startDate="yesterday",
                    endDate="yesterday",
                    metrics="views"
                ).execute()
                return True
            else:
                youtube = build("youtube", "v3", developerKey=creds.get("api_key"))
                youtube.videoCategories().list(part="snippet", regionCode="US").execute()
                return True
        except Exception:
            return False
