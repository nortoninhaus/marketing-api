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
                
                # Default channel filter query format is channel==CHANNEL_ID
                params = {
                    "ids": f"channel=={channel_id}",
                    "startDate": start_str,
                    "endDate": end_str,
                    "metrics": ",".join(request.metrics),
                    "dimensions": "day"
                }
                
                if request.video_id:
                    params["filters"] = f"video=={request.video_id}"

                logger.info(f"Querying YouTube Analytics API: {params}")
                response = youtube_analytics.reports().query(**params).execute()
                
                headers = [h["name"] for h in response.get("columnHeaders", [])]
                rows = response.get("rows", [])
                
                results = []
                for row in rows:
                    row_dict = dict(zip(headers, row))
                    date_val = row_dict.get("day", start_str)
                    
                    metrics_dict = {}
                    for m in request.metrics:
                        val = row_dict.get(m, 0)
                        try:
                            metrics_dict[m] = float(val) if "." in str(val) else int(val)
                        except Exception:
                            metrics_dict[m] = 0
                            
                    campaign_name = f"YT_Video_{request.video_id}" if request.video_id else "YouTube_Channel"
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
            "dimensions": ["video_id", "title", "date"]
        }

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
