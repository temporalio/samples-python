#!/bin/bash
set -euo pipefail

FUNCTION_NAME="${1:?Usage: deploy-lambda.sh <function-name>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Install the published temporalio package (Linux wheels) with the OTel extras
# needed by the lambda_worker contrib module
uv pip install --target "$SCRIPT_DIR/package" --python-platform x86_64-unknown-linux-gnu \
    --only-binary=:all: "temporalio[lambda-worker-otel]"

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
