from temporalio import activity


@activity.defn
async def failing_activity(should_fail: bool) -> str:
    if should_fail:
        try:
            raise ValueError("Inner exception with\nmultiple lines\nof text")
        except ValueError as inner:
            raise RuntimeError(
                "Outer exception that wraps\nanother exception with\nmultiline content"
            ) from inner
    return "Success!"


@activity.defn
async def complex_failing_activity() -> str:
    """Activity that creates a complex multiline traceback"""

    def nested_function():
        def deeply_nested():
            raise Exception("Deep exception with\nvery long\nmultiline\nerror message")

        deeply_nested()

    nested_function()
    return "This won't be reached"
