from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

TASK_QUEUE = "tq-survey-replay2026"
AGGREGATOR_TASK_QUEUE = "tq-survey-aggregator"
AGGREGATOR_WORKFLOW_ID = "poll-aggregator-replay2026"


class SurveyResponse(str, Enum):
    YES = "yes"
    NO = "no"
    MAYBE = "maybe"


@dataclass
class SurveyResponseInput:
    user_id: str
    response: SurveyResponse
    comment: Optional[str] = None

    def __post_init__(self) -> None:
        # Coerce `response` back to the enum regardless of construction path.
        # Two shapes can arrive here:
        #   1. A SurveyResponse member (starter / workflow code passing the
        #      enum directly) -- no work needed.
        #   2. A raw value from the payload converter after a serialization
        #      round-trip. With `class SurveyResponse(str, Enum)` and Python
        #      3.12+'s stricter str-as-Sequence handling, Temporal's
        #      value_to_type walker sometimes decomposes the JSON string
        #      "yes" into a list of chars like ['y', 'e', 's'] before invoking
        #      this constructor. Reassemble in that case.
        if isinstance(self.response, SurveyResponse):
            return
        raw = self.response
        if isinstance(raw, list):
            raw = "".join(raw)
        self.response = SurveyResponse(raw)


@dataclass
class TallyResult:
    counts: Dict[str, int] = field(default_factory=dict)
    total: int = 0
    last_updated: Optional[str] = None
