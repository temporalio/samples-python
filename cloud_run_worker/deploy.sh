#!/usr/bin/env bash
# Deploy the Cloud Run worker to Google Cloud Run.
#
# Usage:
#   ./deploy.sh <service-name> <region> <project>
#
# Example:
#   ./deploy.sh my-temporal-worker us-central1 my-gcp-project
#
# Required env vars (pass via --set-env-vars or Secret Manager):
#   TEMPORAL_ADDRESS   - e.g. <namespace>.<account>.tmprl.cloud:7233
#   TEMPORAL_NAMESPACE - e.g. <namespace>.<account>
#   TEMPORAL_TLS_CERT  - base64-encoded mTLS client certificate (Temporal Cloud)
#   TEMPORAL_TLS_KEY   - base64-encoded mTLS client private key  (Temporal Cloud)

set -euo pipefail

SERVICE="${1:?Usage: $0 <service-name> <region> <project>}"
REGION="${2:?Usage: $0 <service-name> <region> <project>}"
PROJECT="${3:?Usage: $0 <service-name> <region> <project>}"

IMAGE="gcr.io/${PROJECT}/${SERVICE}:latest"

echo "Building and pushing image: ${IMAGE}"
gcloud builds submit --tag "${IMAGE}" --project "${PROJECT}" .

echo "Deploying Cloud Run service: ${SERVICE}"
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --project "${PROJECT}" \
  --platform managed \
  --no-allow-unauthenticated \
  --set-env-vars "TEMPORAL_ADDRESS=${TEMPORAL_ADDRESS},TEMPORAL_NAMESPACE=${TEMPORAL_NAMESPACE}" \
  --set-secrets "TEMPORAL_TLS_CERT=${SERVICE}-tls-cert:latest,TEMPORAL_TLS_KEY=${SERVICE}-tls-key:latest" \
  --min-instances 1 \
  --max-instances 10 \
  --no-cpu-throttling

echo "Done. Service URL:"
gcloud run services describe "${SERVICE}" --region "${REGION}" --project "${PROJECT}" \
  --format "value(status.url)"
