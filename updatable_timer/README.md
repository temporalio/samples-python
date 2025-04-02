# Updatable Timer Sample

Demonstrates a helper class which relies on `workflow.wait_condition` to implement a blocking sleep that can be updated at any moment.

The sample is composed of the three executables:

* `worker.py` hosts the Workflow Executions.
* `starter.py` starts Workflow Executions.
* `wake_up_timer_updater.py` Signals the Workflow Execution with the new time to wake up.

First start the Worker:

```bash
uv run worker.py
```
Check the output of the Worker window. The expected output is:

```
Worker started, ctrl+c to exit
```

Then in a different terminal window start the Workflow Execution:

```bash
uv run starter.py
```
Check the output of the Worker window. The expected output is:
```
Workflow started: run_id=...
```

Then run the updater as many times as you want to change timer to 10 seconds from now:

```bash
uv run wake_up_time_updater.py
```

Check the output of the worker window. The expected output is:

```
Updated wake up time to 10 seconds from now
```