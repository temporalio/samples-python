from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from temporalio.client import Client


def with_pydantic_ai(client: Client) -> Client:
    config = client.config()
    config["plugins"] = [*config["plugins"], PydanticAIPlugin()]
    return Client(**config)
