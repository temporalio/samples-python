# Encryption Sample

This sample shows how to make an encryption codec for end-to-end encryption. It is built to work with the encryption
samples [in TypeScript](https://github.com/temporalio/samples-typescript/tree/main/encryption) and
[in Go](https://github.com/temporalio/samples-go/tree/main/encryption).


For this sample, the optional `encryption` dependency group must be included. To include, run:

    uv sync --group encryption

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the
worker:

    uv run worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflow:

    uv run starter.py

The workflow should complete with the hello result. To view the workflow, use [temporal](https://docs.temporal.io/cli):

    temporal workflow show --workflow-id encryption-workflow-id

Note how the result looks like (with wrapping removed):

```
    Output:[encoding binary/encrypted: payload encoding is not supported]
```

This is because the data is encrypted and not visible. To make data visible to external Temporal tools like `temporal` and
the UI, start a codec server in another terminal:

    uv run codec_server.py

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