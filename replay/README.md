# Replay Sample

This sample shows you how you can verify changes to workflow code are compatible with existing
workflow histories.

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the
worker:

    uv run worker.py

This will start the worker. Then, in another terminal, run the following to execute a workflow:

    uv run starter.py

Next, run the replayer:

    uv run replayer.py

Which should produce some output like:

    WorkflowReplayResults(replay_failures={})

Great! Replay worked. Of course, the reason for the exercise is to catch if you've changed workflow
code in a manner which is *not* compatible with the existing histories. Try it. Open up `worker.py`
and change the `JustActivity` workflow to sleep just before running the activity. Add
`await asyncio.sleep(0.1)` just before the line with `workflow.execute_activity`.

Now run the replayer again. The results from the `replay_workflows` call now indeed contains a
failure! Something like:
    
    WorkflowReplayResults(replay_failures={'e6418672-323c-4868-9de4-ece8f34fec53': NondeterminismError('Workflow activation completion failed: Failure { failure: Some(Failure { message: "Nondeterminism(\\"Timer machine does not handle this event: HistoryEvent(id: 8, Some(ActivityTaskScheduled))\\")", source: "", stack_trace: "", encoded_attributes: None, cause: None, failure_info: Some(ApplicationFailureInfo(ApplicationFailureInfo { r#type: "", non_retryable: false, details: None })) }) }')})

This is telling you that the workflow is not compatible with the existing history. Phew! Glad we
didn't deploy that one.
