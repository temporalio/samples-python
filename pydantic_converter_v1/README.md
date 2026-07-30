# Pydantic v1 Converter Sample

**This sample shows how to use Pydantic v1 with Temporal. This is not recommended: use Pydantic v2 if possible, and use the
main [pydantic_converter](../pydantic_converter/README.md) sample.**

To install, run:

    uv sync --group pydantic-converter
    uv run pip uninstall pydantic pydantic-core
    uv run pip install pydantic==1.10

To run, first see the root [README.md](../README.md) for prerequisites. Then, run the following from the root directory to start the
worker:

    uv run pydantic_converter_v1/worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflow:

    uv run pydantic_converter_v1/starter.py

In the worker terminal, the workflow and its activity will log that it received the Pydantic models. In the starter
terminal, the Pydantic models in the workflow result will be logged.

### Notes

This sample also demonstrates use of `datetime` inside of Pydantic v1 models. Due to a known issue with the Temporal
sandbox, this class is seen by Pydantic v1 as `date` instead of `datetime` upon deserialization. This is due to a
[known Python issue](https://github.com/python/cpython/issues/89010) where, when we proxy the `datetime` class in the
sandbox to prevent non-deterministic calls like `now()`, `issubclass` fails for the proxy type causing Pydantic v1 to think
it's a `date` instead. In `worker.py`, we have shown a workaround of disabling restrictions on `datetime` which solves
this issue but no longer protects against workflow developers making non-deterministic calls in that module.