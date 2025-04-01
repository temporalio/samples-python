# Semaphore Sample

This sample shows how to use a long-lived `semaphore_workflow` to ensure that each `resource` is used by at most one
`load_workflow` at a time. `load_workflow` runs several activities while it has ownership of a resource. 

Run the following from this directory to start the worker:

    poetry run python worker.py

This will start the worker. Then, in another terminal, run the following to execute several load workflows:

    poetry run python starter.py

You should see output indicating that the semaphore workflow serialized access to each resource.

You can query the set of current lock holders with:

    tctl wf query -w semaphore --qt get_current_holders

# Caveats

This sample uses true locking (not leasing!) to avoid complexity and scaling concerns associated with heartbeating via
signals. Locking carries the risk of a "leak" (failure to unlock) permanently removing a resource from the pool. With
Temporal's durabile execution guarantees, this can only happen if:

- A LoadWorkflow times out (prohibited in the sample code)
- You shut down your workers, and never restart them (unhandled, but probably irrelevant)

If a leak were to happen in the wild, you could discover the identity of the leaker using the query above, then:

    ~/Code/tctl/tctl wf signal -w semaphore --name release_resource --input '{ "resource": "the resource", "workflow_id": "holder workflow id", "run_id": "holder run id" }'