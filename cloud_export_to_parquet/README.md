# Cloud Export to parquet sample

This is an example workflow to convert exported file from proto to parquet file. The workflow is an hourly schedule. 

Please make sure your python is 3.9 above. For this sample, run:

    uv sync --group=cloud-export-to-parquet

Before you start, please modify workflow input in `create_schedule.py` with your s3 bucket and namespace. Also make sure you've the right AWS permission set up in your environment to allow this workflow read and write to your s3 bucket. 

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the worker:

```bash
uv run run_worker.py
```

This will start the worker. Then, in another terminal, run the following to execute the schedule:

```bash
uv run create_schedule.py
```

The workflow should convert exported file in your input s3 bucket to parquet in your specified location.
