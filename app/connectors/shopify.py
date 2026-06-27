"""
Shopify connector — commerce analytics.
"""

from typing import List, Dict, Any, Optional
from datetime import timedelta
import requests
import logging

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData
from app.config import settings

logger = logging.getLogger(__name__)


class ShopifyConnector(BaseConnector):
    platform_name = "shopify"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        access_token = creds.get("access_token") or settings.shopify_access_token
        shop_name = request.account_id if request and request.account_id else (creds.get("shop_name") or settings.shopify_shop_name)
        
        return {
            "access_token": access_token,
            "shop_name": shop_name
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        access_token = creds.get("access_token")
        shop_name = creds.get("shop_name")

        if not access_token:
            raise ValueError("Shopify access token is required.")
        if not shop_name:
            raise ValueError("Shopify shop name is required.")

        shop_domain = shop_name
        if "." not in shop_domain:
            shop_domain = f"{shop_domain}.myshopify.com"

        # Fetch orders via Shopify REST API
        headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
        
        # Shopify REST API uses ISO 8601 offset strings
        created_at_min = request.start_date.strftime("%Y-%m-%dT00:00:00-00:00")
        created_at_max = request.end_date.strftime("%Y-%m-%dT23:59:59-00:00")

        orders = []
        url = f"https://{shop_domain}/admin/api/2024-04/orders.json"
        params = {
            "created_at_min": created_at_min,
            "created_at_max": created_at_max,
            "status": "any",
            "limit": 250
        }

        # Simple pagination loop to fetch all matching orders in the range
        page_count = 0
        while url and page_count < 10:
            if page_count == 0:
                response = requests.get(url, headers=headers, params=params, timeout=30)
            else:
                response = requests.get(url, headers=headers, timeout=30)
                
            self._record_rate_limit(response.headers)
            response.raise_for_status()
            data = response.json()
            orders.extend(data.get("orders", []))
            
            # Parse next link from Shopify pagination header
            link_header = response.headers.get("Link")
            url = None
            if link_header:
                parts = link_header.split(",")
                for part in parts:
                    if 'rel="next"' in part:
                        start = part.find("<") + 1
                        end = part.find(">")
                        if start > 0 and end > start:
                            url = part[start:end]
            page_count += 1

        # Group fetched orders by date
        orders_by_date = {}
        curr = request.start_date
        while curr <= request.end_date:
            d_str = curr.strftime("%Y-%m-%d")
            orders_by_date[d_str] = []
            curr += timedelta(days=1)

        for order in orders:
            created_at = order.get("created_at")
            if created_at:
                d_str = created_at[:10]
                if d_str in orders_by_date:
                    orders_by_date[d_str].append(order)

        results = []
        for d_str, day_orders in orders_by_date.items():
            orders_count = len(day_orders)
            total_sales = sum(float(o.get("total_price" or "0.0") or 0.0) for o in day_orders)
            average_order_value = total_sales / orders_count if orders_count > 0 else 0.0
            
            total_refunds = 0.0
            for o in day_orders:
                for ref in o.get("refunds", []):
                    for t in ref.get("refund_transactions", []):
                        try:
                            total_refunds += float(t.get("amount", 0.0))
                        except Exception:
                            pass

            metrics_dict = {}
            for m in request.metrics:
                if m == "conversions":
                    metrics_dict["conversions"] = float(orders_count)
                elif m in ("sessions", "pageviews", "bounce_rate"):
                    # These metrics require Shopify GraphQL shopifyqlQuery — not yet implemented
                    metrics_dict[m] = None
                elif m == "purchase":
                    metrics_dict["purchase"] = total_sales
                elif m == "total_sales":
                    metrics_dict["total_sales"] = total_sales
                elif m == "orders_count":
                    metrics_dict["orders_count"] = float(orders_count)
                elif m == "average_order_value":
                    metrics_dict["average_order_value"] = average_order_value
                elif m == "total_refunds":
                    metrics_dict["total_refunds"] = total_refunds
                else:
                    metrics_dict[m] = 0.0

            results.append(CampaignData(
                campaign_name="Shopify Store Performance",
                date=d_str,
                metrics=metrics_dict
            ))

        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": [
                "conversions", "purchase", "total_sales", "orders_count",
                "average_order_value", "total_refunds",
                {"name": "sessions", "unavailable_note": "Requires Shopify GraphQL shopifyqlQuery — not yet implemented"},
                {"name": "pageviews", "unavailable_note": "Requires Shopify GraphQL shopifyqlQuery — not yet implemented"},
                {"name": "bounce_rate", "unavailable_note": "Requires Shopify GraphQL shopifyqlQuery — not yet implemented"},
            ],
            "dimensions": ["date"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            shop_domain = creds.get("shop_name") or settings.shopify_shop_name
            access_token = creds.get("access_token") or settings.shopify_access_token
            if not shop_domain or not access_token:
                return False
            if "." not in shop_domain:
                shop_domain = f"{shop_domain}.myshopify.com"
            
            url = f"https://{shop_domain}/admin/api/2024-04/shop.json"
            headers = {"X-Shopify-Access-Token": access_token}
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
