import pytest
from pydantic_ai.models import infer_model


def test_documented_live_model_is_available(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("PYDANTIC_AI_GATEWAY_API_KEY", "test-key")
    monkeypatch.setenv(
        "PYDANTIC_AI_GATEWAY_BASE_URL", "https://gateway.example.invalid"
    )
    model = infer_model("gateway/openai:gpt-5.2")
    assert model.model_name == "gpt-5.2"
