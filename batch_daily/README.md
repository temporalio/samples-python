# Batch sample

This is an example workflow that solves the following use-case.

You have a series of records that are divided into daily batches (think a days
worth of telemetry coming from an application).
Every day you would like to run a batch to process a days worth of records, but
you would also like to have the ability to backfill the records from a previous
window of time.

Backfilling might be run as a schedule or it might be run as a directly
triggered workflow.

Please make sure your python is 3.9 above. For this sample, run:

```
poetry install --with batch_daily
```

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the worker:

```bash
poetry run python run_worker.py
```

This will start the worker. Then, in another terminal, run the following to start the workflow:

```bash
poetry run python starter.py
```

Optionally, you can schedule the workflow with:

```bash
poetry run python create_schedule.py
```
