import logging
from typing import Dict, Any, List, Optional
import httpx
from app.config import settings
from app.models.benchmarking import (
    BenchmarkingRequest,
    BenchmarkingResponse,
    InstagramCompetitorData,
    FacebookCompetitorData,
)
from app.connectors.meta import MetaOrganicConnector

logger = logging.getLogger(__name__)
GRAPH_API_VERSION = "v25.0"
BASE_GRAPH_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class BenchmarkingService:
    def __init__(self):
        self.organic_connector = MetaOrganicConnector()

    def get_token(self, request: BenchmarkingRequest) -> str:
        if request.access_token:
            return request.access_token
        try:
            from app.models.requests import DataRequest
            mock_req = DataRequest(
                platform="meta_organic",
                client_id=request.client_id or "",
                user_id=request.user_id or "",
                account_id=request.account_id or "",
                metrics=["followers"],
            )
            creds = self.organic_connector.get_credentials(mock_req)
            token = creds.get("access_token")
            if token:
                return token
        except Exception as e:
            logger.warning(f"Could not load credentials from connector: {e}")
        return settings.meta_access_token or ""

    def get_connected_ig_user_id(self, token: str, account_id: Optional[str] = None) -> Optional[str]:
        """Discover the caller's Instagram Business Account ID."""
        if not token:
            return None
        with httpx.Client(timeout=15.0) as client:
            # 1. Try me/accounts to find connected IG account
            try:
                res = client.get(
                    f"{BASE_GRAPH_URL}/me/accounts",
                    params={"fields": "id,name,instagram_business_account{id,username}", "access_token": token},
                )
                if res.status_code == 200:
                    data = res.json()
                    for page in data.get("data", []):
                        ig_acc = page.get("instagram_business_account")
                        if ig_acc and ig_acc.get("id"):
                            return ig_acc["id"]
            except Exception as e:
                logger.warning(f"Error fetching me/accounts for IG discovery: {e}")

            # 2. Try account_id if provided
            if account_id:
                clean_acc = account_id if account_id.startswith("act_") else f"act_{account_id}"
                try:
                    res = client.get(
                        f"{BASE_GRAPH_URL}/{clean_acc}/instagram_accounts",
                        params={"fields": "id,username", "access_token": token},
                    )
                    if res.status_code == 200:
                        data = res.json()
                        items = data.get("data", [])
                        if items and items[0].get("id"):
                            return items[0]["id"]
                except Exception as e:
                    logger.warning(f"Error fetching ad account instagram_accounts: {e}")

        return None

    def analyze_instagram_competitor(
        self, client: httpx.Client, ig_user_id: str, username: str, token: str, limit_media: int = 25
    ) -> InstagramCompetitorData:
        """Fetch competitor profile and recent media via Business Discovery API."""
        clean_user = username.strip().lstrip("@")
        fields = (
            f"business_discovery.username({clean_user}){{"
            f"id,username,name,biography,website,followers_count,follows_count,media_count,profile_picture_url,"
            f"media.limit({limit_media}){{id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count}}"
            f"}}"
        )
        try:
            res = client.get(
                f"{BASE_GRAPH_URL}/{ig_user_id}",
                params={"fields": fields, "access_token": token},
            )
            if res.status_code != 200:
                logger.error(f"IG Business Discovery error for {clean_user}: {res.status_code} {res.text}")
                return InstagramCompetitorData(username=clean_user)

            payload = res.json()
            disc = payload.get("business_discovery", {})
            media_data = disc.get("media", {}).get("data", [])

            followers = disc.get("followers_count", 0)
            posts_count = sum(1 for m in media_data if m.get("media_type") in ("IMAGE", "CAROUSEL_ALBUM"))
            reels_count = sum(1 for m in media_data if m.get("media_type") == "VIDEO")
            total_likes = sum(int(m.get("like_count", 0)) for m in media_data)
            total_comments = sum(int(m.get("comments_count", 0)) for m in media_data)

            count_analyzed = len(media_data)
            avg_likes = round(total_likes / count_analyzed, 2) if count_analyzed > 0 else 0.0
            avg_comments = round(total_comments / count_analyzed, 2) if count_analyzed > 0 else 0.0

            # Engagement Rate: ((total_interactions / posts_analyzed) / followers) * 100
            total_interactions = total_likes + total_comments
            if followers > 0 and count_analyzed > 0:
                engagement_rate = round(((total_interactions / count_analyzed) / followers) * 100, 4)
            else:
                engagement_rate = 0.0

            return InstagramCompetitorData(
                username=disc.get("username", clean_user),
                name=disc.get("name", clean_user),
                id=disc.get("id"),
                followers=followers,
                follows=disc.get("follows_count", 0),
                media_count=disc.get("media_count", 0),
                posts_count=posts_count,
                reels_count=reels_count,
                total_likes=total_likes,
                total_comments=total_comments,
                avg_likes=avg_likes,
                avg_comments=avg_comments,
                engagement_rate=engagement_rate,
                profile_picture_url=disc.get("profile_picture_url"),
                biography=disc.get("biography"),
                website=disc.get("website"),
            )
        except Exception as e:
            logger.error(f"Unexpected error analyzing IG competitor {clean_user}: {e}")
            return InstagramCompetitorData(username=clean_user)

    def analyze_facebook_competitor(
        self, client: httpx.Client, page_id_or_user: str, token: str, countries: List[str]
    ) -> FacebookCompetitorData:
        """Fetch Facebook Page public stats and active ads count from Ad Library."""
        clean_page = page_id_or_user.strip()
        comp = FacebookCompetitorData(page_id_or_username=clean_page)
        # 1. Page Details
        try:
            res = client.get(
                f"{BASE_GRAPH_URL}/{clean_page}",
                params={
                    "fields": "id,name,fan_count,followers_count,talking_about_count,category,verification_status,link",
                    "access_token": token,
                },
            )
            if res.status_code == 200:
                data = res.json()
                comp.id = data.get("id")
                comp.name = data.get("name", clean_page)
                comp.followers = data.get("followers_count", 0) or data.get("fan_count", 0)
                comp.fan_count = data.get("fan_count", 0)
                comp.talking_about_count = data.get("talking_about_count", 0)
                comp.category = data.get("category")
                comp.verification_status = data.get("verification_status")
                comp.link = data.get("link")
        except Exception as e:
            logger.warning(f"Error fetching FB page {clean_page}: {e}")

        # 2. Meta Ad Library Active Ads
        try:
            search_term = comp.name if comp.name else clean_page
            ad_res = client.get(
                f"{BASE_GRAPH_URL}/ads_archive",
                params={
                    "search_terms": search_term,
                    "ad_reached_countries": str(countries),
                    "ad_type": "ALL",
                    "fields": "id",
                    "limit": 50,
                    "access_token": token,
                },
            )
            if ad_res.status_code == 200:
                ad_data = ad_res.json().get("data", [])
                comp.active_ads_count = len(ad_data)
        except Exception as e:
            logger.warning(f"Error fetching FB ads archive for {clean_page}: {e}")

        return comp

    def run_benchmarking(self, request: BenchmarkingRequest) -> BenchmarkingResponse:
        token = self.get_token(request)
        if not token:
            return BenchmarkingResponse(
                status="warning",
                message="Meta access token not configured. Please provide token or connect accounts.",
            )

        ig_user_id = self.get_connected_ig_user_id(token, request.account_id)
        instagram_results: List[InstagramCompetitorData] = []
        facebook_results: List[FacebookCompetitorData] = []

        with httpx.Client(timeout=25.0) as client:
            # Instagram Analysis
            if request.instagram_competitors:
                if ig_user_id:
                    for comp_username in request.instagram_competitors:
                        ig_data = self.analyze_instagram_competitor(
                            client, ig_user_id, comp_username, token, limit_media=request.limit_media
                        )
                        instagram_results.append(ig_data)
                else:
                    logger.warning("Could not resolve an Instagram Business User ID to run Business Discovery.")
                    for comp_username in request.instagram_competitors:
                        instagram_results.append(InstagramCompetitorData(username=comp_username))

            # Facebook Analysis
            if request.facebook_competitors:
                for comp_page in request.facebook_competitors:
                    fb_data = self.analyze_facebook_competitor(
                        client, comp_page, token, countries=request.ad_reached_countries
                    )
                    facebook_results.append(fb_data)

        # Sort by followers descending (MANDATORY per user request)
        instagram_results.sort(key=lambda x: x.followers, reverse=True)
        facebook_results.sort(key=lambda x: x.followers, reverse=True)

        # Compute Share of Voice across Instagram competitors based on interactions (likes + comments)
        share_of_voice: Dict[str, float] = {}
        total_interactions_all = sum(x.total_likes + x.total_comments for x in instagram_results)
        if total_interactions_all > 0:
            for x in instagram_results:
                interactions = x.total_likes + x.total_comments
                share_of_voice[x.username] = round((interactions / total_interactions_all) * 100, 2)

        return BenchmarkingResponse(
            status="success",
            message="Benchmarking data retrieved successfully",
            instagram=instagram_results,
            facebook=facebook_results,
            share_of_voice=share_of_voice,
            metadata={
                "ig_user_id_used": ig_user_id,
                "instagram_count": len(instagram_results),
                "facebook_count": len(facebook_results),
                "sorted_by": "followers_desc",
            },
        )


benchmarking_service = BenchmarkingService()
