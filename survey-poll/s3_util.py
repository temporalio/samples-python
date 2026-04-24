"""S3 persistence for survey responses.

Responses are stored as one JSON object per user under an hour-partitioned
prefix so a dashboard or backfill job can list just the recent window instead
of the entire bucket.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.client import BaseClient

from models import SurveyResponseInput

_S3_CLIENT: Optional[BaseClient] = None


def _client() -> BaseClient:
    global _S3_CLIENT
    if _S3_CLIENT is None:
        _S3_CLIENT = boto3.client("s3")
    return _S3_CLIENT


def _bucket() -> str:
    bucket = os.environ.get("SURVEY_S3_BUCKET")
    if not bucket:
        raise RuntimeError("SURVEY_S3_BUCKET env var is required for S3 persistence")
    return bucket


def _key_for(user_id: str, now: datetime) -> str:
    return (
        f"survey-replay2026/responses/"
        f"{now:%Y}/{now:%m}/{now:%d}/{now:%H}/{user_id}.json"
    )


async def put_response(input: SurveyResponseInput) -> str:
    """Upload a single response to S3. Returns the object key."""
    now = datetime.now(tz=timezone.utc)
    key = _key_for(input.user_id, now)
    body = json.dumps(
        {
            "user_id": input.user_id,
            "response": input.response.value,
            "comment": input.comment,
            "timestamp": now.isoformat(),
        }
    )

    # boto3 is synchronous; offload to a thread so we don't block the event loop.
    await asyncio.to_thread(
        _client().put_object,
        Bucket=_bucket(),
        Key=key,
        Body=body,
        ContentType="application/json",
    )
    return key
