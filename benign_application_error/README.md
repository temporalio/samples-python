# Benign Application Error
This sample shows how to use ApplicationError(category=BENIGN) in the Python SDK.
It demonstrates how the BENIGN error category affects logging severity and metrics emission for activity failures.

BENIGN ApplicationError
Activity failure is logged only at DEBUG level, otherwise no logging at the logger streaming (uncomment setLevel at line 15 in worker.py to check the logs)
No activity failure metrics are emitted.

Non-BENIGN ApplicationError
Activity failure is logged at WARN/ERROR.
Activity failure metrics are emitted.

This makes BENIGN useful for "expected" failure paths where noisy WARN logs and metrics are not desired.

Dependencies
For this sample, the optional python=json-logger dependency group must be included. To include, run:
    `uv sync`
    
Running the Sample

Start the worker in one terminal:
`    uv run benign_application_error/worker.py
`    

This will start a worker that registers the workflow and activity.
In another terminal, run the starter to execute the workflows:

`    uv run benign_application_error/starter.py
`
Expected Behavior

The first workflow runs with BENIGN=True and will not do any logging.
No failure metrics are emitted.

The second workflow runs with BENIGN=False. The activity fails, and the worker logs a WARN entry.
Failure metrics are emitted.

`running worker....
{"message": "Completing activity as failed ({'activity_id': '1', 'activity_type': 'greeting_activities', 'attempt': 1, 'namespace': 'default', 'task_queue': 'benign_application_error_task_queue', 'workflow_id': 'benign_application_error-wf-2', 'workflow_run_id': '0199828f-af08-7a19-ac0f-eed01a7f1974', 'workflow_type': 'BenignApplicationErrorWorkflow'})", "exc_info": "Traceback (most recent call last):\n  File \"/Users/deepikaawasthi/temporal/my-local-python-samples/samples-python/.venv/lib/python3.13/site-packages/temporalio/worker/_activity.py\", line 297, in _handle_start_activity_task\n    result = await self._execute_activity(start, running_activity, task_token)\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/deepikaawasthi/temporal/my-local-python-samples/samples-python/.venv/lib/python3.13/site-packages/temporalio/worker/_activity.py\", line 610, in _execute_activity\n    return await impl.execute_activity(input)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/deepikaawasthi/temporal/my-local-python-samples/samples-python/.venv/lib/python3.13/site-packages/temporalio/worker/_activity.py\", line 805, in execute_activity\n    return await input.fn(*input.args)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/deepikaawasthi/temporal/my-local-python-samples/samples-python/benign_application_error/activities.py\", line 15, in greeting_activities\n    raise ApplicationError(\"Without benign flag : Greeting not sent\")\ntemporalio.exceptions.ApplicationError: Without benign flag : Greeting not sent", "temporal_activity": {"activity_id": "1", "activity_type": "greeting_activities", "attempt": 1, "namespace": "default", "task_queue": "benign_application_error_task_queue", "workflow_id": "benign_application_error-wf-2", "workflow_run_id": "0199828f-af08-7a19-ac0f-eed01a7f1974", "workflow_type": "BenignApplicationErrorWorkflow"}}
`

Both workflows will still raise exceptions back to the starter, which you can see printed in the console.

Inspecting Workflows

Use the Temporal CLI to view workflow results:

`temporal workflow show --workflow-id benign_application_error-wf-1
temporal workflow show --workflow-id benign_application_error-wf-2`


Both workflows will show failure status, but only the Non-BENIGN run produces WARN logs and metrics.