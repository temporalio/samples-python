import asyncio
import os

from temporalio import activity

import s3_util
from models import SurveyResponseInput

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

    print(
        f"[survey] user={input.user_id} response={input.response.value} "
        f"comment={input.comment!r} key={key}",
        flush=True,
    )
    return f"recorded user={input.user_id} response={input.response.value}"
