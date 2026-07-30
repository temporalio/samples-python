# Request/Response Sample with Update-Based Responses

This sample shows how to send a request to a running workflow and get a response
back, using [Workflow Update](https://docs.temporal.io/encyclopedia/workflow-message-passing#updates).
The update handler runs an activity and returns its result directly to the caller,
so there is no response task queue, no callback activity and no request IDs to
correlate.

It is a port of the Go [reqrespupdate](https://github.com/temporalio/samples-go/tree/main/reqrespupdate)
sample.

To run, open three terminals.

Run the worker in the first:

    uv run reqrespupdate/worker.py

Start the long-running workflow in the second:

    uv run reqrespupdate/starter.py

Then request an uppercasing every second in the third:

    uv run reqrespupdate/requester.py

Several requesters can be run at once, in separate terminals, to confirm they are
independent of one another.

### Comparison with the other request/response approaches

The Go samples also show request/response via
[activities](https://github.com/temporalio/samples-go/tree/main/reqrespactivity) and via
[queries](https://github.com/temporalio/samples-go/tree/main/reqrespquery). Both predate
Workflow Update. Update is the recommended approach and is the only one ported here.

### Continue-as-new and backpressure

Workflow history cannot grow without limit, so a workflow that fields requests
indefinitely has to continue-as-new periodically. To avoid losing work, it must do so
only when no handler is still running, which means there has to be a moment where the
workflow is idle.

`workflow.all_handlers_finished()` reports exactly that: whether any update or signal
handler is still executing, including one waiting on an activity retry. The workflow
waits on it before continuing as new, so no in-flight request is interrupted.

If requests arrive faster than they are handled, that idle moment may never come and
history keeps growing. The workflow therefore rejects requests from the update
validator once it is draining toward a continue-as-new. A validator rejection is not
written to history, which is what makes it the right tool when the problem is history
size. The requester sees the rejection and retries, and because the retry targets the
same workflow ID it lands on the fresh run.

The retry policy and timeout on the activity affect how long a handler can stay in
flight, and therefore how long the workflow can be kept from continuing as new. Set
them balancing resilience against the need for a period of idleness.
