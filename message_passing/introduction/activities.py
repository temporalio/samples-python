import asyncio
from typing import Optional

from temporalio import activity

from message_passing.introduction import Language


@activity.defn
async def call_greeting_service(to_language: Language) -> Optional[str]:
    """
    An Activity that simulates a call to a remote greeting service.
    The remote greeting service supports the full range of languages.
    """
    greetings = {
        Language.ARABIC: "مرحبا بالعالم",
        Language.CHINESE: "你好，世界",
        Language.ENGLISH: "Hello, world",
        Language.FRENCH: "Bonjour, monde",
        Language.HINDI: "नमस्ते दुनिया",
        Language.PORTUGUESE: "Olá mundo",
        Language.SPANISH: "¡Hola mundo",
    }
    await asyncio.sleep(0.2)  # Simulate a network call
    return greetings.get(to_language)
