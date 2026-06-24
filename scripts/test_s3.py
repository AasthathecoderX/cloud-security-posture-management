"""Create and verify a disposable S3 bucket in LocalStack."""

import os

import boto3
from botocore.exceptions import ClientError

BUCKET_NAME = "cspm-phase-zero-smoke-test"


def main() -> None:
    endpoint = os.getenv("LOCALSTACK_ENDPOINT", "http://localstack:4566")
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )

    try:
        client.create_bucket(Bucket=BUCKET_NAME)
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code")
        if code not in {"BucketAlreadyExists", "BucketAlreadyOwnedByYou"}:
            raise

    bucket_names = {bucket["Name"] for bucket in client.list_buckets()["Buckets"]}
    if BUCKET_NAME not in bucket_names:
        raise RuntimeError(f"LocalStack did not return expected bucket: {BUCKET_NAME}")

    print(f"LocalStack S3 smoke test passed: {BUCKET_NAME}")


if __name__ == "__main__":
    main()
