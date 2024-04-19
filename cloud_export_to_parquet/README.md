# Cloud Export to parquet sample

This is an example workflow to convert exported file from proto to parquet file. The workflow is an hourly schedule. 

For this sample, the optional `cloud_export_to_parquet` dependency group must be included. To include, run:

    poetry install --with cloud_export_to_parquet

Before you start, please modify workflow input in `create_schedule.py` with your s3 bucket and namespace. Also make sure you've the right AWS permission set up in your environment to allow this workflow read and write to your s3 bucket. 

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the worker:

```bash
poetry run python run_worker.py
```

This will start the worker. Then, in another terminal, run the following to execute the schedule:

```bash
poetry run python create_schedule.py
```

The workflow should convert exported file in your input s3 bucket to parquet in your specified location.
