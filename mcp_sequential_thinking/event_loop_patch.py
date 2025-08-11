import asyncio


def patch_sdk_python_event_loop():
    """
    The MCP Python SDK uses anyio.
    EventLoop.get_task_factory() must return None in order to work with anyio.
    Hopefully this is a simple change we can make in sdk-python without negative consequences.
    """

    loop = asyncio.get_event_loop()

    original_get_task_factory = loop.get_task_factory
    original_set_task_factory = (
        loop.set_task_factory if hasattr(loop, "set_task_factory") else None
    )

    def patched_get_task_factory():
        try:
            return original_get_task_factory()
        except NotImplementedError:
            return None

    def patched_set_task_factory(factory):
        if original_set_task_factory:
            try:
                return original_set_task_factory(factory)
            except NotImplementedError:
                pass

    loop.get_task_factory = patched_get_task_factory
    if not hasattr(loop, "set_task_factory") or original_set_task_factory:
        loop.set_task_factory = patched_set_task_factory
