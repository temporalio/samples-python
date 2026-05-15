#!/usr/bin/env bash
#
# One-shot demo: create a Worker Deployment, register a Lambda-backed
# Worker Deployment Version, and promote it to "current".
#
# Prereqs:
#   - `temporal` binary present in this directory (or symlinked)
#   - Temporal Cloud auth configured in the current shell
#   - The deployment named below does NOT already exist (the create step
#     fails non-zero on a conflict, and `set -e` will abort)
#
# Re-running: tear down via the UI / CLI between rehearsals.

set -euo pipefail

TEMPORAL_ADDRESS=replay-ma-01.a2dd6.tmprl.cloud:7233
TEMPORAL_NAMESPACE=replay-ma-01.a2dd6
TEMPORAL_API_KEY=<YOUR_TEMPORAL_API_KEY>
DEPLOYMENT_NAME="survey-poll-SA"
BUILD_ID="v1"
AWS_LAMBDA_ARN="arn:aws:lambda:us-east-1:123235337000:function:replay-survey-poll-sa-worker"
ASSUME_IAM_ROLE_ARN="arn:aws:iam::123235337000:role/Temporal-Cloud-Serverless-Worker-survey-replay-demo"
ASSUME_ROLE_EXTERNAL_ID="replay-demo"

banner() {
    echo
    echo "== $* =="
}

banner "Step 1: create Worker Deployment '$DEPLOYMENT_NAME'"
temporal worker deployment create --name "$DEPLOYMENT_NAME"

banner "Step 2: describe Worker Deployment (no versions yet)"
temporal worker deployment describe --name "$DEPLOYMENT_NAME"

banner "Step 3: create Worker Deployment Version '$BUILD_ID' (Lambda)"
temporal worker deployment create-version \
    --deployment-name "$DEPLOYMENT_NAME" \
    --build-id "$BUILD_ID" \
    --aws-lambda-function-arn "$AWS_LAMBDA_ARN" \
    --aws-lambda-assume-role-arn "$ASSUME_IAM_ROLE_ARN" \
    --aws-lambda-assume-role-external-id "$ASSUME_ROLE_EXTERNAL_ID"

sleep 2

banner "Step 4: describe Worker Deployment (version registered, not current)"
temporal worker deployment describe --name "$DEPLOYMENT_NAME"

banner "Step 5: set current version to '$BUILD_ID'"
temporal worker deployment set-current-version \
    --deployment-name "$DEPLOYMENT_NAME" \
    --build-id "$BUILD_ID" \
    --yes --ignore-missing-task-queues

sleep 2

banner "Step 6: describe Worker Deployment (version is now current)"
temporal worker deployment describe --name "$DEPLOYMENT_NAME"
