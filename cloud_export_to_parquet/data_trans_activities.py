import json
import uuid
from dataclasses import dataclass
from typing import List

import boto3
import pandas as pd
import temporalio.api.export.v1 as export
from google.protobuf.json_format import MessageToDict
from temporalio import activity


@dataclass
class GetObjectKeysActivityInput:
    bucket: str
    path: str


@dataclass
class DataTransAndLandActivityInput:
    export_s3_bucket: str
    object_key: str
    output_s3_bucket: str
    write_path: str


@activity.defn
def get_object_keys(activity_input: GetObjectKeysActivityInput) -> List[str]:
    """Function that list objects by key."""
    object_keys = []
    s3 = boto3.client("s3")
    response = s3.list_objects_v2(
        Bucket=activity_input.bucket, Prefix=activity_input.path
    )
    for obj in response.get("Contents", []):
        object_keys.append(obj["Key"])
    if len(object_keys) == 0:
        raise FileNotFoundError(
            f"No files found in {activity_input.bucket}/{activity_input.path}"
        )

    return object_keys


@activity.defn
def data_trans_and_land(activity_input: DataTransAndLandActivityInput) -> str:
    """Function that convert proto to parquet and save to S3."""
    key = activity_input.object_key
    data = get_data_from_object_key(activity_input.export_s3_bucket, key)
    activity.logger.info("Convert proto to parquet for file: %s", key)
    parquet_data = convert_proto_to_parquet_flatten(data)
    activity.logger.info("Finish transformation for file: %s", key)
    return save_to_sink(
        parquet_data, activity_input.output_s3_bucket, activity_input.write_path
    )


def get_data_from_object_key(
    bucket_name: str, object_key: str
) -> export.WorkflowExecutions:
    """Function that get object by key."""
    v = export.WorkflowExecutions()

    s3 = boto3.client("s3")
    try:
        data = s3.get_object(Bucket=bucket_name, Key=object_key)["Body"].read()
    except Exception as e:
        activity.logger.error(f"Error reading object: {e}")
        raise e
    v.ParseFromString(data)
    return v

def convert_proto_to_parquet_flatten(wfs: export.WorkflowExecutions) -> pd.DataFrame:
    """Function that converts flatten proto data to parquet and streams to s3."""
    rows = []
    for wf in wfs.items:
        start_attrs = wf.history.events[0].workflow_execution_started_event_attributes
        workflow_id = start_attrs.workflow_id
        run_id = start_attrs.original_execution_run_id
        for ev in wf.history.events:
            d = MessageToDict(ev, preserving_proto_field_name=False)
            d["WorkflowId"] = workflow_id
            d["RunId"] = run_id
            rows.append(d)
    if rows:
        df = pd.json_normalize(rows, sep="_")
    else:
        df = pd.DataFrame()
    if not df.empty:
        skip_tokens = ("payloads", ".")
        drop_cols = [c for c in df.columns if any(tok in c for tok in skip_tokens)]
        if drop_cols:
            df = df.drop(columns=drop_cols, errors="ignore")
    return df 

def save_to_sink(data: pd.DataFrame, s3_bucket: str, write_path: str) -> str:
    """Function that save object to s3 bucket."""
    write_bytes = data.to_parquet(None, compression="snappy", index=False)
    uuid_name = uuid.uuid1()
    file_name = f"{uuid_name}.parquet"
    activity.logger.info("Writing to S3 bucket: %s", file_name)

    s3 = boto3.client("s3")
    try:
        key = f"{write_path}/{file_name}"
        s3.put_object(Bucket=s3_bucket, Key=key, Body=write_bytes)
        return key
    except Exception as e:
        activity.logger.error(f"Error saving to sink: {e}")
        raise e
