from __future__ import annotations

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from datetime import timedelta
    from idlelib.query import Query
    from typing import Union, Optional, List, Literal, Iterable, Callable, Any
    from wsgiref.headers import Headers
    from agents.function_schema import function_schema
    from agents.models.openai_provider import DEFAULT_MODEL
    from openai_agents.adapters.model_activity import OpenAIActivityInput, invoke_open_ai_model
    from agents import ModelProvider, Model, OpenAIResponsesModel, Tool, RunContextWrapper, FunctionTool
    import httpx
    from fastapi import Body
    from openai import NotGiven, NOT_GIVEN, AsyncStream, AsyncOpenAI
    from openai.types import ResponsesModel, Metadata, Reasoning
    from openai.types.responses import ResponseInputParam, ResponseIncludable, ResponseTextConfigParam, \
        response_create_params, ToolParam, Response, ResponseStreamEvent


def monkey_patch_open_ai_client_create(client: AsyncOpenAI) -> AsyncOpenAI:
    async def open_ai_client_create(self, *,
                                    input: Union[str, ResponseInputParam],
                                    model: ResponsesModel,
                                    include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN,
                                    instructions: Optional[str] | NotGiven = NOT_GIVEN,
                                    max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN,
                                    metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
                                    parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN,
                                    previous_response_id: Optional[str] | NotGiven = NOT_GIVEN,
                                    reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN,
                                    service_tier: Optional[Literal["auto", "default", "flex"]] | NotGiven = NOT_GIVEN,
                                    store: Optional[bool] | NotGiven = NOT_GIVEN,
                                    stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
                                    temperature: Optional[float] | NotGiven = NOT_GIVEN,
                                    text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
                                    tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN,
                                    tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
                                    top_p: Optional[float] | NotGiven = NOT_GIVEN,
                                    truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN,
                                    user: str | NotGiven = NOT_GIVEN, extra_headers: Headers | None = None,
                                    extra_query: Query | None = None, extra_body: Body | None = None,
                                    timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN) -> Response | \
                                                                                                     AsyncStream[
                                                                                                         ResponseStreamEvent]:
        def get_summary(input: Any) -> str:
            ### Activity summary shown in the UI
            try:
                max_size = 100
                if isinstance(input, str):
                    return input[:max_size]
                elif isinstance(input, list):
                    return input[-1].get("content", "")[:max_size]
                elif isinstance(input, dict):
                    return input.get("content", "")[:max_size]
            except Exception as e:
                print(f"Error getting summary: {e}")
            return ""

        activity_input = OpenAIActivityInput(input=input, model=model, include=include, instructions=instructions,
                                             max_output_tokens=max_output_tokens, metadata=metadata,
                                             parallel_tool_calls=parallel_tool_calls,
                                             previous_response_id=previous_response_id,
                                             reasoning=reasoning, service_tier=service_tier, store=store, stream=stream,
                                             temperature=temperature, text=text, tool_choice=tool_choice, tools=tools,
                                             top_p=top_p, truncation=truncation, user=user, extra_headers=extra_headers,
                                             extra_query=extra_query, extra_body=extra_body, timeout=timeout)

        return await workflow.execute_activity(
            invoke_open_ai_model, activity_input,
            start_to_close_timeout=timedelta(seconds=60),
            heartbeat_timeout=timedelta(seconds=5),
            summary=get_summary(input)
        )

    client.responses.create = open_ai_client_create.__get__(client.responses,
                                                            type(client.responses))  # Bind to instance
    return client


class ModelStubProvider(ModelProvider):
    def get_model(self, model_name: str | None) -> Model:
        if model_name is None:
            model_name = DEFAULT_MODEL
        client = AsyncOpenAI()
        return OpenAIResponsesModel(model_name, monkey_patch_open_ai_client_create(client))


def activity_as_tool(activity: Callable[..., Any]) -> Tool:
    async def run_activity(ctx: RunContextWrapper[Any], input: str) -> Any:
        return str(await workflow.execute_activity(
            activity,
            input,
            start_to_close_timeout=timedelta(seconds=10),
        ))

    schema = function_schema(activity)
    return FunctionTool(
        name=schema.name,
        description=schema.description or "",
        params_json_schema=schema.params_json_schema,
        on_invoke_tool=run_activity,
        strict_json_schema=True,
    )
