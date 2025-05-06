from typing import Union, Optional, List, Literal, Iterable, TypedDict

import httpx
from openai import AsyncOpenAI, NotGiven, NOT_GIVEN
from openai._types import Headers, Query, Body
from openai.types import ResponsesModel, Metadata, Reasoning
from openai.types.responses import ResponseInputParam, ResponseIncludable, ResponseTextConfigParam, \
    response_create_params, ToolParam, Response

from temporalio import activity

from openai_agents.adapters.heartbeat_decorator import auto_heartbeater


class OpenAIActivityInput(TypedDict, total=False):
    input: Union[str, ResponseInputParam]
    model: ResponsesModel
    include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN
    instructions: Optional[str] | NotGiven = NOT_GIVEN
    max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN
    metadata: Optional[Metadata] | NotGiven = NOT_GIVEN
    parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN
    previous_response_id: Optional[str] | NotGiven = NOT_GIVEN
    reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN
    service_tier: Optional[Literal["auto", "default", "flex"]] | NotGiven = NOT_GIVEN
    store: Optional[bool] | NotGiven = NOT_GIVEN
    stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN
    temperature: Optional[float] | NotGiven = NOT_GIVEN
    text: ResponseTextConfigParam | NotGiven = NOT_GIVEN
    tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN
    tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN
    top_p: Optional[float] | NotGiven = NOT_GIVEN
    truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN
    user: str | NotGiven = NOT_GIVEN
    extra_headers: Headers | None = None
    extra_query: Query | None = None
    extra_body: Body | None = None
    timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN


@activity.defn
@auto_heartbeater
async def invoke_open_ai_model(input: OpenAIActivityInput) -> Response:
    client = AsyncOpenAI()
    return await client.responses.create(**input)
