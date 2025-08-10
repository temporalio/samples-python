"""Test if anyio can be imported in a Temporal workflow"""

from temporalio import workflow


@workflow.defn(sandboxed=False)
class TestAnyioWorkflow:
    @workflow.run
    async def run(self):
        results = {"success": False, "error": None, "steps": []}

        try:
            # Step 1: Import anyio
            results["steps"].append("Importing anyio...")
            import anyio

            results["steps"].append("✓ anyio imported")

            # Step 2: Import sniffio
            results["steps"].append("Importing sniffio...")
            import sniffio

            results["steps"].append("✓ sniffio imported")

            # Step 3: Check current async library
            results["steps"].append("Checking async library...")
            backend = sniffio.current_async_library()
            results["steps"].append(f"✓ Detected backend: {backend}")

            # Step 4: Try creating a simple task group
            results["steps"].append("Creating anyio task group...")
            async with anyio.create_task_group() as tg:
                results["steps"].append("✓ Task group created")

            results["success"] = True

        except Exception as e:
            results["error"] = f"{type(e).__name__}: {str(e)}"
            workflow.logger.error(f"Error in anyio test: {e}", exc_info=True)

        return results
