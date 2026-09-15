#!/bin/bash
set -euo pipefail

# Creates the IAM role that Temporal Cloud assumes to invoke your AgentCore
# runtime for Serverless Workers. The External ID is provided by Temporal Cloud
# in your namespace's serverless worker configuration.
#
# This is not the runtime's execution role: `agentcore deploy` creates that one.
#
# Get the runtime ARN from `agentcore status`, or:
#   aws bedrock-agentcore-control list-agent-runtimes

STACK_NAME="${1:?Usage: mk-invoke-role.sh <stack-name> <external-id> <agent-runtime-arn>}"
EXTERNAL_ID="${2:?Usage: mk-invoke-role.sh <stack-name> <external-id> <agent-runtime-arn>}"
RUNTIME_ARN="${3:?Usage: mk-invoke-role.sh <stack-name> <external-id> <agent-runtime-arn>}"
SAMPLE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

aws cloudformation create-stack \
  --stack-name "$STACK_NAME" \
  --template-body "file://$SAMPLE_DIR/iam-role-for-temporal-agentcore-invoke.yaml" \
  --parameters \
    ParameterKey=AssumeRoleExternalId,ParameterValue="$EXTERNAL_ID" \
    ParameterKey=AgentRuntimeARNs,ParameterValue="$RUNTIME_ARN" \
  --capabilities CAPABILITY_NAMED_IAM
