"""
This module defines a Nexus service that exposes synchronous operations for query, update, signal,
and signal-with-start operations.

It is used by the nexus service handler to validate that the operation handlers implement the
correct input and output types, and by the caller workflow to create a type-safe client. It does not
contain the implementation of the operations; see nexus_sync_operations.handler.service_handler for
that.
"""

import nexusrpc

from message_passing.introduction import Language
from message_passing.introduction.workflows import (
    ApproveInput,
    GetLanguagesInput,
    SetLanguageInput,
)


@nexusrpc.service
class GreetingService:
    # Query operations
    get_languages: nexusrpc.Operation[GetLanguagesInput, list[Language]]
    get_language: nexusrpc.Operation[None, Language]
    
    # Update operations
    set_language: nexusrpc.Operation[SetLanguageInput, Language]  # async update with activity
    set_language_sync: nexusrpc.Operation[SetLanguageInput, Language]  # synchronous update
    
    # Signal operations
    approve: nexusrpc.Operation[ApproveInput, None]  # signal
    approve_with_start: nexusrpc.Operation[ApproveInput, None]  # signal-with-start
