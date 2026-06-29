"""
GoHighLevel (GHL) connector — CRM leads and sales analytics.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import requests
import logging

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData
from app.config import settings

logger = logging.getLogger(__name__)


class GhlConnector(BaseConnector):
    platform_name = "ghl"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        """
        Resolve credentials.
        Priority:
        1. Explicit request credentials
        2. Dynamic OAuth credentials resolved from credential store (if client_id is present)
        3. Global settings fallbacks
        """
        creds = {}
        if request and request.credentials:
            creds = request.credentials
        elif request and request.client_id and request.account_id:
            # Attempt to resolve from Firestore
            try:
                from app.services.credential_store import credential_store
                import asyncio
                # resolve_credentials is an async method; we run it synchronously using a loop or helper
                # since fetch_data is synchronous.
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Running in an event loop (e.g. Uvicorn worker thread), use a task/future or run_coroutine_threadsafe
                    import nest_asyncio
                    nest_asyncio.apply()
                resolved = loop.run_until_complete(
                    credential_store.resolve_credentials(
                        client_id=request.client_id,
                        platform=self.platform_name,
                        account_id=request.account_id
                    )
                )
                if resolved:
                    creds = resolved
            except Exception as e:
                logger.warning(f"Failed to resolve GHL credentials from Firestore (non-fatal): {e}")

        # Fallback to settings
        access_token = creds.get("access_token") or settings.ghl_access_token
        location_id = request.account_id if request and request.account_id else (creds.get("location_id") or settings.ghl_location_id)

        return {
            "access_token": access_token,
            "location_id": location_id
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        access_token = creds.get("access_token")
        location_id = creds.get("location_id")

        if not access_token:
            raise ValueError("GHL access token is required.")
        if not location_id:
            raise ValueError("GHL location ID is required.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Version": "2021-07-28",
            "Content-Type": "application/json"
        }

        # Initialize grouping by date
        data_by_date = {}
        curr = request.start_date
        while curr <= request.end_date:
            d_str = curr.strftime("%Y-%m-%d")
            data_by_date[d_str] = {
                "leads_count": 0.0,
                "opportunities_count": 0.0,
                "sales_value": 0.0
            }
            curr += timedelta(days=1)

        # 1. Fetch Contacts (Leads)
        if "lead" in request.metrics:
            try:
                # Paginate and fetch contacts
                contacts = []
                url = "https://services.leadconnectorhq.com/contacts/"
                params = {
                    "locationId": location_id,
                    "limit": 100
                }
                
                page_count = 0
                while url and page_count < 10:
                    response = requests.get(url, headers=headers, params=params if page_count == 0 else None, timeout=30)
                    self._record_rate_limit(response.headers)
                    response.raise_for_status()
                    res_data = response.json()
                    
                    batch_contacts = res_data.get("contacts", [])
                    contacts.extend(batch_contacts)
                    
                    # Check if there is next page
                    meta = res_data.get("meta", {})
                    # Some versions return nextPageUrl or nextPageToken
                    next_page_url = meta.get("nextPageUrl")
                    next_page_token = meta.get("nextPageToken")
                    
                    if next_page_url:
                        url = next_page_url
                    elif next_page_token:
                        url = f"https://services.leadconnectorhq.com/contacts/?locationId={location_id}&limit=100&startAfterId={next_page_token}"
                    else:
                        url = None
                    page_count += 1

                for contact in contacts:
                    date_added_str = contact.get("dateAdded")
                    if date_added_str:
                        # Extract YYYY-MM-DD
                        d_str = date_added_str[:10]
                        if d_str in data_by_date:
                            data_by_date[d_str]["leads_count"] += 1.0
            except Exception as e:
                logger.error(f"Error fetching GHL contacts: {e}")
                # We can either raise or handle error
                raise

        # 2. Fetch Opportunities (Conversions & Purchase/Sales value)
        if any(m in request.metrics for m in ("conversions", "purchase")):
            try:
                # Search opportunities
                opportunities = []
                url = "https://services.leadconnectorhq.com/opportunities/search"
                params = {
                    "locationId": location_id,
                    "limit": 100,
                    "status": "all"
                }

                # GHL Opportunities endpoint
                response = requests.get(url, headers=headers, params=params, timeout=30)
                self._record_rate_limit(response.headers)
                response.raise_for_status()
                res_data = response.json()
                opportunities = res_data.get("opportunities", [])

                for opp in opportunities:
                    # GHL returns won status for successful conversions/sales
                    status = opp.get("status", "").lower()
                    date_added_str = opp.get("createdAt") or opp.get("dateAdded")
                    
                    if date_added_str:
                        d_str = date_added_str[:10]
                        if d_str in data_by_date:
                            # If it's a won opportunity, we treat it as conversion and purchase
                            if status == "won":
                                data_by_date[d_str]["opportunities_count"] += 1.0
                                try:
                                    val = float(opp.get("monetaryValue") or 0.0)
                                    data_by_date[d_str]["sales_value"] += val
                                except Exception:
                                    pass
            except Exception as e:
                logger.error(f"Error fetching GHL opportunities: {e}")
                raise

        # Map to requested CampaignData format
        results = []
        for d_str, day_metrics in data_by_date.items():
            metrics_dict = {}
            for m in request.metrics:
                if m == "lead":
                    metrics_dict["lead"] = day_metrics["leads_count"]
                elif m == "conversions":
                    metrics_dict["conversions"] = day_metrics["opportunities_count"]
                elif m == "purchase":
                    metrics_dict["purchase"] = day_metrics["sales_value"]
                else:
                    metrics_dict[m] = 0.0

            results.append(CampaignData(
                campaign_name="GoHighLevel Location Performance",
                date=d_str,
                metrics=metrics_dict
            ))

        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["lead", "conversions", "purchase"],
            "dimensions": ["date"],
            "metadata": {
                "api_version": "v3"
            }
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            access_token = creds.get("access_token")
            location_id = creds.get("location_id")
            if not access_token or not location_id:
                return False

            url = f"https://services.leadconnectorhq.com/opportunities/search"
            params = {"locationId": location_id, "limit": 1}
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Version": "2021-07-28"
            }
            response = requests.get(url, headers=headers, params=params, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
