AI Chatbot example using Amazon Bedrock

Demonstrates how Temporal and Amazon Bedrock can be used to quickly build bulletproof AI applications.

## Pre-requisites

1. An AWS account with Bedrock enabled.
2. A machine that has access to Bedrock.
3. A local Temporal server running on the same machine. See [Temporal's dev server docs](https://docs.temporal.io/cli#start-dev-server) for more information.

A simple way of setting up your environment is to create an AWS EC2 instance with the `AmazonBedrockFullAccess` policy attached. A simple way to access the code and the Temporal server UI running on the EC2 instance is via the [Remote SSH: Connect to Host...](https://code.visualstudio.com/docs/remote/ssh) command in Visual Studio Code.

## Running the example

The example is split into 3 sections. See README.md in each sub-directory for instructions on running each.