# Temporal Python SDK Samples

This is the set of Python samples for the [Python SDK](https://github.com/temporalio/sdk-python).

**UNDER DEVELOPMENT**

The Python SDK is under development. There are no compatibility guarantees nor proper documentation pages at this time.

## Usage

Prerequisites:

* Python >= 3.7
* [Poetry](https://python-poetry.org)
* [Local Temporal server running](https://docs.temporal.io/clusters/quick-install/)

With this repository cloned, run the following at the root of the directory:

    poetry install --no-root

That loads all dependencies. Then to run a sample, usually you just run it in Python. For example:

    poetry run python hello_world/hello_world.py

See each sample's directory for specific instructions.

## Samples

* [Activity Worker](activity_worker) - Use Python activities from a workflow in another language
* [Hello World](hello_world) - Basic hello world workflow and activity
