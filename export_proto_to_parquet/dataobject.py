from dataclasses import dataclass


@dataclass
class GetObjectKeysActivityInput:
    bucket: str
    path: str


@dataclass
class DataTransAndLandActivitiyInput:
    export_s3_bucket: str
    object_key: str
    output_s3_bucket: str
    write_path: str


@dataclass
class ProtoToParquetWorkflowInput:
    num_delay_hour: int
    export_s3_bucket: str
    namespace: str
    output_s3_bucket: str
