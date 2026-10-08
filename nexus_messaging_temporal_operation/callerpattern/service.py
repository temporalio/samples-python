"""
Nexus service definition for the caller (entity) pattern. Shared between the handler and
caller. The caller uses this to create a type-safe Nexus client; the handler implements
the operations.

Every operation includes a user_id so the handler knows which entity workflow to target.
"""

from dataclasses import dataclass
from enum import IntEnum

import nexusrpc


class Language(IntEnum):
    ARABIC = 1
    CHINESE = 2
    ENGLISH = 3
    FRENCH = 4
    HINDI = 5
    PORTUGUESE = 6
    SPANISH = 7


@dataclass
class GetLanguagesInput:
    include_unsupported: bool
    user_id: str


@dataclass
class GetLanguagesOutput:
    languages: list[Language]


@dataclass
class GetLanguageInput:
    user_id: str


@dataclass
class SetLanguageInput:
    language: Language
    user_id: str


@dataclass
class ApproveInput:
    name: str
    user_id: str


@dataclass
class ApproveOutput:
    pass


@nexusrpc.service
class NexusGreetingService:
    # Returns the languages supported by the greeting workflow.
    get_languages: nexusrpc.Operation[GetLanguagesInput, GetLanguagesOutput]
    # Returns the currently active language.
    get_language: nexusrpc.Operation[GetLanguageInput, Language]
    # Changes the active language, returning the previous one.
    set_language: nexusrpc.Operation[SetLanguageInput, Language]
    # Approves the workflow, allowing it to complete.
    approve: nexusrpc.Operation[ApproveInput, ApproveOutput]
