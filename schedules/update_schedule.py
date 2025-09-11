import asyncio

from temporalio.client import (
    Client,
    ScheduleActionStartWorkflow,
    ScheduleUpdate,
    ScheduleUpdateInput,
)
from temporalio.envconfig import ClientConfig


async def main():
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
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
