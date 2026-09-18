#!/bin/bash
set -euo pipefail

# ponytail: un único secreto montado mantiene las credenciales fuera de la imagen.

IMAGE_URL="us-central1-docker.pkg.dev/inhausbrain/mcp-cloud-run-deployments/inhaus-marketing-api:latest"
SERVICE_NAME="inhaus-marketing-api"
REGION="us-central1"
PROJECT_ID="inhausbrain"
ENV_SECRET_NAME="inhaus-marketing-api-env"

if [[ ! -f .env ]]; then
  echo "Falta .env; no se puede desplegar la configuración del servicio." >&2
  exit 1
fi

echo "=== 1. Guardando configuración en Secret Manager ==="
if gcloud secrets describe "$ENV_SECRET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud secrets versions add "$ENV_SECRET_NAME" --project="$PROJECT_ID" --data-file=.env
else
  gcloud secrets create "$ENV_SECRET_NAME" --project="$PROJECT_ID" --replication-policy=automatic --data-file=.env
fi

SERVICE_ACCOUNT=$(gcloud run services describe "$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" --format='value(spec.template.spec.serviceAccountName)')
gcloud secrets add-iam-policy-binding "$ENV_SECRET_NAME" \
  --project="$PROJECT_ID" \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor" >/dev/null

echo "=== 2. Compilando imagen con Cloud Build ==="
gcloud builds submit --project="$PROJECT_ID" --tag="$IMAGE_URL" .

echo "=== 3. Desplegando nueva imagen en Cloud Run ==="
gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE_URL" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --update-env-vars="ENV_FILE=/secrets/.env,ENABLE_BIGQUERY_SINK=true,BIGQUERY_PROJECT_ID=$PROJECT_ID,BIGQUERY_DATASET_ID=marketing_data,BIGQUERY_TABLE_ID=raw_campaign_data" \
  --update-secrets="/secrets/.env=$ENV_SECRET_NAME:latest" \
  --allow-unauthenticated

echo "=== ¡Proceso Completado! ==="
