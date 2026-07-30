import signal
import threading

import boto3
from moto.server import ThreadedMotoServer

from external_storage.worker import S3_ACCESS_KEY, S3_BUCKET, S3_ENDPOINT, S3_SECRET_KEY


def main() -> None:
    server = ThreadedMotoServer(port=5000)
    server.start()
    print(f"Mock S3 server running at {S3_ENDPOINT}")

    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name="us-east-1",
    )
    s3.create_bucket(Bucket=S3_BUCKET)
    print(f"Bucket '{S3_BUCKET}' created. Press ctrl+c to stop.")

    try:
        # signal.pause() is Unix-only; use Event on Windows
        if hasattr(signal, "pause"):
            signal.pause()
        else:
            threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        print("Mock S3 server stopped.")


if __name__ == "__main__":
    main()
