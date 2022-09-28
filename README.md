# Temporal Python SDK Samples

This is the set of Python samples for the [Python SDK](https://github.com/temporalio/sdk-python).

**UNDER DEVELOPMENT**

The Python SDK is under development. There are no compatibility guarantees nor proper documentation pages at this time.

## Usage

Prerequisites:

* Python >= 3.7
* [Poetry](https://python-poetry.org)
* [Local Temporal server running](https://docs.temporal.io/clusters/quick-install/)

With this repository cloned, run the following at the root of the directory:

    poetry install

That loads all required dependencies. Then to run a sample, usually you just run it in Python. For example:

    poetry run python hello/hello_activity.py

Some examples require extra dependencies. See each sample's directory for specific instructions.

## Samples

* [hello](hello) - All of the basic features.
  <!-- Keep this list in alphabetical order and in sync on hello/README.md and root README.md -->
  * [hello_activity](hello/hello_activity.py) - Execute an activity from a workflow.
  * [hello_activity_choice](hello/hello_activity_choice.py) - Execute certain activities inside a workflow based on
    dynamic input.
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
* [activity_worker](activity_worker) - Use Python activities from a workflow in another language.
* [custom_converter](custom_converter) - Use a custom payload converter to handle custom types.
* [custom_decorator](custom_decorator) - Custom decorator to auto-heartbeat a long-running activity.
* [encryption](encryption) - Apply end-to-end encryption for all input/output.


## Test

Running the tests requires `poe` to be installed.

    python -m pip install poethepoet

Once you have `poe` installed you can run:

    poe test