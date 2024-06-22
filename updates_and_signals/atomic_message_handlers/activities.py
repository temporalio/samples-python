import asyncio
from typing import List
from temporalio import activity

@activity.defn
async def allocate_nodes_to_job(nodes: List[str], task_name: str) -> List[str]:
    print(f"Assigning nodes {nodes} to job {task_name}")
    await asyncio.sleep(0.1)


@activity.defn
async def deallocate_nodes_for_job(nodes: List[str], task_name: str) -> List[str]:
    print(f"Deallocating nodes {nodes} from job {task_name}")
    await asyncio.sleep(0.1)


@activity.defn
async def find_bad_nodes(nodes: List[str]) -> List[str]:
    await asyncio.sleep(0.1)
    bad_nodes = [n for n in nodes if int(n) % 5 == 0]
    if bad_nodes:
        print(f"Found bad nodes: {bad_nodes}")
    else:
        print("No new bad nodes found.")
    return bad_nodes
