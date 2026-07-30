# Infrequently Polling Activity

This sample shows how to use Activity retries for infrequent polling of a third-party service (for example via REST). This method can be used for infrequent polls of one minute or slower.

Activity retries are utilized for this option, setting the following Retry options:

- `backoff_coefficient`: to 1
- `initial_interval`: to the polling interval (in this sample set to 60 seconds)

This will enable the Activity to be retried exactly on the set interval.

To run, first see [README.md](../../README.md) for prerequisites.

Then, run the following from the root directory to run the sample:

    uv run polling/infrequent/run_worker.py

Then, in another terminal, run the following to execute the workflow:

    uv run polling/infrequent/run_infrequent.py


Since the test service simulates being _down_ for four polling attempts and then returns _OK_ on the fifth poll attempt, the Workflow will perform four Activity retries with a 60-second poll interval, and then return the service result on the successful fifth attempt.

Note that individual Activity retries are not recorded in Workflow History, so this approach can poll for a very long time without affecting the history size.
