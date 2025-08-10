"""
Patch for Temporal's event loop to work with anyio/sniffio.
The issue is that Temporal's event loop has get_task_factory() but it raises NotImplementedError.
"""

import asyncio

from temporalio import workflow


def patch_temporal_event_loop():
    """
    Patch Temporal's event loop to properly support anyio/sniffio.

    The issue: Temporal's _WorkflowInstanceImpl has get_task_factory() method
    but it raises NotImplementedError instead of returning None.
    """
    loop = asyncio.get_event_loop()

    # Save the original methods
    original_get_task_factory = loop.get_task_factory
    original_set_task_factory = (
        loop.set_task_factory if hasattr(loop, "set_task_factory") else None
    )

    # Create proper implementations
    def patched_get_task_factory():
        """Return None to indicate no custom task factory is set."""
        try:
            return original_get_task_factory()
        except NotImplementedError:
            # This is what anyio expects when no factory is set
            return None

    def patched_set_task_factory(factory):
        """No-op implementation for set_task_factory."""
        if original_set_task_factory:
            try:
                return original_set_task_factory(factory)
            except NotImplementedError:
                # Ignore if not implemented
                pass

    # Apply patches
    loop.get_task_factory = patched_get_task_factory
    if not hasattr(loop, "set_task_factory") or original_set_task_factory:
        loop.set_task_factory = patched_set_task_factory

    workflow.logger.info("Patched Temporal event loop for anyio compatibility")
