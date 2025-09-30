"""
This module defines a Nexus service that exposes three operations.

It is used by the nexus service handler to validate that the operation handlers implement the
correct input and output types, and by the caller workflow to create a type-safe client. It does not
contain the implementation of the operations; see nexus_sync_operations.handler.service_handler for
that.
"""

import nexusrpc

from message_passing.introduction import Language
from message_passing.introduction.workflows import GetLanguagesInput, SetLanguageInput


@nexusrpc.service
class GreetingService:
    get_languages: nexusrpc.Operation[GetLanguagesInput, list[Language]]
    get_language: nexusrpc.Operation[None, Language]
    set_language: nexusrpc.Operation[SetLanguageInput, Language]
