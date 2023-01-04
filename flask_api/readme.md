# Flask Temporal Workflow Template

This repository provides settings for Flask and the Temporal Python SDK for durable workflows.

## Prerequisites

Before using this template, make sure you have the following tools installed:

- [Python](https://www.python.org/downloads/) (3.6 or later)
- [Temporal CLI](https://github.com/temporalio/temporal)

## Getting Started

To use this template, follow these steps:

Activate the virtual environment:

```bash
python3 -m venv venv
. venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Start the Temporal server:

```bash
temporal server start-dev
```

Start the Worker:

```bash
python3 run_worker.py
```

Run either the Flask file:

```bash
python3 run_flask.py
```

Running the tests requires poe to be installed.

```bash
python -m pip install poethepoet
```

Run tests:

```bash
poe test
```

## Further Reading

- [Flask documentation](https://flask.palletsprojects.com/en/)
- [Temporal documentation](https://docs.temporal.io)
