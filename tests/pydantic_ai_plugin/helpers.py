from temporalio.client import Client

from pydantic_ai.durable_exec.temporal import PydanticAIPlugin


def with_pydantic_ai(client: Client) -> Client:
    config = client.config()
    config["plugins"] = [*config["plugins"], PydanticAIPlugin()]
    return Client(**config)
