import pytest
from temporalio.testing import ActivityEnvironment

from hello.hello_activity_choice import (
    order_apples,
    order_bananas,
    order_cherries,
    order_oranges,
)

# A list of tuples where each tuple contains:
# - The activity function
# - The order amount
# - The expected result string
activity_test_data = [
    (order_apples, 5, "Ordered 5 Apples..."),
    (order_bananas, 5, "Ordered 5 Bananas..."),
    (order_cherries, 5, "Ordered 5 Cherries..."),
    (order_oranges, 5, "Ordered 5 Oranges..."),
]


@pytest.mark.parametrize(
    "activity_func, order_amount, expected_result", activity_test_data
)
def test_order_fruit(activity_func, order_amount, expected_result):
    activity_environment = ActivityEnvironment()

    result = activity_environment.run(activity_func, order_amount)

    assert result == expected_result
