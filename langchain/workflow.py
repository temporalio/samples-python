from dataclasses import dataclass
from datetime import timedelta
from typing import List

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import TranslateParams, translate_phrase

@workflow.defn
class LangChainChildWorkflow:
    @workflow.run
    async def run(self, params: TranslateParams) -> str:
        return await workflow.execute_activity(
            translate_phrase,
            params,
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        
@dataclass
class TranslateWorkflowParams:
    phrase: str
    languages: List[str]


@workflow.defn
class LangChainWorkflow:
    @workflow.run
    async def run(self, params: TranslateWorkflowParams) -> dict:
        result = {}
        result[params.languages[0]] = await workflow.execute_activity(
            translate_phrase,
            TranslateParams(params.phrase, params.languages[0]),
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        result[params.languages[1]] = await workflow.execute_activity(
            translate_phrase,
            TranslateParams(params.phrase, params.languages[1]),
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        result[params.languages[2]] = await workflow.execute_child_workflow(
            LangChainChildWorkflow.run,
            TranslateParams(params.phrase, params.languages[2]),
        )
        return result
        
