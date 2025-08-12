import asyncio

from temporalio.client import Client


async def main() -> None:
        # Get repo root - 1 level deep from root
        repo_root = Path(__file__).resolve().parent.parent
        config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    client = await Client.connect(**config)

    async for schedule in await client.list_schedules():
        print(f"List Schedule Info: {schedule.info}.")


if __name__ == "__main__":
    asyncio.run(main())
