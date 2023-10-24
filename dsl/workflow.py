from __future__ import annotations

import asyncio
import dataclasses
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional, Union

from temporalio import workflow


@dataclass
class DSLInput:
    root: Statement
    variables: Dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclass
class ActivityStatement:
    activity: ActivityInvocation


@dataclass
class ActivityInvocation:
    name: str
    arguments: List[str] = dataclasses.field(default_factory=list)
    result: Optional[str] = None


@dataclass
class SequenceStatement:
    sequence: Sequence


@dataclass
class Sequence:
    elements: List[Statement]


@dataclass
class ParallelStatement:
    parallel: Parallel


@dataclass
class Parallel:
    branches: List[Statement]


Statement = Union[ActivityStatement, SequenceStatement, ParallelStatement]


@workflow.defn
class DSLWorkflow:
    @workflow.run
    async def run(self, input: DSLInput) -> Dict[str, Any]:
        self.variables = dict(input.variables)
        workflow.logger.info("Running DSL workflow")
        await self.execute_statement(input.root)
        workflow.logger.info("DSL workflow completed")
        return self.variables

    async def execute_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, ActivityStatement):
            # Invoke activity loading arguments from variables and optionally
            # storing result as a variable
            result = await workflow.execute_activity(
                stmt.activity.name,
                args=[self.variables.get(arg, "") for arg in stmt.activity.arguments],
                start_to_close_timeout=timedelta(minutes=1),
            )
            if stmt.activity.result:
                self.variables[stmt.activity.result] = result
        elif isinstance(stmt, SequenceStatement):
            # Execute each statement in order
            for elem in stmt.sequence.elements:
                await self.execute_statement(elem)
        elif isinstance(stmt, ParallelStatement):
            # Execute all in parallel. Note, this will raise an exception when
            # the first activity fails and will not cancel the others. We could
            # store tasks and cancel if we wanted. In newer Python versions this
            # would use a TaskGroup instead.
            await asyncio.gather(
                *[self.execute_statement(branch) for branch in stmt.parallel.branches]
            )
