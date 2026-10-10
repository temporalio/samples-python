import asyncio
import sys

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from openrouter.budget_gate.workflow import BudgetGateWorkflow
from openrouter.shared import BatchResult


async def main() -> None:
    if len(sys.argv) != 3:
        print("usage: raise_budget.py <workflow-id> <new-budget-usd>")
        raise SystemExit(2)
    workflow_id, new_budget = sys.argv[1], float(sys.argv[2])

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    handle = client.get_workflow_handle(workflow_id, result_type=BatchResult)
    report = await handle.execute_update(BudgetGateWorkflow.raise_budget, new_budget)
    print(
        f"Budget is now ${report.budget_usd:.6f}; spent ${report.spent_usd:.6f} "
        f"across {report.completed} prompts; paused: {report.paused or 'none'}"
    )


if __name__ == "__main__":
    asyncio.run(main())
