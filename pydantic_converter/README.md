# Pydantic Converter Sample

This sample shows how to use the Pydantic data converter.

For this sample, the optional `pydantic_converter` dependency group must be included. To include, run:

    poetry install --with pydantic_converter

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the
worker:

    poetry run python worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflow:

    poetry run python starter.py

In the worker terminal, the workflow and its activity will log that it received the Pydantic models. In the starter
terminal, the Pydantic models in the workflow result will be logged.
