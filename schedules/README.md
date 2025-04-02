# Schedules Samples

These samples show how to schedule a Workflow Execution and control certain action.

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to run the `schedules/` sample:

    uv run run_worker.py
    uv run start_schedule.py

Replace `start_schedule.py` in the command with any other example filename to run it instead.

    uv run backfill_schedule.py
    uv run delete_schedule.py
    uv run describe_schedule.py
    uv run list_schedule.py
    uv run pause_schedule.py
    python run python trigger_schedule.py
    uv run update_schedule.py

- create: Creates a new Schedule. Newly created Schedules return a Schedule ID to be used in other Schedule commands.
- backfill: Backfills the Schedule by going through the specified time periods as if they passed right now.
- delete: Deletes a Schedule. Deleting a Schedule does not affect any Workflows started by the Schedule.
- describe: Shows the current Schedule configuration. This command also provides information about past, current, and future Workflow Runs.
- list: Lists Schedules.
- pause: Pause and unpause a Schedule.
- trigger: Triggers an immediate action with a given Schedule. By default, this action is subject to the Overlap Policy of the Schedule.
- update: Updates an existing Schedule.
