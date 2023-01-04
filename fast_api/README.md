# FastAPI Temporal Workflow Template

This repository provides settings for [FastAPI](https://fastapi.tiangolo.com) and the Temporal Python SDK for durable workflows.

## Getting Started

For this sample, the optional `fast_api` dependency group must be included. To include, run:

```bash
poetry install --with fast_api
```

Start the Worker:

```bash
poetry run python run_worker.py
```

Run the Fast API file:

```bash
poetry run python run_fast.py
```

## Further Reading

- [FastAPI documentation](https://fastapi.tiangolo.com)
- [Temporal documentation](https://docs.temporal.io)
