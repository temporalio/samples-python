# Encryption with JWT Sample

This sample shows how to make an encryption codec for end-to-end encryption. It is built to work with the encryption
samples [in TypeScript](https://github.com/temporalio/samples-typescript/tree/main/encryption) and
[in Go](https://github.com/temporalio/samples-go/tree/main/encryption).

For this sample, the optional `encryption` and `bedrock` dependency groups must be included. To include, run:

    poetry install --with encryption,bedrock

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the
worker:

    poetry run python worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflow:

    poetry run python starter.py

The workflow should complete with the hello result. To view the workflow, use [temporal](https://docs.temporal.io/cli):

    temporal workflow show --workflow-id encryption-workflow-id

Note how the result looks like (with wrapping removed):

```
    Output:[encoding binary/encrypted: payload encoding is not supported]
```

This is because the data is encrypted and not visible. To make data visible to external Temporal tools like `temporal` and
the UI, start a [codec server](codec-server) in another terminal:

    poetry run python codec_server.py

Now with that running, run `temporal` again with the codec endpoint:

    temporal workflow show --workflow-id encryption-workflow-id --codec-endpoint http://localhost:8081

Notice now the output has the unencrypted values:

```
    Result:["Hello, Temporal"]
```

This decryption did not leave the local machine here.

Same case with the web UI. If you go to the web UI, you'll only see encrypted input/results. But, assuming your web UI
is at `http://localhost:8233` (this is the default for the local dev server), if you set the "Remote Codec Endpoint" in the web UI to `http://localhost:8081` you can
then see the unencrypted results. This is possible because CORS settings in the codec server allow the browser to access
the codec server directly over localhost. They can be changed to suit Temporal cloud web UI instead if necessary.

## Connection to Temporal Cloud

Set the following environment variables when starting a worker or running the starter:

- `TEMPORAL_NAMESPACE="your.namespace"`
- `TEMPORAL_ADDRESS="your.namespace.tmprl.cloud:7233"`
- `TEMPORAL_TLS_CERT="/path/to/your.crt"`
- `TEMPORAL_TLS_KEY="/path/to/your.key"`

## Connection to AWS KMS

Set the following environment variables when starting a worker or the codec server:

- `AWS_ACCESS_KEY_ID="your.aws_access_key_id"`
- `AWS_SECRET_ACCESS_KEY="your.aws_secret_access_key"`
- `AWS_SESSION_TOKEN="your.aws_session_token"`

## Codec Server

To run the server using HTTPS create openssl certificate files in the `encryption_jwt` directory.
Run the following command in a `_certs` directory off the project root; it will create a certificate
that's good for 10 years.

```sh
openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes -keyout localhost.key -out localhost.pem -subj "/CN=localhost"
```

Pass the names of the files using the following environment variables.

- `SSL_PEM="../_certs/localhost.pem"`
- `SSL_KEY="../_certs/localhost.key"`

## Protobuf

Install the python tools for protobufs.

Clone the following two repositories:

```sh
git clone https://github.com/temporalio/api-cloud.git
git clone https://github.com/googleapis/googleapis.git
```

Copy the `temporal` directory and its contents, from `api_cloud` into the root of this project.
Copy the `google` directory and its contents, from `googleapis` into the root of this project.

From the project root generate the python wrappers:

```sh
python -m grpc_tools.protoc -I./ --python_out=./ --grpc_python_out=./ temporal/api/cloud/cloudservice/v1/*.proto
```
