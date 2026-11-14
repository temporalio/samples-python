"""Scripted chat client for the sample tests.

Built on ``temporalio.microsoft_agent_framework.testing``. ``scripted_plugin`` registers
one ``FakeChatClient`` under the ``"gpt-4o-mini"`` name the samples use, so the
sample Workflows run unchanged against the script and no API key is needed.
"""

from collections.abc import Callable, Sequence
from typing import Any

from temporalio.microsoft_agent_framework import MicrosoftAgentFrameworkPlugin
from temporalio.microsoft_agent_framework.testing import (
    FakeChatClient,
    ScriptEntry,
    fake_chat_client,
    function_call_response,
    text_response,
)

MODEL = "gpt-4o-mini"

__all__ = ["MODEL", "function_call_response", "scripted_plugin", "text_response"]


def scripted_plugin(
    responses: Sequence[ScriptEntry], **kwargs: Any
) -> tuple[MicrosoftAgentFrameworkPlugin, Callable[[], FakeChatClient]]:
    """Return a plugin whose ``gpt-4o-mini`` client replays ``responses``, and its factory.

    Each model call takes the next entry; the last one repeats. The factory
    hands out the same client every time, so call it after the run to read
    ``calls``, the requests the model received.
    """
    factory = fake_chat_client(responses)
    return MicrosoftAgentFrameworkPlugin(
        chat_clients={MODEL: factory}, **kwargs
    ), factory
