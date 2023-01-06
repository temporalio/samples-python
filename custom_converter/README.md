# Custom Converter Sample

This sample shows how to make a custom payload converter for a type not natively supported by Temporal.

To run, first see [README.md](../README#usage) for prerequisites. Then, run the following from this directory to start the
worker:

    poetry run python worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflow:

    poetry run python starter.py

The workflow should complete with the hello result. If the custom converter was not set for the custom input and output
classes, we would get an error on the client side and on the worker side.