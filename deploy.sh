#!/bin/bash
# ponytail: script para compilar con Docker local (con soporte Apple Silicon), subir a Artifact Registry y desplegar en Cloud Run.

IMAGE_URL="us-central1-docker.pkg.dev/inhausbrain/mcp-cloud-run-deployments/inhaus-marketing-api:latest"
SERVICE_NAME="inhaus-marketing-api"
REGION="us-central1"
PROJECT_ID="inhausbrain"

echo "=== 1. Compilando imagen con Cloud Build ==="
gcloud builds submit --project="$PROJECT_ID" --tag="$IMAGE_URL" .

echo "=== 2. Desplegando nueva imagen en Cloud Run ==="
gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE_URL" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --set-env-vars="ENABLE_BIGQUERY_SINK=true,BIGQUERY_PROJECT_ID=$PROJECT_ID,BIGQUERY_DATASET_ID=marketing_data,BIGQUERY_TABLE_ID=raw_campaign_data" \
  --allow-unauthenticated

echo "=== ¡Proceso Completado! ==="
