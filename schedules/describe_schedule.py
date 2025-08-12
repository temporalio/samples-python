import asyncio

from temporalio.client import Client


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

    desc = await handle.describe()

    print(f"Returns the note: {desc.schedule.state.note}")


if __name__ == "__main__":
    asyncio.run(main())
