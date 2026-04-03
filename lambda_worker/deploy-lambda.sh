#!/bin/bash
set -euo pipefail

FUNCTION_NAME="${1:?Usage: deploy-lambda.sh <function-name>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SDK_DIR="$SCRIPT_DIR/../../sdk-python"

# Install the published temporalio package (Linux wheels) and OTel dependencies
# TODO: Remove explicit OTel deps once lambda-worker-otel extra is published
uv pip install --target "$SCRIPT_DIR/package" --python-platform x86_64-unknown-linux-gnu --no-build \
    temporalio \
    "opentelemetry-api>=1.11.1,<2" \
    "opentelemetry-sdk>=1.11.1,<2" \
    "opentelemetry-exporter-otlp-proto-grpc>=1.11.1,<2" \
    "opentelemetry-semantic-conventions>=0.40b0,<1" \
    "opentelemetry-sdk-extension-aws>=2.0.0,<3"

# Overlay the local SDK's pure-Python source (for unpublished contrib code)
# TODO: Remove this step once the contrib package is published
cp -r "$SDK_DIR/temporalio/contrib" "$SCRIPT_DIR/package/temporalio"

# Copy application code into the package directory (all at zip root)
cp "$SCRIPT_DIR/lambda_function.py" "$SCRIPT_DIR/workflows.py" \
   "$SCRIPT_DIR/activities.py" "$SCRIPT_DIR/package/"

# Bundle with configuration files
cd "$SCRIPT_DIR/package"
zip -r "$SCRIPT_DIR/function.zip" .
cd "$SCRIPT_DIR"
zip function.zip client.pem client.key temporal.toml otel-collector-config.yaml

aws lambda update-function-code --function-name "$FUNCTION_NAME" --zip-file fileb://function.zip

rm -rf "$SCRIPT_DIR/package" "$SCRIPT_DIR/function.zip"
