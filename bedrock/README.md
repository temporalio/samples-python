# AI Chatbot example using Amazon Bedrock

Demonstrates how Temporal and Amazon Bedrock can be used to quickly build bulletproof AI applications.

## Samples

* [basic](basic) - A basic Bedrock workflow to process a single prompt.
* [signals_and_queries](signals_and_queries) - Extension to the basic workflow to allow multiple prompts through signals & queries.
* [entity](entity) - Full multi-Turn chat using an entity workflow..

## Pre-requisites

1. An AWS account with Bedrock enabled.
2. A machine that has access to Bedrock.
3. A local Temporal server running on the same machine. See [Temporal's dev server docs](https://docs.temporal.io/cli#start-dev-server) for more information.

These examples use Amazon's Python SDK (Boto3). To configure Boto3 to use your AWS credentials, follow the instructions in [the Boto3 documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html).

## Running the samples

For these sample, the optional `bedrock` dependency group must be included. To include, run:

    uv sync --group bedrock

There are 3 Bedrock samples, see the README.md in each sub-directory for instructions on running each.