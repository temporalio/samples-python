# Activity Worker

This sample shows a Go workflow calling a Python activity.

First run the Go workflow worker by running this in the `go_workflow` directory in a separate terminal:

    go run .

Then in another terminal, run the sample from the root directory:

    uv run activity_worker/activity_worker.py

The Python code will invoke the Go workflow which will execute the Python activity and return.