# Schedules README

- [x] create: Creates a new Schedule. Newly created Schedules return a Schedule ID to be used in other Schedule commands.
- [x] backfill: Executes Actions ahead of their specified time range.
- [x] delete: Deletes a Schedule. Deleting a Schedule does not affect any Workflows started by the Schedule.
- [x] describe: Shows the current Schedule configuration. This command also provides information about past, current, and future Workflow Runs.
- [x] list: Lists all Schedule configurations. Listing Schedules in Standard Visibility will only provide Schedule IDs.
- [x] toggle: (Pause in python) can pause and unpause a Schedule.
- [x] trigger: Triggers an immediate action with a given Schedule. By default, this action is subject to the Overlap Policy of the Schedule.
- [x] update: Updates an existing Schedule.

1. Start your Worker.

```bash
poetry run python schedules/run_worker.py
```

2. Run your Workflow

Start the Schedules file, then run a feature.

```bash
poetry run python schedules/start_schedules.py
poetry run python schedules/backfill_schedule.py
poetry run python schedules/delete_schedule.py
poetry run python schedules/describe_schedule.py
poetry run python schedules/toggle_schedule.py
poetry run python schedules/update_schedule.py
```
