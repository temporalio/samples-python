"""
Nexus service definition for the on-demand pattern. Every operation includes a userId
so the caller controls which workflow instance is targeted. This also exposes a
run_from_remote operation that starts a new GreetingWorkflow.
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
class RunFromRemoteInput:
    user_id: str


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
class NexusRemoteGreetingService:
    # Starts a new GreetingWorkflow with the given workflow ID (asynchronous).
    run_from_remote: nexusrpc.Operation[RunFromRemoteInput, str]
    # Returns the languages supported by the specified workflow.
    get_languages: nexusrpc.Operation[GetLanguagesInput, GetLanguagesOutput]
    # Returns the currently active language of the specified workflow.
    get_language: nexusrpc.Operation[GetLanguageInput, Language]
    # Changes the active language on the specified workflow, returning the previous one.
    set_language: nexusrpc.Operation[SetLanguageInput, Language]
    # Approves the specified workflow, allowing it to complete.
    approve: nexusrpc.Operation[ApproveInput, ApproveOutput]
