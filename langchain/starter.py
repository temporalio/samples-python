from contextlib import asynccontextmanager
from pathlib import Path
from typing import List
from uuid import uuid4

import uvicorn
from activities import TranslateParams
from fastapi import FastAPI, HTTPException
from langchain_interceptor import LangChainContextPropagationInterceptor
from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from workflow import LangChainWorkflow, TranslateWorkflowParams


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Get repo root - 1 level deep from root

    repo_root = Path(__file__).resolve().parent.parent

    config_file = repo_root / "temporal.toml"

    
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    config["interceptors"] = [LangChainContextPropagationInterceptor()]
    
    app.state.temporal_client = await Client.connect(**config)
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
