import boto3
import pytest
from botocore.stub import Stubber


def test_get_object_keys_reads_all_pages(monkeypatch):
    pytest.importorskip("pandas")

    from cloud_export_to_parquet.data_trans_activities import (
        GetObjectKeysActivityInput,
        get_object_keys,
    )

    bucket = "export-bucket"
    prefix = "exports/"
    keys = [f"{prefix}{index:04d}" for index in range(1001)]
    s3 = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )
    monkeypatch.setattr(boto3, "client", lambda service_name: s3)

    params = {"Bucket": bucket, "Prefix": prefix}
    with Stubber(s3) as stubber:
        stubber.add_response(
            "list_objects_v2",
            {
                "IsTruncated": True,
                "NextContinuationToken": "next-page",
                "Contents": [{"Key": key} for key in keys[:-1]],
            },
            params,
        )
        stubber.add_response(
            "list_objects_v2",
            {"IsTruncated": False, "Contents": [{"Key": keys[-1]}]},
            {**params, "ContinuationToken": "next-page"},
        )

        assert get_object_keys(GetObjectKeysActivityInput(bucket, prefix)) == keys
        stubber.assert_no_pending_responses()
