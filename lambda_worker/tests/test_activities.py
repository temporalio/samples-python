from temporalio.testing import ActivityEnvironment

from activities import hello_activity


async def test_hello_activity() -> None:
    result = await ActivityEnvironment().run(hello_activity, "Temporal")

    assert result == "Hello, Temporal!"
