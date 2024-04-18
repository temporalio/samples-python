"""Module defines export s3 activities convert exported workflow history file from proto to parquet format."""

import json
import uuid
from typing import List

import boto3
import pandas as pd
import temporalio.api.export.v1 as export
from dataobject import DataTransAndLandActivitiyInput, GetObjectKeysActivityInput
from google.protobuf.json_format import MessageToJson
from temporalio import activity


class ExportS3Activities:
    def __init__(self):
        # Make sure you have the AWS credentials set up
        self.s3 = boto3.client("s3")

    @activity.defn
    async def get_object_keys(
        self, activity_input: GetObjectKeysActivityInput
    ) -> List[str]:
        """Function that list objects by key."""
        response = self.s3.list_objects_v2(
            Bucket=activity_input.bucket, Prefix=activity_input.path
        )
        object_keys = []
        for obj in response.get("Contents", []):
            object_keys.append(obj["Key"])

        if len(object_keys) == 0:
            raise FileNotFoundError(
                f"No files found in {activity_input.bucket}/{activity_input.path}"
            )

        return object_keys

    @activity.defn
    async def data_trans_and_land(
        self, activity_input: DataTransAndLandActivitiyInput
    ) -> str:
        """Function that convert proto to parquet and save to S3."""
        key = activity_input.object_key
        data = await self.get_data_from_object_key(activity_input.export_s3_bucket, key)
        activity.logger.info("Convert proto to parquet for file: %s", key)
        parquet_data = await self.convert_proto_to_parquet_flatten(data)
        activity.logger.info("Finish transformation for file: %s", key)

        return await self.save_to_sink(
            parquet_data, activity_input.output_s3_bucket, activity_input.write_path
        )

    async def get_data_from_object_key(
        self, bucket_name: str, object_key: str
    ) -> export.WorkflowExecutions:
        """Function that get object by key."""
        v = export.WorkflowExecutions()
        try:
            data = self.s3.get_object(Bucket=bucket_name, Key=object_key)["Body"].read()
        except Exception as e:
            activity.logger.error(f"Error reading object: {e}")
            raise e

        v.ParseFromString(data)

        return v

    async def convert_proto_to_parquet_flatten(
        self, wfs: export.WorkflowExecutions
    ) -> pd.DataFrame:
        """Function that convert flatten proto data to parquet."""
        dfs = []
        for wf in wfs.items:
            start_attributes = wf.history.events[
                0
            ].workflow_execution_started_event_attributes
            histories = wf.history
            json_str = MessageToJson(histories)
            row = {
                "WorkflowID": start_attributes.workflow_id,
                "RunID": start_attributes.original_execution_run_id,
                "Histories": json.loads(json_str),
            }
            dfs.append(pd.DataFrame([row]))

        df = pd.concat(dfs, ignore_index=True)

        rows_flatten = []
        for _, row in df.iterrows():
            wf_histories_raw = row["Histories"]["events"]
            worfkow_id = row["WorkflowID"]
            run_id = row["RunID"]

            for history_event in wf_histories_raw:
                row_flatten = pd.json_normalize(history_event, sep="_")

                skip_name = ["payloads", "."]
                columns_to_drop = [
                    col
                    for col in row_flatten.columns
                    for skip in skip_name
                    if skip in col
                ]
                row_flatten.drop(columns_to_drop, axis=1, inplace=True)

                row_flatten.insert(0, "WorkflowId", worfkow_id)
                row_flatten.insert(1, "RunId", run_id)

                rows_flatten.append(row_flatten)

        df_flatten = pd.concat(rows_flatten, ignore_index=True)
        return df_flatten

    async def save_to_sink(
        self, data: pd.DataFrame, s3_bucket: str, write_path: str
    ) -> str:
        """Function that save object to s3 bucket."""
        write_bytes = data.to_parquet(None, compression="snappy", index=False)
        s3 = boto3.client("s3")
        uuid_name = uuid.uuid1()
        file_name = f"{uuid_name}.parquet"
        activity.logger.info("Writing to S3 bucket: %s", file_name)
        try:
            key = f"{write_path}/{file_name}"
            s3.put_object(Bucket=s3_bucket, Key=key, Body=write_bytes)
            return key
        except Exception as e:
            activity.logger.error(f"Error saving to sink: {e}")
            raise e
