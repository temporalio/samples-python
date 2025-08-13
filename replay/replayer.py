import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile
from temporalio.worker import Replayer

from replay.worker import JustActivity, JustTimer, TimerThenActivity


async def main():
    # Connect client
    config = ClientConfigProfile.load()
    config["address"] = "localhost:7233"
    client = await Client.connect(**config.to_client_connect_config())

    # Fetch the histories of the workflows to be replayed
    workflows = client.list_workflows('WorkflowId="replayer-workflow-id"')
    histories = workflows.map_histories()
    replayer = Replayer(workflows=[JustActivity, JustTimer, TimerThenActivity])
    results = await replayer.replay_workflows(histories, raise_on_replay_failure=False)
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
