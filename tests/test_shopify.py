"""
Unit tests for Shopify connector.
"""

from unittest.mock import MagicMock, patch
import pytest
from datetime import date
from app.models.requests import DataRequest
from app.connectors.shopify import ShopifyConnector


@patch("app.connectors.shopify.requests.get")
def test_shopify_fetch_data(mock_get):
    # Mock Shopify orders response
    mock_orders_resp = MagicMock()
    mock_orders_resp.status_code = 200
    mock_orders_resp.headers = {
        "x-shopify-shop-api-call-limit": "1/40",
        "Link": ""
    }
    mock_orders_resp.json.return_value = {
        "orders": [
            {
                "id": 111,
                "created_at": "2026-06-01T10:00:00-00:00",
                "total_price": "150.00",
                "refunds": [
                    {
                        "refund_transactions": [
                            {"amount": "10.00"}
                        ]
                    }
                ]
            },
            {
                "id": 222,
                "created_at": "2026-06-01T15:30:00-00:00",
                "total_price": "85.50",
                "refunds": []
            }
        ]
    }

    mock_get.return_value = mock_orders_resp

    connector = ShopifyConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_token": "fake_shopify_token",
            "shop_name": "test-store"
        }

        req = DataRequest(
            platform="shopify",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            metrics=["conversions", "sessions", "pageviews", "bounce_rate", "purchase", "total_sales", "orders_count", "average_order_value", "total_refunds"],
            client_id="test_client",
            user_id="test_user",
            account_id="test-store"
        )

        results = connector.fetch_data(req)
        assert len(results) == 1
        data_row = results[0]
        assert data_row.campaign_name == "Shopify Store Performance"
        assert data_row.date == "2026-06-01"
        assert data_row.metrics["conversions"] == 2.0
        assert data_row.metrics["orders_count"] == 2.0
        assert data_row.metrics["purchase"] == 235.50
        assert data_row.metrics["total_sales"] == 235.50
        assert data_row.metrics["average_order_value"] == 235.50 / 2
        assert data_row.metrics["total_refunds"] == 10.00
        
        # Verify simulated traffic metrics are None (as fake simulation is removed)
        assert data_row.metrics["sessions"] is None
        assert data_row.metrics["pageviews"] is None
        assert data_row.metrics["bounce_rate"] is None

