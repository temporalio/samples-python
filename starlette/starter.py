import asyncio

from temporalio.client import Client
from worker import SayHello

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


async def say_hello_endpoint(request):
    client = await Client.connect("localhost:7233")

    result = await client.execute_workflow(
        SayHello.run, "World", id="my-workflow-id", task_queue="my-task-queue"
    )
    return JSONResponse({"response": result})


app = Starlette(debug=True, routes=[Route("/", say_hello_endpoint)])

if __name__ == "__main__":
    asyncio.run(app())
