import asyncio
from dataclasses import dataclass
from datetime import timedelta
from enum import IntEnum
from typing import List

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

# Activities that will be called by the workflow


@activity.defn
async def order_apples(amount: int) -> str:
    return f"Ordered {amount} Apples..."


@activity.defn
async def order_bananas(amount: int) -> str:
    return f"Ordered {amount} Bananas..."


@activity.defn
async def order_cherries(amount: int) -> str:
    return f"Ordered {amount} Cherries..."


@activity.defn
async def order_oranges(amount: int) -> str:
    return f"Ordered {amount} Oranges..."


# We have to make enumerates IntEnum to be JSON serializable
class Fruit(IntEnum):
    APPLE = 1
    BANANA = 2
    CHERRY = 3
    ORANGE = 4


@dataclass
class ShoppingListItem:
    fruit: Fruit
    amount: int


@dataclass
class ShoppingList:
    items: List[ShoppingListItem]


# Basic workflow that logs and invokes different activities based on input
@workflow.defn
class PurchaseFruitsWorkflow:
    @workflow.run
    async def run(self, shopping_list: ShoppingList) -> str:
        # Order each thing on the list
        ordered: List[str] = []
        for item in shopping_list.items:
            if item.fruit is Fruit.APPLE:
                order_function = order_apples
            elif item.fruit is Fruit.BANANA:
                order_function = order_bananas
            elif item.fruit is Fruit.CHERRY:
                order_function = order_cherries
            elif item.fruit is Fruit.ORANGE:
                order_function = order_oranges
            else:
                raise ValueError(f"Unrecognized fruit: {item.fruit}")
            ordered.append(
                await workflow.execute_activity(
                    order_function,
                    item.amount,
                    start_to_close_timeout=timedelta(seconds=5),
                )
            )
        return "".join(ordered)


async def main():
    # Start client
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-activity-choice-task-queue",
        workflows=[PurchaseFruitsWorkflow],
        activities=[order_apples, order_bananas, order_cherries, order_oranges],
    ):

        # While the worker is running, use the client to run the workflow and
        # print out its result. Note, in many production setups, the client
        # would be in a completely separate process from the worker.
        result = await client.execute_workflow(
            PurchaseFruitsWorkflow.run,
            ShoppingList(
                [
                    ShoppingListItem(Fruit.APPLE, 8),
                    ShoppingListItem(Fruit.BANANA, 5),
                    ShoppingListItem(Fruit.CHERRY, 1),
                    ShoppingListItem(Fruit.ORANGE, 4),
                ]
            ),
            id="hello-activity-choice-workflow-id",
            task_queue="hello-activity-choice-task-queue",
        )
        print(f"Order result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
