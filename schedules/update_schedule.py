import asyncio

from temporalio.client import (
    Client,
    ScheduleActionStartWorkflow,
    ScheduleUpdate,
    ScheduleUpdateInput,
)


async def main():
        # Get repo root - 1 level deep from root
        repo_root = Path(__file__).resolve().parent.parent
        config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    client = await Client.connect(**config)
    handle = client.get_schedule_handle(
        "workflow-schedule-id",
    )

    async def update_schedule_simple(input: ScheduleUpdateInput) -> ScheduleUpdate:
        schedule_action = input.description.schedule.action

        if isinstance(schedule_action, ScheduleActionStartWorkflow):
            schedule_action.args = ["my new schedule arg"]
        return ScheduleUpdate(schedule=input.description.schedule)

    await handle.update(update_schedule_simple)


if __name__ == "__main__":
    asyncio.run(main())
