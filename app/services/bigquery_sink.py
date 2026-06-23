"""
BigQuery Sink Service — Dual-write marketing data to BigQuery.
"""

import logging
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google.cloud import bigquery
from google.api_core import exceptions
from app.config import settings
from app.models.requests import Platform

logger = logging.getLogger(__name__)

class BigQuerySink:
    def __init__(self):
        self.client: Optional[bigquery.Client] = None
        if settings.enable_bigquery_sink:
            try:
                self.client = bigquery.Client(project=settings.bigquery_project_id)
                logger.info("BigQuery client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize BigQuery client: {e}")

    def _get_table_id(self) -> str:
        return f"{settings.bigquery_project_id}.{settings.bigquery_dataset_id}.{settings.bigquery_table_id}"

    async def write_data(
        self, 
        platform: Platform, 
        data: List[Dict[str, Any]], 
        client_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Background task to write data to BigQuery."""
        if not self.client or not settings.enable_bigquery_sink:
            return

        if not data:
            return

        # Prepare rows
        timestamp = datetime.now(timezone.utc).isoformat()
        rows_to_insert = []
        for item in data:
            row = {
                "platform": platform.value,
                "client_id": client_id,
                "user_id": user_id,
                "data": json.dumps(item),
                "metadata": json.dumps(metadata or {}),
                "ingested_at": timestamp
            }
            rows_to_insert.append(row)

        try:
            await asyncio.to_thread(self._insert_rows, rows_to_insert)
            logger.info(f"Successfully wrote {len(rows_to_insert)} rows to BigQuery for {platform.value}")
        except Exception as e:
            logger.error(f"BigQuery write failed for {platform.value}: {e}")

    def _insert_rows(self, rows: List[Dict[str, Any]]):
        table_id = self._get_table_id()
        errors = self.client.insert_rows_json(table_id, rows)
        if errors:
            raise Exception(f"BigQuery insert errors: {errors}")

    async def ensure_dataset_and_table(self):
        """Utility to create dataset and table if they don't exist."""
        if not self.client:
            return

        dataset_id = f"{settings.bigquery_project_id}.{settings.bigquery_dataset_id}"
        table_id = self._get_table_id()

        def _setup():
            # Create Dataset
            try:
                self.client.get_dataset(dataset_id)
            except exceptions.NotFound:
                dataset = bigquery.Dataset(dataset_id)
                dataset.location = "US"
                self.client.create_dataset(dataset, timeout=30)
                logger.info(f"Created dataset {dataset_id}")

            # Create Table
            schema = [
                bigquery.SchemaField("platform", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("client_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("data", "JSON", mode="REQUIRED"),
                bigquery.SchemaField("metadata", "JSON", mode="NULLABLE"),
                bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="REQUIRED"),
            ]
            
            try:
                self.client.get_table(table_id)
            except exceptions.NotFound:
                table = bigquery.Table(table_id, schema=schema)
                self.client.create_table(table)
                logger.info(f"Created table {table_id}")

        await asyncio.to_thread(_setup)

# Global instance
bq_sink = BigQuerySink()
