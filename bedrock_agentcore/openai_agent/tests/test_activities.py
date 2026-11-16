from temporalio import activity

from activities import execute_code


def test_execute_code_is_an_activity() -> None:
    defn = activity._Definition.from_callable(execute_code)

    assert defn is not None
    assert defn.name == "execute_code"
    assert not defn.is_async  # sync: the Worker runs it on its thread pool
