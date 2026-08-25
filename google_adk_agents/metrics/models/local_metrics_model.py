from collections.abc import AsyncGenerator

from google.adk.models import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

MODEL_NAME = "local-metrics-model"


class LocalMetricsModel(BaseLlm):
    @classmethod
    def supported_models(cls) -> list[str]:
        return [MODEL_NAME]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="Replay-safe metrics are ready.")],
            ),
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=8,
                candidates_token_count=5,
                total_token_count=13,
            ),
        )
