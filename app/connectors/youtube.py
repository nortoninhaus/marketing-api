"""
YouTube connector.
"""

from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData
from app.config import settings

class YouTubeConnector(BaseConnector):
    platform_name = "youtube"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        api_key = creds.get("api_key", settings.youtube_api_key)
        
        return {
            "api_key": api_key
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        youtube = build("youtube", "v3", developerKey=creds.get("api_key"))
        start_str = request.start_date.strftime("%Y-%m-%d")
        if request.video_id:
            yt_request = youtube.videos().list(part="statistics,snippet", id=request.video_id)
            response = yt_request.execute()
            if not response.get("items"):
                return []
            item = response["items"][0]
            return [CampaignData(
                campaign_name=item["snippet"]["title"],
                date=start_str,
                metrics=item["statistics"]
            )]
        else:
            channel_id = request.account_id
            yt_request = youtube.channels().list(part="statistics", id=channel_id)
            response = yt_request.execute()
            if not response.get("items"):
                return []
            item = response["items"][0]
            return [CampaignData(
                campaign_name="YouTube_Channel",
                date=start_str,
                metrics=item["statistics"]
            )]

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["viewCount", "likeCount", "commentCount"],
            "dimensions": ["video_id", "title"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            youtube = build("youtube", "v3", developerKey=creds.get("api_key"))
            youtube.videoCategories().list(part="snippet", regionCode="US").execute()
            return True
        except Exception:
            return False
