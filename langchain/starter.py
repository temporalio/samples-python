from contextlib import asynccontextmanager
from typing import List
from uuid import uuid4

import uvicorn
from activities import TranslateParams
from fastapi import FastAPI, HTTPException
from temporalio.client import Client
from workflow import TranslateWorkflowParams
from langchain_interceptor import LangChainContextPropagationInterceptor
from workflow import LangChainWorkflow


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.temporal_client = await Client.connect("localhost:7233", interceptors=[LangChainContextPropagationInterceptor()])
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/translate")
async def translate(phrase: str, language1: str, language2: str, language3: str):
    languages = [language1, language2, language3]
    client = app.state.temporal_client
    try:
        result = await client.execute_workflow(
            LangChainWorkflow.run,
            TranslateWorkflowParams(phrase, languages),
            id=f"langchain-translation-{uuid4()}",
            task_queue="langchain-task-queue",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"translations": result}


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
