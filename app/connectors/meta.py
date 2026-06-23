"""
Meta (Facebook/Instagram) connectors — Ads and Organic.
Supports dynamic level (campaign, adset, ad), conversions parsing, pagination,
daily timeseries (time_increment=1), Instagram Organic connectivity,
comments fetching for Ads/Pages/Instagram, and updated metrics (views replaces
deprecated impressions for IG media created after July 2024).
"""

from typing import List, Dict, Any, Optional
import logging
import httpx
from datetime import datetime, time, timezone

from facebook_business.session import FacebookSession
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.page import Page

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData, CommentData
from app.config import settings

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v25.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class MetaAdsConnector(BaseConnector):
    platform_name = "meta_ads"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        access_token = creds.get("access_token") if creds else None
        if not access_token:
            access_token = settings.meta_access_token
            
        ad_account_id = request.account_id if request else creds.get("ad_account_id")
            
        return {
            "access_token": access_token,
            "ad_account_id": ad_account_id
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        session = FacebookSession(
            app_id=settings.meta_app_id,
            app_secret=settings.meta_app_secret,
            access_token=creds["access_token"]
        )
        api = FacebookAdsApi(session)
        account = AdAccount(creds["ad_account_id"], api=api)
        
        # Determine the level from requested dimensions
        level = "campaign"
        if request.dimensions:
            if "ad_name" in request.dimensions or "ad.name" in request.dimensions:
                level = "ad"
            elif "adset_name" in request.dimensions or "adset.name" in request.dimensions:
                level = "adset"

        # Determine fields to request. If conversions is requested, we need to request 'actions'
        fields = []
        has_conversions = False
        for m in request.metrics:
            if m == "conversions":
                has_conversions = True
                if "actions" not in fields:
                    fields.append("actions")
            else:
                fields.append(m)

        # Always include date_start/date_stop to reconstruct date, and name fields for campaign_name mapping
        if "date_start" not in fields:
            fields.append("date_start")
        if level == "ad" and "ad_name" not in fields:
            fields.append("ad_name")
        elif level == "adset" and "adset_name" not in fields:
            fields.append("adset_name")
        elif "campaign_name" not in fields:
            fields.append("campaign_name")

        # Handle breakdown dimensions
        breakdowns = []
        if request.dimensions:
            for dim in request.dimensions:
                if dim in ["age", "gender", "country", "dma", "publisher_platform", "platform_device", "device_platform",
                           "body_asset", "image_asset", "title_asset", "video_asset", "description_asset"]:
                    breakdowns.append(dim)

        params = {
            "time_range": {
                "since": request.start_date.strftime("%Y-%m-%d"),
                "until": request.end_date.strftime("%Y-%m-%d")
            },
            "level": level,
            "time_increment": 1  # Get daily timeseries data
        }
        if breakdowns:
            params["breakdowns"] = breakdowns

        # Handle action attribution windows
        if hasattr(request, "action_attribution_windows") and request.action_attribution_windows:
            params["action_attribution_windows"] = request.action_attribution_windows

        # Handle filters translation to Meta's filtering list
        if hasattr(request, "filters") and request.filters:
            if isinstance(request.filters, list):
                params["filtering"] = request.filters
            elif isinstance(request.filters, dict):
                filtering_list = []
                for field, val in request.filters.items():
                    filtering_list.append({
                        "field": field,
                        "operator": "IN" if isinstance(val, list) else "EQUAL",
                        "value": val if isinstance(val, list) else [val]
                    })
                params["filtering"] = filtering_list

        insights = account.get_insights(
            fields=fields,
            params=params
        )

        results = []
        while insights is not None:
            for i in insights:
                # Map name based on level
                if level == "ad":
                    campaign_name = i.get("ad_name") or i.get("campaign_name") or "Unknown Ad"
                elif level == "adset":
                    campaign_name = i.get("adset_name") or i.get("campaign_name") or "Unknown Adset"
                else:
                    campaign_name = i.get("campaign_name") or "Unknown Campaign"

                # Append breakdown values to campaign_name to differentiate rows
                for b in breakdowns:
                    b_val = i.get(b)
                    if b_val:
                        campaign_name += f"_{b_val}"

                date_val = i.get("date_start") or request.start_date.strftime("%Y-%m-%d")

                metrics_dict = {}
                for m in request.metrics:
                    if m == "conversions":
                        # Parse standard actions array
                        actions = i.get("actions", [])
                        total_conversions = 0
                        for action in actions:
                            try:
                                total_conversions += int(float(action.get("value", 0)))
                            except Exception:
                                pass
                        metrics_dict["conversions"] = total_conversions
                    else:
                        val = i.get(m)
                        if isinstance(val, list):
                            total_val = 0
                            for item in val:
                                try:
                                    total_val += float(item.get("value", 0))
                                except Exception:
                                    pass
                            metrics_dict[m] = total_val
                        elif val is not None:
                            try:
                                # Safely cast metrics to float/int
                                metrics_dict[m] = float(val) if "." in str(val) else int(val)
                            except Exception:
                                metrics_dict[m] = 0
                        else:
                            metrics_dict[m] = 0

                results.append(
                    CampaignData(
                        campaign_name=campaign_name,
                        date=date_val,
                        metrics=metrics_dict
                    )
                )

            try:
                insights = insights.get_next_page()
            except Exception:
                insights = None

        return results

    def fetch_comments(self, post_id: str, access_token: str) -> List[CommentData]:
        """
        Fetch comments on an ad creative's effective post.
        For ads, post_id should be the effective_object_story_id from the ad creative.
        """
        url = f"{GRAPH_BASE}/{post_id}/comments"
        comments: List[CommentData] = []

        with httpx.Client(timeout=30.0) as client:
            params: Dict[str, Any] = {
                "fields": "id,message,from,created_time,comment_count,like_count",
                "limit": 50,
                "access_token": access_token,
            }
            while True:
                res = client.get(url, params=params)
                if res.status_code != 200:
                    logger.error(f"Meta Ads comments error: {res.text}")
                    break

                data = res.json()
                for item in data.get("data", []):
                    from_data = item.get("from", {})
                    comments.append(CommentData(
                        comment_id=item.get("id", ""),
                        text=item.get("message", ""),
                        author=from_data.get("name", ""),
                        timestamp=item.get("created_time", ""),
                        like_count=item.get("like_count", 0),
                        reply_count=item.get("comment_count", 0),
                    ))

                paging = data.get("paging", {})
                next_url = paging.get("next")
                if not next_url:
                    break
                url = next_url
                params = {}

        return comments

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": [
                "impressions", 
                "clicks", 
                "spend", 
                "reach", 
                "conversions",
                "cpc", 
                "cpm", 
                "ctr", 
                "frequency", 
                "actions",
                "purchase_roas",
                "unique_clicks",
                "inline_link_clicks",
                "unique_inline_link_clicks",
                "video_p25_watched_actions",
                "video_p50_watched_actions",
                "video_p75_watched_actions",
                "video_p100_watched_actions",
                "video_play_actions",
                "video_30_sec_watched_actions",
                "video_avg_time_watched_actions",
                "social_spend",
                "cost_per_unique_click",
                "cost_per_inline_link_click",
                "cost_per_conversion",
                "action_values",
                "cost_per_action_type",
                "cost_per_unique_action_type",
                "mobile_app_purchase_roas",
                "website_purchase_roas",
                "website_ctr",
                "outbound_clicks",
                "unique_outbound_clicks",
                "cost_per_outbound_click"
            ],
            "dimensions": ["campaign_name", "adset_name", "ad_name", "date_start",
                          "age", "gender", "country", "dma", "publisher_platform", "platform_device", "device_platform",
                          "body_asset", "image_asset", "title_asset", "video_asset", "description_asset"],
            "metadata": {
                "api_version": GRAPH_API_VERSION,
                "comment_support": True,
            },
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            session = FacebookSession(
                app_id=settings.meta_app_id,
                app_secret=settings.meta_app_secret,
                access_token=creds["access_token"]
            )
            api = FacebookAdsApi(session)
            account = AdAccount(creds["ad_account_id"], api=api)
            account.get_insights(params={"limit": 1})
            return True
        except Exception:
            return False


class MetaOrganicConnector(BaseConnector):
    platform_name = "meta_organic"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        access_token = creds.get("access_token") if creds else None
        if not access_token:
            access_token = settings.meta_access_token
            
        page_id = request.account_id if request else creds.get("page_id")
        is_instagram = creds.get("is_instagram", False) if creds else False
            
        return {
            "access_token": access_token,
            "page_id": page_id,
            "is_instagram": is_instagram
        }

    # Categorization constants for metrics
    IG_ACCOUNT_DAILY_METRICS = {"views", "reach", "profile_views", "follower_count", "accounts_engaged", "total_interactions", "website_clicks"}
    IG_ACCOUNT_DEMO_METRICS = {"audience_gender_age", "audience_country", "audience_city", "audience_locale"}
    IG_MEDIA_METRICS = {"views", "reach", "saved", "shares", "likes", "comments", "total_interactions", "plays", "replays", "carousel_album_saves", "carousel_album_impressions"}

    PAGE_DAILY_METRICS = {"page_views_total", "page_post_engagements", "page_follows", "page_fans", "page_actions_post_reactions_total", "page_media_view", "page_total_media_view_unique"}
    PAGE_DEMO_METRICS = {"page_fans_gender_age", "page_fans_country", "page_fans_city", "page_fans_locale"}
    PAGE_POST_METRICS = {"post_clicks", "post_media_view", "post_total_media_view_unique"}

    # ─── Instagram Organic ─────────────────────────────────────────────

    def _fetch_instagram_data(self, request: DataRequest, creds: Dict[str, Any]) -> List[CampaignData]:
        """Fetch Instagram Organic metrics using raw HTTP Graph API requests.
        Uses 'views' instead of deprecated 'impressions' for IG media/account insights.
        """
        access_token = creds["access_token"]
        ig_account_id = creds["page_id"]  # In Instagram connections, account_id is the IG Business ID
        since_dt = datetime.combine(request.start_date, time.min)
        until_dt = datetime.combine(request.end_date, time.max)
        since_ts = int(since_dt.replace(tzinfo=timezone.utc).timestamp())
        until_ts = int(until_dt.replace(tzinfo=timezone.utc).timestamp())

        daily_data: Dict[str, Dict[str, Any]] = {}
        campaign_name = "Instagram_Organic_Insights"

        # 1. Check if demographic metrics are requested (Lifetime)
        demo_metrics = [m for m in request.metrics if m in self.IG_ACCOUNT_DEMO_METRICS or "audience_" in m]
        if demo_metrics and not request.post_id:
            try:
                demo_url = f"{GRAPH_BASE}/{ig_account_id}/insights"
                with httpx.Client() as client:
                    res = client.get(
                        demo_url,
                        params={
                            "metric": ",".join(demo_metrics),
                            "period": "lifetime",
                            "access_token": access_token
                        }
                    )
                    if res.status_code == 200:
                        insights_data = res.json().get("data", [])
                        day = request.start_date.strftime("%Y-%m-%d")
                        if day not in daily_data:
                            daily_data[day] = {}
                        for item in insights_data:
                            name = item.get("name")
                            values = item.get("values", [])
                            if values:
                                daily_data[day][name] = values[0].get("value", {})
                    else:
                        logger.warning(f"IG Demographics fetch failed: {res.text}")
            except Exception as e:
                logger.warning(f"IG Demographics insights error: {e}")

        # 2. If post_id is "all" or dimension post_id is requested (fetch all media with nested insights in one batch API request)
        if request.post_id == "all" or (not request.post_id and request.dimensions and "post_id" in request.dimensions):
            # Filter for valid Instagram Media metrics
            media_metrics = []
            for m in request.metrics:
                if m in ("views", "impressions"):
                    media_metrics.append("views")
                elif "reach" in m:
                    media_metrics.append("reach")
                elif "save" in m:
                    media_metrics.append("saved")
                elif "engagement" in m or "interaction" in m:
                    media_metrics.append("total_interactions")
                elif "share" in m:
                    media_metrics.append("shares")
                elif "like" in m:
                    media_metrics.append("likes")
                elif "comment" in m:
                    media_metrics.append("comments")
                elif m in self.IG_MEDIA_METRICS:
                    media_metrics.append(m)
            if not media_metrics:
                media_metrics = ["views", "reach", "total_interactions", "saved", "shares", "likes", "comments"]
            media_metrics = list(dict.fromkeys(media_metrics))
            
            url = f"{GRAPH_BASE}/{ig_account_id}/media"
            results = []
            try:
                with httpx.Client() as client:
                    res = client.get(
                        url,
                        params={
                            "fields": f"id,caption,timestamp,media_type,insights.metric({','.join(media_metrics)}){{name,values}}",
                            "limit": request.limit or 50,
                            "access_token": access_token
                        }
                    )
                    if res.status_code == 200:
                        media_list = res.json().get("data", [])
                        for item in media_list:
                            media_id = item.get("id")
                            caption = item.get("caption", "")
                            timestamp = item.get("timestamp", request.start_date.strftime("%Y-%m-%d"))
                            
                            insights_data = item.get("insights", {}).get("data", [])
                            metrics_dict = {}
                            for ins in insights_data:
                                name = ins.get("name")
                                values = ins.get("values", [])
                                if values:
                                    metrics_dict[name] = values[0].get("value", 0)
                            
                            results.append(CampaignData(
                                campaign_name=f"IG_Post_{media_id}_{caption[:20]}",
                                date=timestamp[:10],
                                metrics=metrics_dict
                            ))
                return results
            except Exception as e:
                logger.error(f"IG Media batch fetch error: {e}")
                return []

        # 3. If post_id is provided, fetch insights for specific Instagram Media
        elif request.post_id:
            media_id = request.post_id
            url = f"{GRAPH_BASE}/{media_id}/insights"
            # Map and filter for valid Instagram Media metrics
            media_metrics = []
            for m in request.metrics:
                if m in ("views", "impressions"):
                    media_metrics.append("views")
                elif "reach" in m:
                    media_metrics.append("reach")
                elif "save" in m:
                    media_metrics.append("saved")
                elif "engagement" in m or "interaction" in m:
                    media_metrics.append("total_interactions")
                elif "share" in m:
                    media_metrics.append("shares")
                elif "like" in m:
                    media_metrics.append("likes")
                elif "comment" in m:
                    media_metrics.append("comments")
                elif m in self.IG_MEDIA_METRICS:
                    media_metrics.append(m)
                elif "view" in m or "play" in m:
                    media_metrics.append("views")

            if not media_metrics:
                media_metrics = ["views", "reach", "total_interactions", "saved", "shares", "likes", "comments"]

            media_metrics = list(dict.fromkeys(media_metrics))

            try:
                with httpx.Client() as client:
                    res = client.get(
                        url,
                        params={
                            "metric": ",".join(media_metrics),
                            "access_token": access_token
                        }
                    )
                    if res.status_code == 200:
                        insights_data = res.json().get("data", [])
                        day = request.start_date.strftime("%Y-%m-%d")
                        if day not in daily_data:
                            daily_data[day] = {}
                        for item in insights_data:
                            name = item.get("name")
                            values = item.get("values", [])
                            if values:
                                daily_data[day][name] = values[0].get("value", 0)
                        campaign_name = f"IG_Post_{media_id}"
            except Exception as e:
                logger.error(f"IG Media insights error: {e}")

        # 4. Otherwise, fetch Account/Profile level Insights
        else:
            url = f"{GRAPH_BASE}/{ig_account_id}/insights"
            ig_metrics = []
            for m in request.metrics:
                if m in ("views", "impressions"):
                    ig_metrics.append("views")
                elif "reach" in m:
                    ig_metrics.append("reach")
                elif "profile_views" in m:
                    ig_metrics.append("profile_views")
                elif "follower" in m:
                    ig_metrics.append("follower_count")
                elif "accounts_engaged" in m or "engaged" in m:
                    ig_metrics.append("accounts_engaged")
                elif "total_interactions" in m or "interaction" in m:
                    ig_metrics.append("total_interactions")
                elif "website_clicks" in m:
                    ig_metrics.append("website_clicks")
                elif m in self.IG_ACCOUNT_DAILY_METRICS:
                    ig_metrics.append(m)

            if not ig_metrics:
                ig_metrics = ["views", "reach", "profile_views", "accounts_engaged", "total_interactions"]

            ig_metrics = list(dict.fromkeys(ig_metrics))

            try:
                with httpx.Client() as client:
                    res = client.get(
                        url,
                        params={
                            "metric": ",".join(ig_metrics),
                            "period": "day",
                            "since": since_ts,
                            "until": until_ts,
                            "access_token": access_token
                        }
                    )
                    if res.status_code == 200:
                        insights_data = res.json().get("data", [])
                        for item in insights_data:
                            metric_name = item.get("name")
                            for val_entry in item.get("values", []):
                                end_time = val_entry.get("end_time")
                                day = end_time[:10] if end_time else request.start_date.strftime("%Y-%m-%d")
                                if day not in daily_data:
                                    daily_data[day] = {}
                                daily_data[day][metric_name] = val_entry.get("value", 0)
            except Exception as e:
                logger.error(f"IG Account insights error: {e}")

        if not daily_data:
            return []

        return [
            CampaignData(
                campaign_name=campaign_name,
                date=day,
                metrics=metrics_dict
            ) for day, metrics_dict in sorted(daily_data.items())
        ]

    def _fetch_instagram_comments(self, post_id: str, access_token: str) -> List[CommentData]:
        """Fetch comments on an Instagram media post with nested replies."""
        url = f"{GRAPH_BASE}/{post_id}/comments"
        comments: List[CommentData] = []

        with httpx.Client(timeout=30.0) as client:
            params: Dict[str, Any] = {
                "fields": "id,text,username,timestamp,like_count,replies{id,text,username,timestamp,like_count}",
                "limit": 50,
                "access_token": access_token,
            }
            while True:
                res = client.get(url, params=params)
                if res.status_code != 200:
                    logger.error(f"IG comments error: {res.text}")
                    break

                data = res.json()
                for item in data.get("data", []):
                    # Parse nested replies
                    reply_items = item.get("replies", {}).get("data", [])
                    replies = [
                        CommentData(
                            comment_id=r.get("id", ""),
                            text=r.get("text", ""),
                            author=r.get("username", ""),
                            timestamp=r.get("timestamp", ""),
                            like_count=r.get("like_count", 0),
                        )
                        for r in reply_items
                    ]

                    comments.append(CommentData(
                        comment_id=item.get("id", ""),
                        text=item.get("text", ""),
                        author=item.get("username", ""),
                        timestamp=item.get("timestamp", ""),
                        like_count=item.get("like_count", 0),
                        reply_count=len(replies),
                        replies=replies,
                    ))

                paging = data.get("paging", {})
                next_url = paging.get("next")
                if not next_url:
                    break
                url = next_url
                params = {}

        return comments

    # ─── Facebook Page Comments ────────────────────────────────────────

    def _fetch_page_comments(self, post_id: str, access_token: str) -> List[CommentData]:
        """Fetch comments on a Facebook Page post with nested replies."""
        url = f"{GRAPH_BASE}/{post_id}/comments"
        comments: List[CommentData] = []

        with httpx.Client(timeout=30.0) as client:
            params: Dict[str, Any] = {
                "fields": "id,message,from,created_time,comment_count,like_count",
                "limit": 50,
                "access_token": access_token,
            }
            while True:
                res = client.get(url, params=params)
                if res.status_code != 200:
                    logger.error(f"Page comments error: {res.text}")
                    break

                data = res.json()
                for item in data.get("data", []):
                    from_data = item.get("from", {})
                    comments.append(CommentData(
                        comment_id=item.get("id", ""),
                        text=item.get("message", ""),
                        author=from_data.get("name", ""),
                        timestamp=item.get("created_time", ""),
                        like_count=item.get("like_count", 0),
                        reply_count=item.get("comment_count", 0),
                    ))

                paging = data.get("paging", {})
                next_url = paging.get("next")
                if not next_url:
                    break
                url = next_url
                params = {}

        return comments

    def fetch_comments(self, post_id: str, access_token: str, is_instagram: bool = False) -> List[CommentData]:
        """Unified comment fetching — routes to IG or Page comment method."""
        if is_instagram:
            return self._fetch_instagram_comments(post_id, access_token)
        return self._fetch_page_comments(post_id, access_token)

    # ─── Facebook Page Data ────────────────────────────────────────────

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        if creds.get("is_instagram"):
            return self._fetch_instagram_data(request, creds)

        session = FacebookSession(
            app_id=settings.meta_app_id,
            app_secret=settings.meta_app_secret,
            access_token=creds["access_token"]
        )
        api = FacebookAdsApi(session)
        page = Page(creds["page_id"], api=api)
        
        since_str = request.start_date.strftime("%Y-%m-%d")
        until_str = request.end_date.strftime("%Y-%m-%d")

        results = []
        daily_data: Dict[str, Dict[str, Any]] = {}
        campaign_name = "Page_Insights"

        # 1. Fetch demographics if requested (run safely in try/except)
        demo_metrics = [m for m in request.metrics if m in self.PAGE_DEMO_METRICS or "page_fans_" in m]
        if demo_metrics and not request.post_id:
            try:
                insights = page.get_insights(params={
                    "metric": demo_metrics,
                    "period": "lifetime"
                })
                for insight in insights:
                    metric_name = insight.get("name", "unknown")
                    values_list = insight.get("values", [])
                    for val_entry in values_list:
                        end_time = val_entry.get("end_time", since_str)
                        day = end_time[:10] if end_time else since_str
                        if day not in daily_data:
                            daily_data[day] = {}
                        daily_data[day][metric_name] = val_entry.get("value", {})
            except Exception as e:
                logger.warning(f"Meta Page demographics fetch failed (possibly due to < 100 fans): {e}")

        # 2. If post_id is "all" or dimension post_id is requested (fetch all posts with nested insights in one batch request)
        fetch_posts = False
        if request.post_id == "all" or (not request.post_id and request.dimensions and "post_id" in request.dimensions):
            fetch_posts = True
            # Filter for valid Facebook Post metrics
            post_metrics = [m for m in request.metrics if m in self.PAGE_POST_METRICS]
            if not post_metrics:
                post_metrics = ["post_clicks", "post_media_view", "post_total_media_view_unique"]
            post_metrics = list(dict.fromkeys(post_metrics))
            
            try:
                url = f"{GRAPH_BASE}/{creds['page_id']}/posts"
                with httpx.Client() as client:
                    res = client.get(
                        url,
                        params={
                            "fields": f"id,message,created_time,insights.metric({','.join(post_metrics)}){{name,values}}",
                            "limit": request.limit or 50,
                            "access_token": creds["access_token"]
                        }
                    )
                    if res.status_code == 200:
                        post_list = res.json().get("data", [])
                        for item in post_list:
                            pid = item.get("id")
                            message = item.get("message", "")
                            created_time = item.get("created_time", since_str)
                            
                            insights_data = item.get("insights", {}).get("data", [])
                            metrics_dict = {}
                            for ins in insights_data:
                                name = ins.get("name")
                                values = ins.get("values", [])
                                if values:
                                    metrics_dict[name] = values[0].get("value", 0)
                            
                            results.append(CampaignData(
                                campaign_name=f"Post_{pid}_{message[:20]}",
                                date=created_time[:10],
                                metrics=metrics_dict
                            ))
            except Exception as e:
                logger.error(f"Meta Page posts batch fetch failed: {e}")

        # 3. Fetch specific post if requested
        if request.post_id and request.post_id != "all":
            try:
                posts = page.get_posts(params={"ids": request.post_id})
                if posts:
                    post = posts[0]
                    post_metrics = [m for m in request.metrics if m in self.PAGE_POST_METRICS]
                    if not post_metrics:
                        post_metrics = ["post_clicks", "post_media_view", "post_total_media_view_unique"]
                    post_metrics = list(dict.fromkeys(post_metrics))
                    
                    insights = post.get_insights(params={
                        "metric": post_metrics,
                        "since": since_str,
                        "until": until_str
                    })
                    campaign_name = f"Post_{request.post_id}"
                    for insight in insights:
                        metric_name = insight.get("name", "unknown")
                        values_list = insight.get("values", [])
                        for val_entry in values_list:
                            end_time = val_entry.get("end_time", since_str)
                            day = end_time[:10] if end_time else since_str
                            if day not in daily_data:
                                daily_data[day] = {}
                            daily_data[day][metric_name] = val_entry.get("value", 0)
            except Exception as e:
                logger.error(f"Meta Page post fetch failed: {e}")

        # 4. Fetch Page daily metrics
        if not request.post_id or request.post_id == "all":
            page_metrics = [m for m in request.metrics if m in self.PAGE_DAILY_METRICS]
            if not page_metrics and not fetch_posts:
                page_metrics = ["page_views_total", "page_post_engagements", "page_follows", "page_fans", "page_actions_post_reactions_total"]
            
            if page_metrics:
                page_metrics = list(dict.fromkeys(page_metrics))
                try:
                    insights = page.get_insights(params={
                        "metric": page_metrics,
                        "since": since_str,
                        "until": until_str
                    })
                    for insight in insights:
                        metric_name = insight.get("name", "unknown")
                        values_list = insight.get("values", [])
                        for val_entry in values_list:
                            end_time = val_entry.get("end_time", since_str)
                            day = end_time[:10] if end_time else since_str
                            if day not in daily_data:
                                daily_data[day] = {}
                            daily_data[day][metric_name] = val_entry.get("value", 0)
                except Exception as e:
                    logger.error(f"Meta Page insights fetch failed: {e}")

        if not daily_data:
            return results

        results.extend([
            CampaignData(
                campaign_name=campaign_name,
                date=day,
                metrics=metrics_dict
            ) for day, metrics_dict in sorted(daily_data.items())
        ])
        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": [
                # Facebook Page metrics (migrated from deprecated impressions)
                "page_media_view",
                "page_total_media_view_unique",
                "page_post_engagements",
                "page_views_total",
                "page_follows",
                "page_fans",
                "page_actions_post_reactions_total",
                "post_media_view",
                "post_total_media_view_unique",
                "post_clicks",
                # Instagram Organic metrics (views replaces deprecated impressions)
                "views",
                "reach",
                "accounts_engaged",
                "total_interactions",
                "profile_views",
                "follower_count",
                "website_clicks",
                # IG Media-level metrics
                "saved",
                "shares",
                "likes",
                "comments",
                "plays",
                "replays",
                "carousel_album_saves",
                "carousel_album_impressions",
                "audience_gender_age",
                "audience_country",
                "audience_city",
                "audience_locale",
                "page_fans_gender_age",
                "page_fans_country",
                "page_fans_city",
                "page_fans_locale",
            ],
            "dimensions": ["post_id", "date_start", "audience_gender_age", "audience_country", "audience_city", "audience_locale"],
            "metadata": {
                "api_version": GRAPH_API_VERSION,
                "comment_support": True,
                "notes": "Instagram: 'impressions' deprecated July 2024, use 'views'. "
                         "Pages: 'page_impressions' deprecated June 2026, use 'page_media_view'.",
            },
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            session = FacebookSession(
                app_id=settings.meta_app_id,
                app_secret=settings.meta_app_secret,
                access_token=creds["access_token"]
            )
            api = FacebookAdsApi(session)
            page = Page(creds["page_id"], api=api)
            page.api_get(fields=["name"])
            return True
        except Exception:
            return False
