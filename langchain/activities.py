from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from temporalio import activity

from langchain.prompts import ChatPromptTemplate


@dataclass
class TranslateParams:
    phrase: str
    language: str


@activity.defn
async def translate_phrase(params: TranslateParams) -> str:
    # LangChain setup
    template = """You are a helpful assistant who translates between languages.
    Translate the following phrase into the specified language: {phrase}
    Language: {language}"""
    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            ("human", "Translate"),
        ]
    )
    chain = chat_prompt | ChatOpenAI()
    # Use the asynchronous invoke method
    return (
        dict(
            await chain.ainvoke({"phrase": params.phrase, "language": params.language})
        ).get("content")
        or ""
    )
