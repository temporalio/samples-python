# Temporal Python SDK Samples

This is a collection of samples showing how to use the [Python SDK](https://github.com/temporalio/sdk-python).

## Usage

Prerequisites:

* [uv](https://docs.astral.sh/uv/)
* [Temporal CLI installed](https://docs.temporal.io/cli#install)
* [Local Temporal server running](https://docs.temporal.io/cli/server#start-dev)

The SDK requires Python >= 3.9. You can install Python using uv. For example,

    uv python install 3.13

With this repository cloned, run the following at the root of the directory:

    uv sync

That loads all required dependencies. Then to run a sample, usually you just run it under uv. For example:

    uv run hello/hello_activity.py

Some examples require extra dependencies. See each sample's directory for specific instructions.

## Samples

* [hello](hello) - All of the basic features.
  <!-- Keep this list in alphabetical order and in sync on hello/README.md and root README.md -->
  * [hello_activity](hello/hello_activity.py) - Execute an activity from a workflow.
  * [hello_activity_choice](hello/hello_activity_choice.py) - Execute certain activities inside a workflow based on
    dynamic input.
  * [hello_activity_method](hello/hello_activity_method.py) - Demonstrate an activity that is an instance method on a
    class and can access class state.
  * [hello_activity_multiprocess](hello/hello_activity_multiprocess.py) - Execute a synchronous activity on a process
    pool.
  * [hello_activity_retry](hello/hello_activity_retry.py) - Demonstrate activity retry by failing until a certain number
    of attempts.
  * [hello_activity_threaded](hello/hello_activity_threaded.py) - Execute a synchronous activity on a thread pool.
  * [hello_async_activity_completion](hello/hello_async_activity_completion.py) - Complete an activity outside of the
    function that was called.
  * [hello_cancellation](hello/hello_cancellation.py) - Manually react to cancellation inside workflows and activities.
  * [hello_child_workflow](hello/hello_child_workflow.py) - Execute a child workflow from a workflow.
  * [hello_continue_as_new](hello/hello_continue_as_new.py) - Use continue as new to restart a workflow.
  * [hello_cron](hello/hello_cron.py) - Execute a workflow once a minute.
  * [hello_exception](hello/hello_exception.py) - Execute an activity that raises an error out of the workflow and out
    of the program.
  * [hello_local_activity](hello/hello_local_activity.py) - Execute a local activity from a workflow.
  * [hello_mtls](hello/hello_mtls.py) - Accept URL, namespace, and certificate info as CLI args and use mTLS for
    connecting to server.
  * [hello_parallel_activity](hello/hello_parallel_activity.py) - Execute multiple activities at once.
  * [hello_query](hello/hello_query.py) - Invoke queries on a workflow.
  * [hello_search_attributes](hello/hello_search_attributes.py) - Start workflow with search attributes then change
    while running.
  * [hello_signal](hello/hello_signal.py) - Send signals to a workflow.
<!-- Keep this list in alphabetical order -->
* [activity_worker](activity_worker) - Use Python activities from a workflow in another language.
* [bedrock](bedrock) - Orchestrate a chatbot with Amazon Bedrock.
* [cloud_export_to_parquet](cloud_export_to_parquet) - Set up schedule workflow to process exported files on an hourly basis
* [context_propagation](context_propagation) - Context propagation through workflows/activities via interceptor.
* [custom_converter](custom_converter) - Use a custom payload converter to handle custom types.
* [custom_decorator](custom_decorator) - Custom decorator to auto-heartbeat a long-running activity.
* [custom_metric](custom_metric) - Custom metric to record the workflow type in the activity schedule to start latency.
* [dsl](dsl) - DSL workflow that executes steps defined in a YAML file.
* [encryption](encryption) - Apply end-to-end encryption for all input/output.
* [gevent_async](gevent_async) - Combine gevent and Temporal.
* [langchain](langchain) - Orchestrate workflows for LangChain.
* [message_passing/introduction](message_passing/introduction/) - Introduction to queries, signals, and updates.
* [message_passing/safe_message_handlers](message_passing/safe_message_handlers/) - Safely handling updates and signals.
* [message_passing/update_with_start/lazy_initialization](message_passing/update_with_start/lazy_initialization/) - Use update-with-start to update a Shopping Cart, starting it if it does not exist.
* [open_telemetry](open_telemetry) - Trace workflows with OpenTelemetry.
* [patching](patching) - Alter workflows safely with `patch` and `deprecate_patch`.
* [polling](polling) - Recommended implementation of an activity that needs to periodically poll an external resource waiting its successful completion.
* [prometheus](prometheus) - Configure Prometheus metrics on clients/workers.
* [pydantic_converter](pydantic_converter) - Data converter for using Pydantic models.
* [schedules](schedules) - Demonstrates a Workflow Execution that occurs according to a schedule.
* [sentry](sentry) - Report errors to Sentry.
* [trio_async](trio_async) - Use asyncio Temporal in Trio-based environments.
* [updatable_timer](updatable_timer) - A timer that can be updated while sleeping.
* [worker_specific_task_queues](worker_specific_task_queues) - Use unique task queues to ensure activities run on specific workers.
* [worker_versioning](worker_versioning) - Use the Worker Versioning feature to more easily version your workflows & other code.

## Test

Running the tests requires `poe` to be installed.

    uv tool install poethepoet

Once you have `poe` installed you can run:

    poe test
