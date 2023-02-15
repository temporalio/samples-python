# Starlette Temporal Workflow Template

This repository provides settings for [Starelette](https://www.starlette.io/) and the Temporal Python SDK for durable workflows.

## Getting Started

For this sample, the optional `starlette` dependency group must be included.
To include, run:

```bash
poetry install --with starlette
```

Start the Worker:

```bash
poetry run python starlette/worker.py
```

Run Starlette:

```bash
cd starlette
poetry run uvicorn starter:app
```

Curl the API:

```bash
curl localhost:8000
```

Expected output:

```bash
{"response":"Hello, World!"}
```

## Further Reading

- [Starelette documentation](https://www.starlette.io/)
- [Temporal documentation](https://docs.temporal.io)
