# Worker Versioning Sample

This sample shows you how you can use the [Worker Versioning](https://docs.temporal.io/workers#worker-versioning)
feature to deploy incompatible changes to workflow code more easily.

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory:

    uv run example.py

This will add some Build IDs to a Task Queue, and will also run Workers with those versions to show how you can 
mark add versions, mark them as compatible (or not) with one another, and run Workers at specific versions. You'll
see that only the workers only process Workflow Tasks assigned versions they are compatible with.
