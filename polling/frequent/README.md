# Frequent polling

This sample shows how we can implement frequent polling (1 second or faster) inside our activity. The implementation is a loop that polls our service and then sleeps for the poll interval (1 second in the sample).

To ensure that polling activity is restarted in a timely manner, we make sure that it heartbeats on every iteration. Note that heartbeating only works if we set the `heartbeat_timeout` to a shorter value than the activity `start_to_close_timeout` timeout.

To run, first see [README.md](../README.md) for prerequisites.

Then, run the following from this directory to run the sample:

```bash
poetry run python run_worker.py
poetry run python run_frequent.py
```

The Workflow will continue to poll the service and heartbeat on every iteration until it succeeds.

Note that with frequent polling, the activity may execute for a long time, and it may be beneficial to set a Timeout on the Activity to avoid long-running Activities that are not heartbeating.

If the polling interval needs to be changed during runtime, the activity needs to be canceled and a new instance with the updated arguments needs to be started.
