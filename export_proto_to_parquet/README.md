# Temporal proto to parquet sample

This is an example workflow to convert exported file from proto to parquet file. The workflow is an hourly schedule

To use this code, make sure you have a [Temporal Cluster running](https://docs.temporal.io/docs/server/quick-install/) first.

Create a virtual environment and activate it. On macOS and Linux, run these commands:

```
python3 -m venv env
source env/bin/activate
```

On Windows, run these commands:

```
python -m venv env
env\Scripts\activate
```

With the virtual environment configured, install the Temporal SDK:

```
python -m pip install temporalio
python -m pip install pandas
python -m pip install pyarrow
python -m pip install boto3
```


Run the workflow:

```bash
python run_workflow.py
```

In another window, activate the virtual environment:

On macOS or Linux, run this command:

```
source env/bin/activate
```

On Windows, run this command:

```
python -m venv env
env\Scripts\activate
```


Then run the worker:


```bash
python run_worker.py
```

