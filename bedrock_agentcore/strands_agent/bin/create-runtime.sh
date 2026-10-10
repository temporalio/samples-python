#!/bin/bash
set -euo pipefail

# Creates (or updates) the AgentCore runtime for this sample with the AgentCore
# CLI, which builds the container on CodeBuild and deploys via CDK:
#   https://github.com/aws/agentcore-cli
#
# The runtime is described by the checked-in agentcore/agentcore.json. Before the
# first run, set your account and region in agentcore/aws-targets.json and your
# Temporal connection details in the runtime's "envVars".

TARGET="${1:-default}"
SAMPLE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SAMPLE_DIR"

# uv is easy to miss: the CDK build shells out to it to install dependencies for
# the runtime's platform, and if it is absent the subprocess is killed and the
# CLI reports only "uv install failed ... with exit code null".
for tool in agentcore aws uv; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "'$tool' is required but not installed." >&2
    [ "$tool" = agentcore ] && echo "Install it with: npm install -g @aws/agentcore" >&2
    [ "$tool" = uv ] && echo "Install it from: https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
  fi
done

if [ ! -d agentcore/cdk ]; then
  echo "Bootstrapping the AgentCore CDK scaffold (one time)..." >&2
  PROJECT_NAME="$(python3 -c 'import json;print(json.load(open("agentcore/agentcore.json"))["name"])')"
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT
  agentcore create \
    --project-name "$PROJECT_NAME" \
    --no-agent \
    --output-dir "$TMP_DIR" \
    --skip-git \
    --skip-python-setup
  mv "$TMP_DIR/$PROJECT_NAME/agentcore/cdk" agentcore/cdk
fi

agentcore validate
agentcore deploy --target "$TARGET" -y

echo >&2
echo "Runtime deployed" >&2
