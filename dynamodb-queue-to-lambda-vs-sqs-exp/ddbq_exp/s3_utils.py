"""
IMP: this code is just improvised for the sake of this experiment.

For a proper S3 client see clients-monorepo (at the time of writing I haven't created
 and S3 client yet, but I have clients in patatrack-monorepo - where this code was
 copied from -, hdmap-web/slackbot and map-cli).
"""

import io
import os
from typing import cast

import boto3
import botocore.session
import log_utils as logger
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    PartialCredentialsError,
    ProfileNotFound,
)
from mypy_boto3_s3.service_resource import Bucket, Object, S3ServiceResource

# Src: https://github.com/python/cpython/blob/3.11/Lib/concurrent/futures/thread.py#L142
MAX_CONCURRENT_THREADS = min(32, (os.cpu_count() or 1) + 4)


def does_exist_in_s3(
    bucket_name: str,
    key: str,
):
    aws_region_name = "eu-south-1"

    try:
        bc_session = botocore.session.get_session()
        _session = boto3.session.Session(
            botocore_session=bc_session, region_name=aws_region_name
        )
        s3_config = dict(use_accelerate_endpoint=False)
        # Note: when doing multi-threading do NOT share the S3 `resource`, but use and
        # share a low-level client instead, see:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/resources.html#multithreading-and-multiprocessing
        s3_resource: S3ServiceResource = _session.resource(
            "s3", config=get_default_botocore_config(s3=s3_config)
        )
    except (PartialCredentialsError, ProfileNotFound) as exc:
        raise Exception("BotoAuthError") from exc

    # To access the underlying low-level client:
    # s3_client: S3Client = s3_resource.meta.client

    bucket: Bucket = s3_resource.Bucket(bucket_name)
    obj: Object = bucket.Object(key)

    try:
        # `load` is an HTTP HEAD request.
        # It actually calls something like `self.s3_resource.meta.client.head_object(Bucket=bucket_name, Key=key)` that
        # actually returns some attributes like `ContentLength` and `Metadata`.
        obj.load()
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "404":
            return False
        raise
    return True


def upload_to_s3(
    bucket_name: str,
    key: str,
    content: str | bytes,
) -> None:
    aws_region_name = "eu-south-1"

    try:
        bc_session = botocore.session.get_session()
        _session = boto3.session.Session(
            botocore_session=bc_session, region_name=aws_region_name
        )
        s3_config = dict(use_accelerate_endpoint=False)
        # Note: when doing multi-threading do NOT share the S3 `resource`, but use and
        # share a low-level client instead, see:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/resources.html#multithreading-and-multiprocessing
        s3_resource: S3ServiceResource = _session.resource(
            "s3", config=get_default_botocore_config(s3=s3_config)
        )
    except (PartialCredentialsError, ProfileNotFound) as exc:
        raise Exception("BotoAuthError") from exc

    # To access the underlying low-level client:
    # s3_client: S3Client = s3_resource.meta.client

    bucket: Bucket = s3_resource.Bucket(bucket_name)
    obj: Object = bucket.Object(key)

    # Ensure content is in bytes, cast if not.
    if hasattr(content, "encode"):
        content = content.encode()
    content = cast(bytes, content)  # Typing cast.

    extra_args: dict[str, str | dict] = dict()
    extra_args["ContentType"] = "text/plain"

    logger.debug(f"Uploading content to: {obj.key}")
    with io.BytesIO(content) as bytes_in:
        obj.upload_fileobj(
            Fileobj=bytes_in,
            # ExtraArgs docs: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-uploading-files.html?highlight=extraargs#the-extraargs-parameter
            ExtraArgs=extra_args or None,
            # Callback docs: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-uploading-files.html?highlight=extraargs#the-callback-parameter
            # Callback=...
            Config=get_default_transfer_config(),
        )


def get_default_botocore_config(**kwargs) -> Config:
    # Boto3 config docs:
    #  - https://botocore.amazonaws.com/v1/documentation/api/latest/reference/config.html
    #  - https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html
    config = dict(
        # region_name=region_name,
        # signature_version="v4",
        # retries={"max_attempts": 10, "mode": "standard"},
        max_pool_connections=MAX_CONCURRENT_THREADS  # Default: 10
    )
    config.update(kwargs)
    return Config(**config)


def get_default_transfer_config(**kwargs) -> TransferConfig:
    # Boto3 transfer config:
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/customizations/s3.html#boto3.s3.transfer.S3Transfer.ALLOWED_UPLOAD_ARGS
    config = dict(
        # multipart_threshold=25 * KB,  # Default: 8 * MB.
        # multipart_chunksize=25 * KB,  # Default: 8 * MB.
        max_concurrency=MAX_CONCURRENT_THREADS,  # Default: 10
        # use_threads=True,  # Default: true.
    )
    config.update(kwargs)
    return TransferConfig(**config)
