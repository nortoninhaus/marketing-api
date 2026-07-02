#!/bin/bash
# ponytail: script para compilar con Docker local (con soporte Apple Silicon), subir a Artifact Registry y desplegar en Cloud Run.

IMAGE_URL="us-central1-docker.pkg.dev/inhausbrain/mcp-cloud-run-deployments/inhaus-marketing-api:latest"
SERVICE_NAME="inhaus-marketing-api"
REGION="us-central1"
PROJECT_ID="inhausbrain"

echo "=== 1. Autenticando Docker con Google Artifact Registry ==="
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet

echo "=== 2. Compilando imagen local de Docker ==="
# --platform linux/amd64 es crítico porque estás en Mac M1/M2/M3; Cloud Run requiere arquitectura x86/amd64.
docker build --platform linux/amd64 -t "$IMAGE_URL" .

echo "=== 3. Subiendo imagen a Artifact Registry ==="
docker push "$IMAGE_URL"

echo "=== 4. Desplegando nueva imagen en Cloud Run ==="
gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE_URL" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --set-env-vars="ENABLE_BIGQUERY_SINK=true,BIGQUERY_PROJECT_ID=$PROJECT_ID,BIGQUERY_DATASET_ID=marketing_data,BIGQUERY_TABLE_ID=raw_campaign_data" \
  --allow-unauthenticated

echo "=== ¡Proceso Completado! ==="
