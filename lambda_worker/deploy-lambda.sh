#!/bin/bash
set -euo pipefail

FUNCTION_NAME="${1:?Usage: deploy-lambda.sh <function-name>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Export the locked artifact URLs so the Linux install uses the same SDK
# build and runtime dependencies as the local sample.
LOCK_DIR="$(mktemp -d)"
trap 'rm -rf "$LOCK_DIR"' EXIT
uv export --project "$SCRIPT_DIR" --locked --no-dev --no-emit-project \
    --format pylock.toml --output-file "$LOCK_DIR/pylock.toml" --quiet
uv pip install --target "$SCRIPT_DIR/package" --python-platform x86_64-unknown-linux-gnu \
    --only-binary=:all: --requirements "$LOCK_DIR/pylock.toml"

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
