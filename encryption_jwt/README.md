# Encryption with Temporal user role access

This sample demonstrates:

- CORS settings to allow connections to a codec server
- using a KMS key to encrypt/decrypt payloads
- extracting data from a JWT
- controlling decyption based on a user's Temporal Cloud role

The Codec Server uses the [Operations API](https://docs.temporal.io/ops) to get user information. It would be helpful to be familiar with the API's requirements. This API is currently a beta relase and may change in the future.

## Install

For this sample, the optional `encryption_jwt` and `bedrock` dependency groups must be included. To include, run:

```sh
poetry install --with encryption_jwt,bedrock
```

## Setup

> [!WARNING]
> You must connect your Worker(s) to Temporal Cloud to see decryption working in the Web UI.

### Key management

This example uses the [AWS Key Management Service](https://aws.amazon.com/kms/) (KMS). You will need
to create a "Customer managed key" with its Alias set to your Temporal Namespace (replace `.`s with `_`s).
Alternately replace the key management portion with your own implementation.

### Self-signed certificates

The codec server will need to use HTTPS, self-signed certificates will work in the development
environment. Run the following command in a `_certs` directory that's a subdirectory of this one.
It will create certificate files that are good for 10 years.

```sh
openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes -keyout localhost.key -out localhost.pem -subj "/CN=localhost"
```

In the projects you can access the files using the following relative paths.

- `./_certs/localhost.pem`
- `./_certs/localhost.key`

## Run

### Worker

To run, first see the [repo README.md](../README.md) for prerequisites.

Before starting the worker, open a terminal and add the following environment variables with
appropriate values:

```sh
export TEMPORAL_ADDRESS=<your temporal domain and port>
export TEMPORAL_TLS_CERT=<path to the crt file used to generate the CA Certificate for the temporal namespace>
export TEMPORAL_TLS_KEY=<path to the key file used to generate the CA Certificate for the temporal namespace>
export AWS_ACCESS_KEY_ID=<AWS account access key>
export AWS_SECRET_ACCESS_KEY=<AWS account secret key>
export AWS_SESSION_TOKEN=<AWS session token>
```

In the same terminal start the worker:

```sh
poetry run python worker.py <namespace>
```

> [!Note]
> You will need to run at least one Worker per-namespace.

### Codec server

The codec server allows you to see the encrypted payloads of workflows in the Web UI. The server
must be started with secure connections (HTTPS), you will need the paths to a pem (crt) and key
file. [Self-signed certificates](#self-signed-certificates) will work just fine.

You will also need a [Temporal API Key](https://docs.temporal.io/cloud/api-keys#generate-an-api-key). It's value is set using the `TEMPORAL_API_KEY` env var.

Open a new terminal and add the following environment variables with values:

```sh
export TEMPORAL_TLS_CERT=<path to the crt file used to generate the CA Certificate for the namespace>
export TEMPORAL_TLS_KEY=<path to the key file used to generate the CA Certificate for the namespace>
export TEMPORAL_API_KEY=<An API key> # see https://docs.temporal.io/cloud/tcld/apikey#create
export TEMPORAL_OPS_ADDRESS=saas-api.tmprl.cloud:443 # uses "saas-api.tmprl.cloud:443" if not provided
export TEMPORAL_OPS_API_VERSION=2024-05-13-00
export AWS_ACCESS_KEY_ID=<AWS account access key>
export AWS_SECRET_ACCESS_KEY=<AWS account secret key>
export AWS_SESSION_TOKEN=<AWS session token>
export SSL_PEM=<path to self-signed pem (crt) file>
export SSL_KEY=<path to self-signed key file>
```

In the same terminal start the codec server:

```sh
poetry run python codec_server.py
```

### Execute workflow

In a third terminal, add the environment variables:

```txt
export TEMPORAL_ADDRESS=<your temporal domain and port>
export TEMPORAL_TLS_CERT=<path to the crt file used to generate the CA Certificate for the namespace>
export TEMPORAL_TLS_KEY=<path to the key file used to generate the CA Certificate for the namespace>
```

Then run the command to execute the workflow:

```sh
poetry run python starter.py <namespace>
```

The workflow should complete with the hello result. To view the workflow, use [temporal](https://docs.temporal.io/cli):

```sh
temporal workflow show --workflow-id encryption-workflow-id
```

Note how the result looks (with wrapping removed):

```txt
Output:[encoding binary/encrypted: payload encoding is not supported]
```

This is because the data is encrypted and not visible.

## Temporal Web UI

Open the Web UI and select a workflow, you'll only see encrypted results. To see decrypted results:

- You must have the Temporal role of "admin"
- The codec server must be running
- Set the "Remote Codec Endpoint" in the web UI to the codec server domain: `https://localhost:8081`
  - Both the "Pass the user access token" and "Include cross-origin credentials" must be enabled

Once those requirements are met you can then see the unencrypted results. This is possible because
CORS settings in the codec server allow the browser to access the codec server directly over
localhost. Decrypted data never leaves your local machine. See [Codec
Server](https://docs.temporal.io/production-deployment/data-encryption)
