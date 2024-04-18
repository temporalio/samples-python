"""Module defines workflows convert exported workflow history file from proto to parquet format."""

from datetime import timedelta

from dataobject import ProtoToParquetWorkflowInput
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from export_proto_to_parquet.data_trans_activities import (
        DataTransAndLandActivitiyInput,
        ExportS3Activities,
        GetObjectKeysActivityInput,
    )


@workflow.defn
class ProtoToParquet:
    """Proto to parquet workflow."""

    @workflow.run
    async def run(self, workflow_input: ProtoToParquetWorkflowInput) -> str:
        """Run proto to parquet workflow."""
        retry_policy = RetryPolicy(
            maximum_attempts=10, maximum_interval=timedelta(seconds=5)
        )

        # Read from export S3 bucket and given at least 2 hour delay to ensure the file has been uploaded
        read_time = workflow.now() - timedelta(hours=workflow_input.num_delay_hour)
        common_path = f"{workflow_input.namespace}/{read_time.year}/{read_time.month:02}/{read_time.day:02}/{read_time.hour:02}/00"
        path = f"temporal-workflow-history/export/{common_path}"
        get_object_keys_input = GetObjectKeysActivityInput(
            workflow_input.export_s3_bucket, path
        )

        # Read Input File
        object_keys_output = await workflow.execute_activity_method(
            ExportS3Activities.get_object_keys,
            get_object_keys_input,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy,
        )

        write_path = f"temporal-workflow-history/parquet/{common_path}"

        try:
            # Could spin up multiple threads to process files in parallel
            for key in object_keys_output:
                data_trans_and_land_input = DataTransAndLandActivitiyInput(
                    workflow_input.export_s3_bucket,
                    key,
                    workflow_input.output_s3_bucket,
                    write_path,
                )
                # Convert proto to parquet and save to S3
                await workflow.execute_activity_method(
                    ExportS3Activities.data_trans_and_land,
                    data_trans_and_land_input,
                    start_to_close_timeout=timedelta(minutes=10),
                    retry_policy=retry_policy,
                )
        except ActivityError as output_err:
            workflow.logger.error(f"Data transformation failed: {output_err}")
            raise output_err

        return write_path
