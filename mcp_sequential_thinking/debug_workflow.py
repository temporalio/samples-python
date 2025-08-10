"""
Debug workflow to inspect Temporal's event loop
"""

import asyncio

from temporalio import workflow


@workflow.defn(sandboxed=False)
class DebugEventLoopWorkflow:
    @workflow.run
    async def run(self):
        # Get the event loop
        loop = asyncio.get_event_loop()

        # Collect info about the loop
        info = {
            "loop_type": str(type(loop)),
            "loop_class_name": type(loop).__name__,
            "has_get_task_factory": hasattr(loop, "get_task_factory"),
            "has_set_task_factory": hasattr(loop, "set_task_factory"),
            "loop_methods": sorted([m for m in dir(loop) if not m.startswith("_")]),
        }

        workflow.logger.info(f"Event loop info: {info}")

        # Try patching
        if not hasattr(loop, "get_task_factory"):
            workflow.logger.info("Patching get_task_factory...")
            loop.get_task_factory = lambda: None
            info["patched_get_task_factory"] = True

        if not hasattr(loop, "set_task_factory"):
            workflow.logger.info("Patching set_task_factory...")
            loop.set_task_factory = lambda factory: None
            info["patched_set_task_factory"] = True

        # Return early without trying anyio for now
        info["debug"] = "Basic event loop inspection only"

        return info
