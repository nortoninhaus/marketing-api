#!/bin/bash
# ponytail: script para compilar con Docker local (con soporte Apple Silicon), subir a Artifact Registry y desplegar en Cloud Run.

IMAGE_URL="us-central1-docker.pkg.dev/inhausbrain/mcp-cloud-run-deployments/inhaus-marketing-api:latest"
SERVICE_NAME="inhaus-marketing-api"
REGION="us-central1"
PROJECT_ID="inhausbrain"

# --- Auth durable: ADC en vez de la cuenta activa OAuth (caduca ~1h). ---
# Sin esto, `gcloud builds submit` / `gcloud run deploy` fallan con
# "Reauthentication failed. cannot prompt during non-interactive execution."
# El ADC se obtiene una vez con `gcloud auth application-default login` y
# sobrevive a procesos no interactivos (mismo patron que portal-deploy-adc).
if [ -z "${CLOUDSDK_AUTH_ACCESS_TOKEN:-}" ]; then
  CLOUDSDK_AUTH_ACCESS_TOKEN="$(gcloud auth application-default print-access-token 2>/dev/null)" \
    || { echo "ERROR: no hay token ADC. Corre 'gcloud auth application-default login' una vez."; exit 1; }
  export CLOUDSDK_AUTH_ACCESS_TOKEN
fi
echo "deploy via ADC (${CLOUDSDK_AUTH_ACCESS_TOKEN:0:8}...) sin login interactivo"


echo "=== 1. Compilando imagen con Cloud Build ==="
gcloud builds submit --project="$PROJECT_ID" --tag="$IMAGE_URL" .

echo "=== 2. Desplegando nueva imagen en Cloud Run ==="
# --session-affinity NO es opcional: el transporte SSE del MCP guarda la sesión
# (/mcp/sse -> session_id) en la MEMORIA de la instancia. Sin afinidad, Cloud Run
# reparte el POST /mcp/messages a otra instancia que no conoce ese session_id y
# responde 404 "Could not find session" -> el agente ve el MCP como caído.
gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE_URL" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --set-env-vars="ENABLE_BIGQUERY_SINK=true,BIGQUERY_PROJECT_ID=$PROJECT_ID,BIGQUERY_DATASET_ID=marketing_data,BIGQUERY_TABLE_ID=raw_campaign_data,MARKETING_PUBLIC_URL=https://inhaus-marketing-api-1096509611056.us-central1.run.app" \
  --session-affinity \
  --allow-unauthenticated

echo "=== ¡Proceso Completado! ==="
