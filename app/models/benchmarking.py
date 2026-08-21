from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class InstagramCompetitorData(BaseModel):
    username: str
    name: str = ""
    id: Optional[str] = None
    followers: int = 0
    follows: int = 0
    media_count: int = 0
    posts_count: int = 0
    reels_count: int = 0
    total_likes: int = 0
    total_comments: int = 0
    avg_likes: float = 0.0
    avg_comments: float = 0.0
    engagement_rate: float = 0.0
    profile_picture_url: Optional[str] = None
    biography: Optional[str] = None
    website: Optional[str] = None


class FacebookCompetitorData(BaseModel):
    page_id_or_username: str
    name: str = ""
    id: Optional[str] = None
    followers: int = 0
    fan_count: int = 0
    talking_about_count: int = 0
    posts_count: int = 0
    avg_reactions: float = 0.0
    avg_comments: float = 0.0
    avg_shares: float = 0.0
    engagement_rate: float = 0.0
    active_ads_count: int = 0
    category: Optional[str] = None
    verification_status: Optional[str] = None
    link: Optional[str] = None


class BenchmarkingRequest(BaseModel):
    client_id: Optional[str] = Field(default="", description="Client workspace ID")
    user_id: Optional[str] = Field(default="", description="User ID associated with client credentials")
    account_id: Optional[str] = Field(default="", description="Optional Meta ad account ID (e.g. act_1314422010193648)")
    access_token: Optional[str] = Field(default=None, description="Optional override Meta Graph API user/page token")
    instagram_competitors: List[str] = Field(default_factory=list, description="List of competitor Instagram usernames (e.g. ['parmalatecuador', 'toniec'])")
    facebook_competitors: List[str] = Field(default_factory=list, description="List of competitor Facebook page IDs or usernames (e.g. ['parmalatecuador', 'ToniLacteosEc'])")
    ad_reached_countries: List[str] = Field(default_factory=lambda: ["EC"], description="Country codes for Meta Ad Library ad archive search")
    limit_media: int = Field(default=25, description="Number of recent media items to fetch per competitor for engagement analysis")

    model_config = {
        "json_schema_extra": {
            "example": {
                "client_id": "nutri",
                "account_id": "act_1314422010193648",
                "instagram_competitors": ["parmalatecuador", "toniec", "lalecheraec", "vita_ecuador"],
                "facebook_competitors": ["parmalatecuador", "ToniLacteosEc", "LaLecheraEcuador", "VitaEcuador"],
                "ad_reached_countries": ["EC"],
                "limit_media": 25,
            }
        }
    }


class BenchmarkingResponse(BaseModel):
    status: str = Field(default="success", description="Status string: 'success' or 'warning'")
    message: str = Field(default="Benchmarking data retrieved successfully", description="Informative status message")
    instagram: List[InstagramCompetitorData] = Field(default_factory=list, description="Instagram competitor matrix sorted by followers descending")
    facebook: List[FacebookCompetitorData] = Field(default_factory=list, description="Facebook competitor matrix sorted by followers descending")
    share_of_voice: Dict[str, float] = Field(default_factory=dict, description="Share of voice distribution by competitor based on interactions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata and caller IDs")
