"""
Test if we can patch the event loop to work with anyio/sniffio
"""

import asyncio
import sys


def patch_event_loop():
    """Patch event loop for anyio compatibility"""
    loop = asyncio.get_event_loop()
    print(f"Event loop type: {type(loop)}")
    print(f"Has get_task_factory: {hasattr(loop, 'get_task_factory')}")

    if not hasattr(loop, "get_task_factory"):
        print("Adding get_task_factory...")
        loop.get_task_factory = lambda: None

    if not hasattr(loop, "set_task_factory"):
        print("Adding set_task_factory...")
        loop.set_task_factory = lambda factory: None

    print(f"After patch - has get_task_factory: {hasattr(loop, 'get_task_factory')}")


async def test_anyio():
    """Test if anyio/sniffio works after patching"""
    try:
        # Patch the event loop
        patch_event_loop()

        # Try importing anyio and using it
        import anyio

        print("anyio imported successfully")

        # Try sniffio
        import sniffio

        backend = sniffio.current_async_library()
        print(f"Detected async backend: {backend}")

        # Try creating anyio task group
        async with anyio.create_task_group() as tg:
            print("Successfully created anyio task group!")

        print("✅ anyio appears to be working!")
        return True

    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run with standard asyncio
    print("Testing with standard asyncio event loop...")
    success = asyncio.run(test_anyio())
    sys.exit(0 if success else 1)
