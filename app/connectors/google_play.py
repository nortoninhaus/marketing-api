"""
Google Play connector.
"""

import csv
import io
import json
import logging
import os
import urllib.parse
from datetime import datetime, date
from typing import List, Dict, Any, Optional

import httpx
from google.auth.transport.requests import Request as AuthRequest
from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData
from app.config import settings

logger = logging.getLogger(__name__)

class GooglePlayConnector(BaseConnector):
    platform_name = "google_play"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        service_account_json = creds.get("service_account_json", settings.google_play_service_account_json)
        package_name = request.account_id if request and request.account_id else creds.get("package_name")
        gcs_bucket = creds.get("google_play_gcs_bucket", settings.google_play_gcs_bucket)
        
        return {
            "service_account_json": service_account_json,
            "package_name": package_name,
            "google_play_gcs_bucket": gcs_bucket
        }

    def _load_credentials(self, service_account_val: str, scopes: List[str]) -> service_account.Credentials:
        if not service_account_val:
            raise ValueError("Service account JSON string or file path is empty.")
        
        # Check if it is a file path
        if os.path.exists(service_account_val):
            return service_account.Credentials.from_service_account_file(
                service_account_val,
                scopes=scopes
            )
        
        # Try to parse as inline JSON
        try:
            info = json.loads(service_account_val)
            return service_account.Credentials.from_service_account_info(
                info,
                scopes=scopes
            )
        except json.JSONDecodeError:
            raise FileNotFoundError(
                f"Service account file not found and is not valid JSON: {service_account_val}"
            )

    def _get_months_in_range(self, start_date: date, end_date: date) -> List[str]:
        months = []
        current = start_date.replace(day=1)
        while current <= end_date:
            months.append(current.strftime("%Y%m"))
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        return months

    def _decode_content(self, content: bytes) -> str:
        if content.startswith(b'\xff\xfe') or content.startswith(b'\xfe\xff'):
            try:
                return content.decode("utf-16")
            except Exception:
                pass
        for encoding in ("utf-16", "utf-16-le", "utf-8", "latin-1"):
            try:
                return content.decode(encoding)
            except Exception:
                continue
        return content.decode("utf-8", errors="ignore")

    def _parse_play_csv(self, csv_text: str) -> List[Dict[str, str]]:
        if csv_text.startswith('\ufeff'):
            csv_text = csv_text.lstrip('\ufeff')
            
        lines = csv_text.splitlines()
        if not lines:
            return []
            
        reader = csv.reader(lines)
        headers = next(reader, None)
        if not headers:
            return []
            
        normalized_headers = []
        for h in headers:
            norm = h.strip().lower().replace("_", " ").replace("  ", " ")
            normalized_headers.append(norm)
            
        results = []
        for row in reader:
            if not row:
                continue
            if len(row) < len(normalized_headers):
                row = row + [""] * (len(normalized_headers) - len(row))
            results.append(dict(zip(normalized_headers, row)))
        return results

    def _extract_date(self, row: Dict[str, str]) -> Optional[date]:
        date_str = row.get("date")
        if not date_str:
            return None
        date_str = date_str.strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

    def _extract_numeric_metric(self, row: Dict[str, str], aliases: List[str]) -> Optional[int]:
        for alias in aliases:
            if alias in row:
                val_str = row[alias].strip()
                if not val_str:
                    continue
                try:
                    val_str = val_str.replace(",", "")
                    return int(val_str)
                except ValueError:
                    try:
                        return int(float(val_str))
                    except ValueError:
                        continue
        return None

    def _extract_float_metric(self, row: Dict[str, str], aliases: List[str]) -> Optional[float]:
        for alias in aliases:
            if alias in row:
                val_str = row[alias].strip()
                if not val_str:
                    continue
                try:
                    val_str = val_str.replace(",", "")
                    return float(val_str)
                except ValueError:
                    continue
        return None

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        package_name = creds["package_name"]
        bucket = creds.get("google_play_gcs_bucket")
        
        # 1. Fetch reviews from Android Publisher API as standard
        reviews_count = 0
        try:
            android_creds = self._load_credentials(
                creds["service_account_json"],
                scopes=["https://www.googleapis.com/auth/androidpublisher"]
            )
            service = build("androidpublisher", "v3", credentials=android_creds)
            reviews = service.reviews().list(packageName=package_name).execute()
            reviews_count = len(reviews.get("reviews", []))
        except Exception as e:
            logger.warning(f"Failed to fetch reviews from Android Publisher API: {e}")

        # 2. Fetch installs and ratings from GCS if bucket is configured
        daily_data = {}
        if bucket:
            try:
                scopes = ["https://www.googleapis.com/auth/devstorage.read_only"]
                gcs_creds = self._load_credentials(creds["service_account_json"], scopes=scopes)
                gcs_creds.refresh(AuthRequest())
                access_token = gcs_creds.token
                
                months = self._get_months_in_range(request.start_date, request.end_date)
                
                with httpx.Client() as client:
                    for yyyyMM in months:
                        # Fetch installs report
                        installs_obj = f"stats/installs/installs_{package_name}_{yyyyMM}_overview.csv"
                        quoted_installs = urllib.parse.quote(installs_obj, safe='')
                        installs_url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{quoted_installs}?alt=media"
                        
                        try:
                            resp = client.get(installs_url, headers={"Authorization": f"Bearer {access_token}"})
                            if resp.status_code == 200:
                                csv_text = self._decode_content(resp.content)
                                rows = self._parse_play_csv(csv_text)
                                for row in rows:
                                    date_val = self._extract_date(row)
                                    if date_val and request.start_date <= date_val <= request.end_date:
                                        date_str = date_val.strftime("%Y-%m-%d")
                                        installs_metric = self._extract_numeric_metric(row, ["daily installs", "installs", "install events"])
                                        uninstalls_metric = self._extract_numeric_metric(row, ["daily uninstalls", "uninstalls", "uninstall events"])
                                        
                                        if date_str not in daily_data:
                                            daily_data[date_str] = {}
                                        if installs_metric is not None:
                                            daily_data[date_str]["installs"] = daily_data[date_str].get("installs", 0) + installs_metric
                                        if uninstalls_metric is not None:
                                            daily_data[date_str]["uninstalls"] = daily_data[date_str].get("uninstalls", 0) + uninstalls_metric
                            elif resp.status_code == 404:
                                logger.info(f"Installs overview report not found for {yyyyMM} (GCS 404)")
                            else:
                                logger.warning(f"Failed to fetch installs report for {yyyyMM}: GCS returned {resp.status_code}")
                        except Exception as e:
                            logger.error(f"Error fetching/parsing installs report for {yyyyMM}: {e}")
                            
                        # Fetch ratings report
                        ratings_obj = f"stats/ratings/ratings_{package_name}_{yyyyMM}_overview.csv"
                        quoted_ratings = urllib.parse.quote(ratings_obj, safe='')
                        ratings_url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{quoted_ratings}?alt=media"
                        
                        try:
                            resp = client.get(ratings_url, headers={"Authorization": f"Bearer {access_token}"})
                            if resp.status_code == 200:
                                csv_text = self._decode_content(resp.content)
                                rows = self._parse_play_csv(csv_text)
                                for row in rows:
                                    date_val = self._extract_date(row)
                                    if date_val and request.start_date <= date_val <= request.end_date:
                                        date_str = date_val.strftime("%Y-%m-%d")
                                        rating_metric = self._extract_float_metric(row, ["daily average rating", "average rating", "daily average", "rating", "total average rating", "total average"])
                                        
                                        if date_str not in daily_data:
                                            daily_data[date_str] = {}
                                        if rating_metric is not None:
                                            daily_data[date_str]["rating"] = rating_metric
                            elif resp.status_code == 404:
                                logger.info(f"Ratings overview report not found for {yyyyMM} (GCS 404)")
                            else:
                                logger.warning(f"Failed to fetch ratings report for {yyyyMM}: GCS returned {resp.status_code}")
                        except Exception as e:
                            logger.error(f"Error fetching/parsing ratings report for {yyyyMM}: {e}")
            except Exception as e:
                logger.error(f"Failed to fetch GCS reports: {e}")

        # 3. Formulate response CampaignData list
        campaign_name = package_name if package_name else "Google Play"
        campaign_data_list = []
        
        if daily_data:
            for date_str, metrics in sorted(daily_data.items()):
                metrics_copy = metrics.copy()
                # Put the reviews count on the start date if matches
                if date_str == request.start_date.strftime("%Y-%m-%d") and reviews_count > 0:
                    metrics_copy["reviews_count"] = reviews_count
                campaign_data_list.append(CampaignData(
                    campaign_name=campaign_name,
                    date=date_str,
                    metrics=metrics_copy
                ))
        else:
            # Fallback to reviews count only
            campaign_data_list.append(CampaignData(
                campaign_name=campaign_name,
                date=request.start_date.strftime("%Y-%m-%d"),
                metrics={"reviews_count": reviews_count}
            ))
            
        return campaign_data_list

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["reviews_count", "rating", "installs", "uninstalls"],
            "dimensions": ["package_name", "date", "country"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            android_creds = self._load_credentials(
                creds["service_account_json"],
                scopes=["https://www.googleapis.com/auth/androidpublisher"]
            )
            service = build("androidpublisher", "v3", credentials=android_creds)
            service.reviews().list(packageName=creds["package_name"], maxResults=1).execute()
            return True
        except Exception:
            return False
