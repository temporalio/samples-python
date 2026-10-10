#!/usr/bin/env bash
# Deploy the Temporal Cloud Run worker sample. Export the variables documented in
# README.md ("Deploy") first. The create steps are one-time and skipped when the
# resource already exists, so this is safe to re-run to redeploy.
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
: "${REGION:?set REGION}"
: "${REPOSITORY:?set REPOSITORY}"
: "${SERVICE_ACCOUNT_EMAIL:?set SERVICE_ACCOUNT_EMAIL}"
: "${TEMPORAL_API_KEY_SECRET:?set TEMPORAL_API_KEY_SECRET}"
: "${TEMPORAL_API_KEY_FILE:?set TEMPORAL_API_KEY_FILE}"
: "${COLLECTOR_CONFIG_SECRET:?set COLLECTOR_CONFIG_SECRET}"
: "${WORKER_IMAGE:?set WORKER_IMAGE}"

# Enable APIs, create the Artifact Registry repo and runtime service account.
gcloud services enable artifactregistry.googleapis.com cloudbuild.googleapis.com \
  monitoring.googleapis.com run.googleapis.com secretmanager.googleapis.com \
  telemetry.googleapis.com --project "$PROJECT_ID"
gcloud artifacts repositories describe "$REPOSITORY" --location "$REGION" --project "$PROJECT_ID" >/dev/null 2>&1 ||
  gcloud artifacts repositories create "$REPOSITORY" --location "$REGION" \
    --repository-format docker --project "$PROJECT_ID"
gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" --project "$PROJECT_ID" >/dev/null 2>&1 ||
  gcloud iam service-accounts create "${SERVICE_ACCOUNT_EMAIL%%@*}" --project "$PROJECT_ID"

# Grant the service account the collector's telemetry roles.
for role in roles/logging.logWriter roles/monitoring.metricWriter roles/telemetry.tracesWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member "serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role "$role"
done

# Store the API key and collector config as secrets the service account can read.
gcloud secrets describe "$TEMPORAL_API_KEY_SECRET" --project "$PROJECT_ID" >/dev/null 2>&1 ||
  gcloud secrets create "$TEMPORAL_API_KEY_SECRET" --data-file "$TEMPORAL_API_KEY_FILE" --project "$PROJECT_ID"
gcloud secrets describe "$COLLECTOR_CONFIG_SECRET" --project "$PROJECT_ID" >/dev/null 2>&1 ||
  gcloud secrets create "$COLLECTOR_CONFIG_SECRET" \
    --data-file gcp/cloud_run/collector-config.yaml --project "$PROJECT_ID"
for secret in "$TEMPORAL_API_KEY_SECRET" "$COLLECTOR_CONFIG_SECRET"; do
  gcloud secrets add-iam-policy-binding "$secret" \
    --member "serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role roles/secretmanager.secretAccessor --project "$PROJECT_ID"
done

# Build the image (build context is the sample dir, keeping credentials out).
gcloud builds submit gcp/cloud_run --region "$REGION" \
  --tag "$WORKER_IMAGE" --project "$PROJECT_ID"

# Render and deploy the two-container worker pool.
envsubst < gcp/cloud_run/worker-pool.yaml > /tmp/worker-pool.yaml
gcloud run worker-pools replace /tmp/worker-pool.yaml --project "$PROJECT_ID"
