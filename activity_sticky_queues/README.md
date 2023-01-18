# Sticky Activity Queues

This sample is a Python implementation of the [TypeScript "Sticky Workers" example](https://github.com/temporalio/samples-typescript/tree/main/activities-sticky-queues), full credit for the design to the authors of that sample. A [sticky execution](https://docs.temporal.io/tasks#sticky-execution) is a job distribution design pattern where all workflow computational tasks are executed on a single worker. In the Go and Java SDKs this is explicitly supported via the Session option, but in other SDKs a different approach is required. 

Typical use cases for sticky executions include tasks where interaction with a filesystem is required, such as data processing or interacting with legacy access structures. This example will write text files to folders corresponding to each worker, located in the `demo_fs` folder. In production, these folders would typically be independent machines in a worker cluster.

This strategy is:
- Create a `get_available_task_queue` activity that generates a unique task queue name, `unique_worker_task_queue`.
- For activities intended to be "sticky", only register them in one Worker, and have that be the only Worker listening on that `unique_worker_task_queue`. This will be run on a series of `FileProcessing` workflows.
- Execute workflows from the Client like normal. Check the Temporal Web UI to confirm tasks were staying with their respective worker.

It doesn't matter where the `get_available_task_queue` activity is run, so it can be "non sticky" as per Temporal default behavior. In this demo, `unique_worker_task_queue` is simply a `uuid` initialized in the Worker, but you can inject smart logic here to uniquely identify the Worker, [as Netflix did](https://community.temporal.io/t/using-dynamic-task-queues-for-traffic-routing/3045). Our example differs from the Node sample by running across 5 unique task queues.

Activities have been artificially slowed with `time.sleep(3)` to simulate slow activities.

### Running This Sample

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the
worker:

    poetry run python worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflow:

    poetry run python starter.py

#### Example output:

```bash
(temporalio-samples-py3.10) user@machine:~/samples-python/activities_sticky_queues$ poetry run python starter.py 
Output checksums:
49d7419e6cba3575b3158f62d053f922aa08b23c64f05411cda3213b56c84ba4
49d7419e6cba3575b3158f62d053f922aa08b23c64f05411cda3213b56c84ba4
49d7419e6cba3575b3158f62d053f922aa08b23c64f05411cda3213b56c84ba4
49d7419e6cba3575b3158f62d053f922aa08b23c64f05411cda3213b56c84ba4
49d7419e6cba3575b3158f62d053f922aa08b23c64f05411cda3213b56c84ba4
49d7419e6cba3575b3158f62d053f922aa08b23c64f05411cda3213b56c84ba4
49d7419e6cba3575b3158f62d053f922aa08b23c64f05411cda3213b56c84ba4
49d7419e6cba3575b3158f62d053f922aa08b23c64f05411cda3213b56c84ba4
49d7419e6cba3575b3158f62d053f922aa08b23c64f05411cda3213b56c84ba4
49d7419e6cba3575b3158f62d053f922aa08b23c64f05411cda3213b56c84ba4
```

<details>
<summary>Checking the history to see where activities are run</summary>
All activities for the one workflow are running against the same task queue, which corresponds to unique workers:

![image](./static/all-activitites-on-same-task-queue.png)

</details>


