from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Inhaus Marketing Data API",
    description="API unificada para extracción de datos de marketing y apps (Ads + Organic + Analytics)",
    version="5.0.0"
)

# ====================== MODELOS ======================
class DataRequest(BaseModel):
    platform: str = Field(..., description="Plataforma objetivo")
    start_date: str = Field(..., description="Fecha inicio (YYYY-MM-DD)")
    end_date: str = Field(..., description="Fecha fin (YYYY-MM-DD)")
    metrics: List[str] = Field(..., description="Lista de métricas")
    post_id: Optional[str] = None
    video_id: Optional[str] = None
    app_id: Optional[str] = None

class CampaignData(BaseModel):
    campaign_name: str
    date: str
    metrics: dict

class DataResponse(BaseModel):
    status: str
    platform: str
    data: List[CampaignData]

class CommentsResponse(BaseModel):
    status: str
    post_id: str
    total_comments: int
    comments: List[dict]

# ====================== FUNCIONES POR PLATAFORMA ======================

# --- META ---
def fetch_meta_ads_data(start_date, end_date, metrics):
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    
    FacebookAdsApi.init(access_token=os.getenv("META_ACCESS_TOKEN"))
    account = AdAccount(os.getenv("META_AD_ACCOUNT_ID"))
    
    insights = account.get_insights(
        fields=metrics,
        params={"time_range": {"since": start_date, "until": end_date}, "level": "campaign"}
    )
    return [{"campaign_name": i.get("campaign_name"), "date": i.get("date_start"), "metrics": {m: i.get(m) for m in metrics}} for i in insights]

def fetch_meta_organic_data(start_date, end_date, metrics, post_id=None):
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.page import Page
    
    FacebookAdsApi.init(access_token=os.getenv("META_ACCESS_TOKEN"))
    page = Page(os.getenv("META_PAGE_ID"))
    
    if post_id:
        post = page.get_posts(params={"ids": post_id})[0]
        insights = post.get_insights(fields=metrics, params={"since": start_date, "until": end_date})
    else:
        insights = page.get_insights(fields=metrics, params={"since": start_date, "until": end_date})
    
    return [{"campaign_name": f"Post_{post_id}" if post_id else "Page_Insights", "date": start_date, "metrics": {m: i.get(m) for m in metrics}} for i in insights]

# --- GOOGLE ---
def fetch_google_ads_data(start_date, end_date, metrics):
    from google.ads.googleads.client import GoogleAdsClient
    
    client = GoogleAdsClient.load_from_dict({
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
    })
    ga_service = client.get_service("GoogleAdsService")
    query = f"SELECT campaign.name, segments.date, {', '.join(metrics)} FROM campaign WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'"
    response = ga_service.search(customer_id=os.getenv("GOOGLE_ADS_CUSTOMER_ID"), query=query)
    
    return [{"campaign_name": row.campaign.name, "date": row.segments.date, "metrics": {m: getattr(row.metrics, m, 0) for m in metrics}} for row in response]

def fetch_google_analytics_data(start_date, end_date, metrics):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension
    
    client = BetaAnalyticsDataClient()
    request = RunReportRequest(
        property=f"properties/{os.getenv('GA4_PROPERTY_ID')}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        metrics=[Metric(name=m) for m in metrics],
        dimensions=[Dimension(name="date")]
    )
    response = client.run_report(request)
    return [{"campaign_name": "GA4_Report", "date": row.dimension_values[0].value, "metrics": {metrics[i]: row.metric_values[i].value for i in range(len(metrics))}} for row in response.rows]

# --- TIKTOK ---
def fetch_tiktok_ads_data(start_date, end_date, metrics):
    access_token = os.getenv("TIKTOK_ADS_ACCESS_TOKEN")
    advertiser_id = os.getenv("TIKTOK_ADVERTISER_ID")
    url = "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/"
    headers = {"Access-Token": access_token}
    params = {
        "advertiser_id": advertiser_id,
        "report_type": "BASIC",
        "data_level": "AUCTION_CAMPAIGN",
        "dimensions": ["campaign_name", "stat_time_day"],
        "metrics": metrics,
        "start_date": start_date,
        "end_date": end_date,
        "page": 1,
        "page_size": 1000
    }
    response = requests.get(url, headers=headers, params=params).json()
    if response.get("code") != 0:
        raise Exception(f"TikTok Ads Error: {response}")
    return [{"campaign_name": item["dimensions"]["campaign_name"], "date": item["dimensions"]["stat_time_day"], "metrics": {m: item["metrics"].get(m, 0) for m in metrics}} for item in response["data"]["list"]]

def fetch_tiktok_organic_data(start_date, end_date, metrics, video_id=None):
    access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
    if video_id:
        url = f"https://open.tiktokapis.com/v2/video/query/?fields={','.join(metrics)}"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(url, headers=headers, json={"video_ids": [video_id]}).json()
        return [{"campaign_name": f"Video_{video_id}", "date": start_date, "metrics": response.get("data", {}).get("videos", [{}])[0]}]
    else:
        url = "https://open.tiktokapis.com/v2/user/info/"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(url, headers=headers).json()
        return [{"campaign_name": "TikTok_Account", "date": start_date, "metrics": response.get("data", {})}]

# --- LINKEDIN ---
def fetch_linkedin_ads_data(start_date, end_date, metrics):
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    ad_account_id = os.getenv("LINKEDIN_AD_ACCOUNT_ID")
    url = f"https://api.linkedin.com/v2/adAnalytics?q=analytics&dateRange.start.day={start_date}&dateRange.end.day={end_date}&campaign={ad_account_id}"
    headers = {"Authorization": f"Bearer {access_token}", "X-Restli-Protocol-Version": "2.0.0"}
    response = requests.get(url, headers=headers).json()
    return [{"campaign_name": item.get("campaign", "Unknown"), "date": start_date, "metrics": {m: item.get(m, 0) for m in metrics}} for item in response.get("elements", [])]

def fetch_linkedin_organic_data(start_date, end_date, metrics, post_id=None):
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    org_id = os.getenv("LINKEDIN_ORGANIZATION_ID")
    if post_id:
        url = f"https://api.linkedin.com/v2/shares/{post_id}"
    else:
        url = f"https://api.linkedin.com/v2/organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity=urn:li:organization:{org_id}&timeIntervals.timeGranularityType=DAY&timeIntervals.timeRange.start={start_date}&timeIntervals.timeRange.end={end_date}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers).json()
    return [{"campaign_name": f"Post_{post_id}" if post_id else "LinkedIn_Page", "date": start_date, "metrics": response.get("elements", [{}])[0]}]

# --- X (TWITTER) ---
def fetch_x_ads_data(start_date, end_date, metrics):
    access_token = os.getenv("X_ADS_ACCESS_TOKEN")
    account_id = os.getenv("X_ADS_ACCOUNT_ID")
    url = f"https://ads-api.twitter.com/12/stats/accounts/{account_id}/campaigns"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"start_time": start_date, "end_time": end_date, "entity": "CAMPAIGN", "granularity": "DAY"}
    response = requests.get(url, headers=headers, params=params).json()
    return [{"campaign_name": item.get("id", "Unknown"), "date": start_date, "metrics": {m: item.get(m, 0) for m in metrics}} for item in response.get("data", [])]

def fetch_x_organic_data(start_date, end_date, metrics, post_id=None):
    bearer_token = os.getenv("X_BEARER_TOKEN")
    if post_id:
        url = f"https://api.twitter.com/2/tweets/{post_id}?tweet.fields=public_metrics,created_at"
    else:
        url = "https://api.twitter.com/2/users/me"
    headers = {"Authorization": f"Bearer {bearer_token}"}
    response = requests.get(url, headers=headers).json()
    return [{"campaign_name": f"Tweet_{post_id}" if post_id else "X_Account", "date": start_date, "metrics": response.get("data", {})}]

# --- YOUTUBE ---
def fetch_youtube_data(start_date, end_date, metrics, video_id=None):
    from googleapiclient.discovery import build
    youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))
    
    if video_id:
        request = youtube.videos().list(part="statistics,snippet", id=video_id)
        response = request.execute()
        return [{"campaign_name": response["items"][0]["snippet"]["title"], "date": start_date, "metrics": response["items"][0]["statistics"]}]
    else:
        request = youtube.channels().list(part="statistics", mine=True)
        response = request.execute()
        return [{"campaign_name": "YouTube_Channel", "date": start_date, "metrics": response["items"][0]["statistics"]}]

# --- GOOGLE PLAY ---
def fetch_google_play_data(start_date, end_date, metrics, app_id=None):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    
    credentials = service_account.Credentials.from_service_account_file(os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON"))
    service = build("androidpublisher", "v3", credentials=credentials)
    reviews = service.reviews().list(packageName=app_id or os.getenv("GOOGLE_PLAY_PACKAGE_NAME")).execute()
    return [{"campaign_name": "Google Play", "date": start_date, "metrics": {"reviews_count": len(reviews.get("reviews", []))}}]

# --- APPLE APP STORE ---
def fetch_apple_app_store_data(start_date, end_date, metrics, app_id=None):
    import jwt, time
    key_id = os.getenv("APPLE_KEY_ID")
    issuer_id = os.getenv("APPLE_ISSUER_ID")
    private_key = os.getenv("APPLE_PRIVATE_KEY")
    
    token = jwt.encode(
        {"iss": issuer_id, "iat": int(time.time()), "exp": int(time.time()) + 1200, "aud": "appstoreconnect-v1"},
        private_key, algorithm="ES256", headers={"kid": key_id}
    )
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.appstoreconnect.apple.com/v1/apps/{app_id or os.getenv('APPLE_APP_ID')}/appStoreVersions"
    response = requests.get(url, headers=headers).json()
    return [{"campaign_name": "Apple App Store", "date": start_date, "metrics": {"versions": len(response.get("data", []))}}]

# --- APPLE ADS ---
def fetch_apple_ads_data(start_date, end_date, metrics):
    access_token = os.getenv("APPLE_ADS_ACCESS_TOKEN")
    org_id = os.getenv("APPLE_ADS_ORG_ID")
    url = "https://api.searchads.apple.com/api/v4/reports/campaigns"
    headers = {"Authorization": f"Bearer {access_token}", "X-AP-Context": org_id}
    params = {"startTime": start_date, "endTime": end_date, "granularity": "DAILY"}
    response = requests.get(url, headers=headers, params=params).json()
    return [{"campaign_name": item.get("campaignName", "Unknown"), "date": start_date, "metrics": item.get("metrics", {})} for item in response.get("data", [])]

# ====================== ENDPOINTS ======================
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "5.0.0"}

@app.post("/api/v1/campaign-data", response_model=DataResponse)
async def get_campaign_data(request: DataRequest):
    platform = request.platform.lower().replace(" ", "")
    logger.info(f"Request received for platform: {request.platform}")

    try:
        if "metaads" in platform:
            data = fetch_meta_ads_data(request.start_date, request.end_date, request.metrics)
        elif "metaorganic" in platform:
            data = fetch_meta_organic_data(request.start_date, request.end_date, request.metrics, request.post_id)
        elif "googleads" in platform:
            data = fetch_google_ads_data(request.start_date, request.end_date, request.metrics)
        elif "googleanalytics" in platform or "ga4" in platform:
            data = fetch_google_analytics_data(request.start_date, request.end_date, request.metrics)
        elif "tiktokads" in platform:
            data = fetch_tiktok_ads_data(request.start_date, request.end_date, request.metrics)
        elif "tiktokorganic" in platform:
            data = fetch_tiktok_organic_data(request.start_date, request.end_date, request.metrics, request.video_id)
        elif "linkedinads" in platform:
            data = fetch_linkedin_ads_data(request.start_date, request.end_date, request.metrics)
        elif "linkedinorganic" in platform:
            data = fetch_linkedin_organic_data(request.start_date, request.end_date, request.metrics, request.post_id)
        elif "xads" in platform or "twitterads" in platform:
            data = fetch_x_ads_data(request.start_date, request.end_date, request.metrics)
        elif "xorganic" in platform or "twitterorganic" in platform:
            data = fetch_x_organic_data(request.start_date, request.end_date, request.metrics, request.post_id)
        elif "youtube" in platform:
            data = fetch_youtube_data(request.start_date, request.end_date, request.metrics, request.video_id)
        elif "googleplay" in platform:
            data = fetch_google_play_data(request.start_date, request.end_date, request.metrics, request.app_id)
        elif "appleappstore" in platform or "appstore" in platform:
            data = fetch_apple_app_store_data(request.start_date, request.end_date, request.metrics, request.app_id)
        elif "appleads" in platform:
            data = fetch_apple_ads_data(request.start_date, request.end_date, request.metrics)
        else:
            raise HTTPException(status_code=400, detail="Plataforma no soportada")

        return DataResponse(status="success", platform=request.platform, data=data)

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("connector_api:app", host="0.0.0.0", port=8000, reload=True)