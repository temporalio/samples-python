# Mutex

This mutex workflow demos an ability to lock/unlock a particular resource within a particular Temporal namespace
so that other workflows within the same namespace would wait until a resource lock is released. This is useful 
when we want to avoid race conditions or parallel mutually exclusive operations on the same resource.

One way of coordinating parallel processing is to use Temporal signals with [`start_signal`](https://docs.temporal.io/develop/python/message-passing#signal-with-start) and
make sure signals are getting processed sequentially, however the logic might become too complex if we
need to lock two or more resources at the same time. Mutex workflow pattern can simplify that.

This example enqueues two long running `SampleWorkflowWithMutex` workflows in parallel. And each of the workflows has a mutex section (lasting 2 seconds in this example). 
When `SampleWorkflowWithMutex` reaches the mutex section, it starts a mutex workflow via local activity, and blocks until
`acquire-lock-event` is received. Once `acquire-lock-event` is received, it enters critical section,
and finally releases the lock once processing is over by sending `release_lock` a signal to the `MutexWorkflow`.

## Run this sample


To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the
worker:

    uv run worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflows:

    uv run starter.py

This will start a worker to run your workflow and activities, then start two SampleWorkflowWithMutex in parallel, both locking on the same ressource.

The starter terminal should complete with the workflows IDs and the worker terminal should show the logs with the locking.

