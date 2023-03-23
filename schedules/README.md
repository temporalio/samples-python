# Schedules Samples

These samples show how to schedule a Workflow Execution and control certain action.

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to run the
`hello_activity.py` sample:

    poetry run python run_worker.py
    poetry run python start_schedule.py

Replace `start_schedule.py` in the command with any other example filename to run it instead.

    poetry run python backfill_schedule.py
    poetry run python delete_schedule.py
    poetry run python describe_schedule.py
    poetry run python pause_schedule.py
    poetry run python update_schedule.py

- [x] create: Creates a new Schedule. Newly created Schedules return a Schedule ID to be used in other Schedule commands.
- [x] backfill: Executes Actions ahead of their specified time range.
- [x] delete: Deletes a Schedule. Deleting a Schedule does not affect any Workflows started by the Schedule.
- [x] describe: Shows the current Schedule configuration. This command also provides information about past, current, and future Workflow Runs.
- [x] pause: Pause and unpause a Schedule.
- [x] trigger: Triggers an immediate action with a given Schedule. By default, this action is subject to the Overlap Policy of the Schedule.
- [x] update: Updates an existing Schedule.
