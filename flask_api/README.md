# Flask Temporal Workflow Template

This repository provides settings for [Flask](https://flask.palletsprojects.com/en/2.2.x/) and the Temporal Python SDK for durable workflows.

## Getting Started

For this sample, the optional `flask_api` dependency group must be included. To include, run:

```bash
poetry install --with flask_api
```

Start the Worker:

```bash
poetry run python run_worker.py
```

Run the Flask file:

```bash
poetry run python run_flask.py
```

## Further Reading

- [Flask documentation](https://flask.palletsprojects.com/en/2.2.x/)
- [Temporal documentation](https://docs.temporal.io)
