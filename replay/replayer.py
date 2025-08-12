import asyncio

from temporalio.client import Client
from temporalio.worker import Replayer

from replay.worker import JustActivity, JustTimer, TimerThenActivity


async def main():
    # Connect client
        # Get repo root - 1 level deep from root
        repo_root = Path(__file__).resolve().parent.parent
        config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    client = await Client.connect(**config)

    # Fetch the histories of the workflows to be replayed
    workflows = client.list_workflows('WorkflowId="replayer-workflow-id"')
    histories = workflows.map_histories()
    replayer = Replayer(workflows=[JustActivity, JustTimer, TimerThenActivity])
    results = await replayer.replay_workflows(histories, raise_on_replay_failure=False)
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
