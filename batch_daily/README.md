# Batch sample

This is an example workflow to process batches of records matching a particular
query criteria, in daily windows of time.

Please make sure your python is 3.9 above. For this sample, run:

```
poetry install --with batch_daily
```

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the worker:

```bash
poetry run python run_worker.py
```

This will start the worker. Then, in another terminal, run the following to execute the schedule:

```bash
poetry run python create_schedule.py
```
