import asyncio
import os

from temporalio import activity

import s3_util
from models import AGGREGATOR_WORKFLOW_ID, SurveyResponseInput
from workflows import PollAggregatorWorkflow

HEARTBEAT_INTERVAL_SECONDS = 5.0


@activity.defn
async def record_response(input: SurveyResponseInput) -> str:
    activity.logger.info(
        "record_response: user=%s response=%s", input.user_id, input.response
    )

    # The real side effect: durable audit log in S3. Temporal's activity retry
    # policy covers transient failures.
    key = await s3_util.put_response(input)
    activity.logger.info("record_response: wrote s3://.../%s", key)

    # Optional saturation delay for the scaling demo. Default 0 keeps the real
    # activity fast; set SURVEY_DURATION_SECONDS=150 to reproduce the
    # max_concurrent_activities=1 saturation behavior used by load_starter.py.
    duration_s = float(os.environ.get("SURVEY_DURATION_SECONDS") or "0")
    if duration_s > 0:
        info = activity.info()
        elapsed = float(info.heartbeat_details[0]) if info.heartbeat_details else 0.0
        if elapsed > 0:
            activity.logger.info("Resuming at %.1fs / %.1fs", elapsed, duration_s)
        while elapsed < duration_s:
            activity.heartbeat(elapsed)
            remaining = duration_s - elapsed
            step = min(HEARTBEAT_INTERVAL_SECONDS, remaining)
            await asyncio.sleep(step)
            elapsed += step

    # Notify the live-tally aggregator. No try/except here: a failure raises
    # out of the activity, Temporal applies the retry policy, and the whole
    # activity replays. The S3 PUT above is idempotent on user_id (same key),
    # so retry is safe.
    client = activity.client()
    handle = client.get_workflow_handle(AGGREGATOR_WORKFLOW_ID)
    await handle.signal(PollAggregatorWorkflow.submit_vote, input.response)

    print(
        f"[survey] user={input.user_id} response={input.response.value} "
        f"comment={input.comment!r} key={key}",
        flush=True,
    )
    return f"recorded user={input.user_id} response={input.response.value}"
