import asyncio
from typing import Optional

from temporalio import activity

from nexus_messaging.callerpattern.service import Language


@activity.defn
async def call_greeting_service(language: Language) -> Optional[str]:
    """Simulates a call to a remote greeting service. Returns None if unsupported."""
    greetings = {
        Language.ARABIC: "\u0645\u0631\u062d\u0628\u0627 \u0628\u0627\u0644\u0639\u0627\u0644\u0645",
        Language.CHINESE: "\u4f60\u597d\uff0c\u4e16\u754c",
        Language.ENGLISH: "Hello, world",
        Language.FRENCH: "Bonjour, monde",
        Language.HINDI: "\u0928\u092e\u0938\u094d\u0924\u0947 \u0926\u0941\u0928\u093f\u092f\u093e",
        Language.PORTUGUESE: "Ol\u00e1 mundo",
        Language.SPANISH: "Hola mundo",
    }
    await asyncio.sleep(0.2)
    return greetings.get(language)
