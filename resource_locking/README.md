# Resource Locking Sample

This sample shows how to use a long-lived `LockManagerWorkflow` to ensure that each `resource` is used by at most one
`ResourceLockingWorkflow` at a time. `ResourceLockingWorkflow` runs several activities while it has ownership of a
resource.

Run the following from this directory to start the worker:

    poetry run python worker.py

This will start the worker. Then, in another terminal, run the following to execute several load workflows:

    poetry run python starter.py

You should see output indicating that the LockManagerWorkflow serialized access to each resource.

You can query the set of current lock holders with:

    tctl wf query -w lock_manager --qt get_current_holders

# Other approaches

There are simpler ways to manage concurrent access to resources. Consider using resource-specific workers/task queues,
and limiting the number of activity slots on the workers. The golang SDK also [sessions](https://docs.temporal.io/develop/go/sessions)
that allow workflows to pin themselves to workers.

The technique in this sample is capable of more complex resource locking than the options above, but it doesn't scale
as well. Specifically, it can:
- Manage access to a set of resources that is decoupled from the set of workers and task queues
- Run arbitrary code to place workloads on resources as they become available

# Caveats

This sample uses true locking (not leasing!) to avoid complexity and scaling concerns associated with heartbeating via
signals. Locking carries a risk where failure to unlock permanently removing a resource from the pool. However, with
Temporal's durable execution guarantees, this can only happen if:

- A LoadWorkflow times out (prohibited in the sample code)
- You shut down your workers and never restart them (unhandled, but irrelevant)

If a leak were to happen, you could discover the identity of the leaker using the query above, then:

    tctl wf signal -w lock_manager --name release_resource --input '{ "resource": "the resource", "workflow_id": "holder workflow id", "run_id": "holder run id" }'

Performance: A single LockManagerWorkflow scales to tens, but not hundreds, of lock/unlock events per second. It is
best suited for locking resources during long-running workflows. Actual performance will depend on your temporal
server's persistence layer.