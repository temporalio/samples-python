# Pydantic Converter Sample

This sample shows how to use the Pydantic data converter.

For this sample, the optional `pydantic_converter` dependency group must be included. To include, run:

    uv sync --group pydantic-converter

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from the root directory to start the
worker:

    uv run pydantic_converter/worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflow:

    uv run pydantic_converter/starter.py

In the worker terminal, the workflow and its activity will log that it received the Pydantic models. In the starter
terminal, the Pydantic models in the workflow result will be logged.
