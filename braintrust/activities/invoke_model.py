from temporalio import activity
from openai import AsyncOpenAI
import braintrust
from braintrust import wrap_openai
from typing import Optional, List, cast, Any, TypeVar, Generic
from typing_extensions import Annotated
from pydantic import BaseModel
from pydantic.functional_validators import BeforeValidator
from pydantic.functional_serializers import PlainSerializer

import importlib
import os

T = TypeVar("T", bound=BaseModel)


def _coerce_class(v: Any) -> type[Any]:
    """Pydantic validator: convert string path to class during deserialization."""
    if isinstance(v, str):
        mod_path, sep, qual = v.partition(":")
        if not sep:  # support "package.module.Class"
            mod_path, _, qual = v.rpartition(".")
        module = importlib.import_module(mod_path)
        obj = module
        for attr in qual.split("."):
            obj = getattr(obj, attr)
        return cast(type[Any], obj)
    elif isinstance(v, type):
        return v
    else:
        raise ValueError(f"Cannot coerce {v} to class")


def _dump_class(t: type[Any]) -> str:
    """Pydantic serializer: convert class to string path during serialization."""
    return f"{t.__module__}:{t.__qualname__}"


# Custom type that automatically handles class <-> string conversion in Pydantic serialization
ClassReference = Annotated[
    type[T],
    BeforeValidator(_coerce_class),
    PlainSerializer(_dump_class, return_type=str),
]


class InvokeModelRequest(BaseModel, Generic[T]):
    model: str
    instructions: str  # Fallback if Braintrust prompt unavailable
    input: str
    prompt_slug: Optional[str] = None  # Braintrust prompt slug (e.g., "report-synthesis")
    response_format: Optional[ClassReference[T]] = None
    tools: Optional[List[dict]] = None


class InvokeModelResponse(BaseModel, Generic[T]):
    # response_format records the type of the response model
    response_format: Optional[ClassReference[T]] = None
    response_model: Any

    @property
    def response(self) -> T:
        """Reconstruct the original response type if response_format was provided."""
        if self.response_format:
            model_cls = self.response_format
            return model_cls.model_validate(self.response_model)
        return self.response_model


@activity.defn
async def invoke_model(request: InvokeModelRequest[T]) -> InvokeModelResponse[T]:
    instructions = request.instructions

    # Load prompt from Braintrust if slug provided
    if request.prompt_slug:
        try:
            prompt = braintrust.load_prompt(
                project=os.environ.get("BRAINTRUST_PROJECT", "deep-research"),
                slug=request.prompt_slug,
            )
            # Extract system message content only
            # NOTE: Other params (temperature, max_tokens, model) are NOT used
            built = prompt.build()
            for msg in built.get("messages", []):
                if msg.get("role") == "system":
                    instructions = msg["content"]
                    activity.logger.info(
                        f"Loaded prompt '{request.prompt_slug}' from Braintrust"
                    )
                    break
        except Exception as e:
            # Log warning but continue with fallback
            activity.logger.warning(
                f"Failed to load prompt '{request.prompt_slug}': {e}. "
                "Using hardcoded fallback."
            )

    client = wrap_openai(AsyncOpenAI(max_retries=0))

    kwargs: dict[str, Any] = {
        "model": request.model,
        "instructions": instructions,
        "input": request.input,
    }

    if request.response_format:
        kwargs["text_format"] = request.response_format

    if request.tools:
        kwargs["tools"] = request.tools

    # Use responses API consistently
    resp = await client.responses.parse(**kwargs)

    if request.response_format:
        # Convert structured response to dict for managed serialization.
        # This allows us to reconstruct the original response type while maintaining type safety.
        parsed_model = cast(BaseModel, resp.output_parsed)
        return InvokeModelResponse(
            response_model=parsed_model.model_dump(),
            response_format=request.response_format,
        )
    else:
        return InvokeModelResponse(
            response_model=resp.output_text, response_format=None
        )
