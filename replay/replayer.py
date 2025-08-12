import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Replayer

from replay.worker import JustActivity, JustTimer, TimerThenActivity
from util import get_temporal_config_path


async def main():
    # Connect client
    config = ClientConfig.load_client_connect_config(
        config_file=str(get_temporal_config_path())
    )

    client = await Client.connect(**config)

    # Fetch the histories of the workflows to be replayed
    workflows = client.list_workflows('WorkflowId="replayer-workflow-id"')
    histories = workflows.map_histories()
    replayer = Replayer(workflows=[JustActivity, JustTimer, TimerThenActivity])
    results = await replayer.replay_workflows(histories, raise_on_replay_failure=False)
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
