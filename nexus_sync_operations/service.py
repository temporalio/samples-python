import nexusrpc

from message_passing.introduction import Language
from message_passing.introduction.workflows import (
    GetLanguagesInput,
    SetLanguageInput,
    SetLanguageUsingActivityInput,
)


@nexusrpc.service
class GreetingService:
    get_languages: nexusrpc.Operation[GetLanguagesInput, list[Language]]
    get_language: nexusrpc.Operation[None, Language]
    set_language: nexusrpc.Operation[SetLanguageInput, Language]
    set_language_using_activity: nexusrpc.Operation[
        SetLanguageUsingActivityInput, Language
    ]
