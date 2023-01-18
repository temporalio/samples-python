# Encryption Sample

This sample shows how to make an encryption codec for end-to-end encryption. It is built to work with the encryption
samples [in TypeScript](https://github.com/temporalio/samples-typescript/tree/main/encryption) and
[in Go](https://github.com/temporalio/samples-go/tree/main/encryption).

For this sample, the optional `encryption` dependency group must be included. To include, run:

    poetry install --with encryption

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the
worker:

    poetry run python worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflow:

    poetry run python starter.py

The workflow should complete with the hello result. To view the workflow, use [tctl](https://docs.temporal.io/tctl-v1/):

    tctl workflow show --workflow_id encryption-workflow-id

Note how the input/result look like (with wrapping removed):

```
    Input:[encoding binary/encrypted: payload encoding is not supported]
    ...
    Result:[encoding binary/encrypted: payload encoding is not supported]
```

This is because the data is encrypted and not visible. To make data visible to external Temporal tools like `tctl` and
the UI, start a codec server in another terminal:

    poetry run python codec_server.py

Now with that running, run `tctl` again with the codec endpoint:

    tctl --codec_endpoint http://localhost:8081 workflow show --workflow_id encryption-workflow-id

Notice now the output has the unencrypted values:

```
    Input:["Temporal"]
    ...
    Result:["Hello, Temporal"]
```

This decryption did not leave the local machine here.

Same case with the web UI. If you go to the web UI, you'll only see encrypted input/results. But, assuming your web UI
is at `http://localhost:8080`, if you set the "Remote Codec Endpoint" in the web UI to `http://localhost:8081` you can
then see the unencrypted results. This is possible because CORS settings in the codec server allow the browser to access
the codec server directly over localhost. They can be changed to suit Temporal cloud web UI instead if necessary.