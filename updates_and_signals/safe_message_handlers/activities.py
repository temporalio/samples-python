import asyncio
from dataclasses import dataclass
from typing import List

from temporalio import activity


@dataclass
class AllocateNodesToJobInput:
    nodes: List[str]
    job_name: str


@activity.defn
async def allocate_nodes_to_job(input: AllocateNodesToJobInput):
    print(f"Assigning nodes {input.nodes} to job {input.job_name}")
    await asyncio.sleep(0.1)


@dataclass
class DeallocateNodesForJobInput:
    nodes: List[str]
    job_name: str


@activity.defn
async def deallocate_nodes_for_job(input: DeallocateNodesForJobInput):
    print(f"Deallocating nodes {input.nodes} from job {input.job_name}")
    await asyncio.sleep(0.1)


@dataclass
class FindBadNodesInput:
    nodes_to_check: List[str]


@activity.defn
async def find_bad_nodes(input: FindBadNodesInput) -> List[str]:
    await asyncio.sleep(0.1)
    bad_nodes = [n for n in input.nodes_to_check if int(n) % 5 == 0]
    if bad_nodes:
        print(f"Found bad nodes: {bad_nodes}")
    else:
        print("No new bad nodes found.")
    return bad_nodes
