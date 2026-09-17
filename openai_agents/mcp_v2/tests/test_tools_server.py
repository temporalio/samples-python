from unittest.mock import Mock, patch

from tools_server import add, get_current_weather, get_secret_word


def test_add() -> None:
    assert add(7, 22) == 29


@patch("tools_server.random.choice", return_value="banana")
def test_get_secret_word(choice: Mock) -> None:
    assert get_secret_word() == "banana"
    choice.assert_called_once_with(["apple", "banana", "cherry"])


@patch("tools_server.requests.get")
def test_get_current_weather(get: Mock) -> None:
    get.return_value.text = "Sunny"

    assert get_current_weather("Tokyo") == "Sunny"
    get.assert_called_once_with("https://wttr.in/Tokyo")
