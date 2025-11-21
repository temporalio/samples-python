# Workflow Task Multiprocessing Sample


## Python Concurrency Limitations

CPU bound tasks effectively cannot be run in parallel in Python due to the [global interpreter lock](https://docs.python.org/3/glossary.html#term-global-interpreter-lock). The [Python standard library `threading` module](https://docs.python.org/3/library/threading.html) shares the following advice:

> CPython implementation detail: In CPython, due to the Global Interpreter Lock, only one thread can execute Python code at once (even though certain performance-oriented libraries might overcome this limitation). If you want your application to make better use of the computational resources of multi-core machines, you are advised to use multiprocessing or concurrent.futures.ProcessPoolExecutor. However, threading is still an appropriate model if you want to run multiple I/O-bound tasks simultaneously.

## Temporal Workflow Tasks in Python

[Temporal Workflow Tasks](https://docs.temporal.io/tasks#workflow-task) are CPU bound operations and therefore cannot be run concurrently using threads or an async runtime. Instead, we can use [`concurrent.futures.ProcessPoolExecutor`](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ProcessPoolExecutor) or the [`multiprocessing` module](https://docs.python.org/3/library/multiprocessing.html) as suggested by the `threading` documentation to more appropriately utilize machine resources.

This sample demonstrates using `concurrent.futures.ProcessPoolExecutor` to run multiple workflow worker processes.

## Running the Sample

To run, first see the root [README.md](../README.md) for prerequisites. Then, run the following from the root directory to run the `workflow_task_multiprocessing/` sample:

```
uv run workflow_task_multiprocessing/worker.py
uv run workflow_task_multiprocessing/starter.py
```

Both `worker.py` and `starter.py` have minimal arguments that can be modified to run the sample in varying contexts.

```
uv run workflow_task_multiprocessing/worker.py -h

usage: worker.py [-h] [-w NUM_WORKFLOW_WORKERS] [-a NUM_ACTIVITY_WORKERS]

options:
  -h, --help            show this help message and exit
  -w, --num-workflow-workers NUM_WORKFLOW_WORKERS
  -a, --num-activity-workers NUM_ACTIVITY_WORKERS
```

```
uv run workflow_task_multiprocessing/starter.py -h

usage: starter.py [-h] [-n NUM_WORKFLOWS]

options:
  -h, --help            show this help message and exit
  -n, --num-workflows NUM_WORKFLOWS
                        the number of workflows to execute
```

## Example Output

```
uv run workflow_task_multiprocessing/worker.py

starting 2 workflow worker(s) and 1 activity worker(s)
waiting for keyboard interrupt or for all workers to exit
workflow-worker:0 starting
workflow-worker:1 starting
activity-worker:0 starting
workflow-worker:0 shutting down
activity-worker:0 shutting down
workflow-worker:1 shutting down
```


```
uv run workflow_task_multiprocessing/starter.py

wf-starting-pid:19178 | activity-pid:19180 | wf-ending-pid:19178
wf-starting-pid:19179 | activity-pid:19180 | wf-ending-pid:19179
wf-starting-pid:19178 | activity-pid:19180 | wf-ending-pid:19178
wf-starting-pid:19179 | activity-pid:19180 | wf-ending-pid:19179
wf-starting-pid:19178 | activity-pid:19180 | wf-ending-pid:19178
wf-starting-pid:19179 | activity-pid:19180 | wf-ending-pid:19179
wf-starting-pid:19178 | activity-pid:19180 | wf-ending-pid:19178
wf-starting-pid:19179 | activity-pid:19180 | wf-ending-pid:19179
wf-starting-pid:19178 | activity-pid:19180 | wf-ending-pid:19178
wf-starting-pid:19179 | activity-pid:19180 | wf-ending-pid:19179
wf-starting-pid:19178 | activity-pid:19180 | wf-ending-pid:19178
wf-starting-pid:19179 | activity-pid:19180 | wf-ending-pid:19179
wf-starting-pid:19178 | activity-pid:19180 | wf-ending-pid:19178
wf-starting-pid:19179 | activity-pid:19180 | wf-ending-pid:19179
wf-starting-pid:19178 | activity-pid:19180 | wf-ending-pid:19178
wf-starting-pid:19179 | activity-pid:19180 | wf-ending-pid:19179
wf-starting-pid:19178 | activity-pid:19180 | wf-ending-pid:19178
wf-starting-pid:19179 | activity-pid:19180 | wf-ending-pid:19179
wf-starting-pid:19179 | activity-pid:19180 | wf-ending-pid:19179
wf-starting-pid:19178 | activity-pid:19180 | wf-ending-pid:19178
wf-starting-pid:19179 | activity-pid:19180 | wf-ending-pid:19179
wf-starting-pid:19178 | activity-pid:19180 | wf-ending-pid:19178
wf-starting-pid:19179 | activity-pid:19180 | wf-ending-pid:19179
wf-starting-pid:19178 | activity-pid:19180 | wf-ending-pid:19178
wf-starting-pid:19178 | activity-pid:19180 | wf-ending-pid:19178
```
