import asyncio

from flask import Flask
from temporalio.client import Client

from flask_api.run_worker import SayHello

app = Flask(__name__)


@app.route("/")
async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    # Execute a workflow
    result = await client.execute_workflow(
        SayHello.run, "World", id="my-workflow-id", task_queue="my-task-queue"
    )

    return result


if __name__ == "__main__":
    asyncio.run(main())
    app.run(debug=True)
