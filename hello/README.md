# Hello Samples

These samples show basic workflow and activity features.

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to run the
`hello_activity.py` sample:

    poetry run python hello_activity.py

The result will be:

    Result: Hello, World!

Replace `hello_activity.py` in the command with any other example filename to run it instead.

## Samples

<!-- Keep this list in alphabetical order and in sync on hello/README.md and root README.md -->
* [hello_activity](hello_activity.py) - Execute an activity from a workflow.
* [hello_activity_choice](hello_activity_choice.py) - Execute certain activities inside a workflow based on dynamic
  input.
* [hello_activity_method](hello_activity_method.py) - Demonstrate an activity that is an instance method on a
  class and can access class state.
* [hello_activity_multiprocess](hello_activity_multiprocess.py) - Execute a synchronous activity on a process pool.
* [hello_activity_retry](hello_activity_retry.py) - Demonstrate activity retry by failing until a certain number of
  attempts.
* [hello_activity_threaded](hello_activity_threaded.py) - Execute a synchronous activity on a thread pool.
* [hello_async_activity_completion](hello_async_activity_completion.py) - Complete an activity outside of the function
  that was called.
* [hello_cancellation](hello_cancellation.py) - Manually react to cancellation inside workflows and activities.
* [hello_child_workflow](hello_child_workflow.py) - Execute a child workflow from a workflow.
* [hello_continue_as_new](hello_continue_as_new.py) - Use continue as new to restart a workflow.
* [hello_cron](hello_cron.py) - Execute a workflow once a minute.
* [hello_exception](hello_exception.py) - Execute an activity that raises an error out of the workflow and out of the
  program.
* [hello_local_activity](hello_local_activity.py) - Execute a local activity from a workflow.
* [hello_mtls](hello_mtls.py) - Accept URL, namespace, and certificate info as CLI args and use mTLS for connecting to
  server.
* [hello_parallel_activity](hello_parallel_activity.py) - Execute multiple activities at once.
* [hello_query](hello_query.py) - Invoke queries on a workflow.
* [hello_search_attributes](hello_search_attributes.py) - Start workflow with search attributes then change while
  running.
* [hello_signal](hello_signal.py) - Send signals to a workflow.
* [hello_update](hello_update.py) - Send a request to and a response from a client to a workflow execution.

Note: To enable the workflow update, set the `frontend.enableUpdateWorkflowExecution` dynamic config value to true.

    temporal server start-dev --dynamic-config-value frontend.enableUpdateWorkflowExecution=true