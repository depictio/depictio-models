from abc import ABC
from typing import Optional, List
from pydantic import validate_call
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

from depictio_models.models.cli import CLIConfig
from depictio_models.models.s3 import MinioConfig, PolarsStorageOptions
from depictio_models.logging import logger


class S3ProviderBase(ABC):
    def __init__(self, config: MinioConfig):
        self.config = config
        self.bucket_name = config.bucket
        self.endpoint_url = config.endpoint_url
        self.access_key = config.root_user
        self.secret_key = config.root_password
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    def check_s3_accessibility(self) -> bool:
        """
        Check only S3 storage accessibility without checking specific bucket.

        Returns:
            bool: True if S3 is accessible, False otherwise
        """
        try:
            self.s3_client.list_buckets()
            logger.info("S3 storage is accessible.")
            return True
        except (NoCredentialsError, PartialCredentialsError):
            logger.error("Invalid credentials for S3.")
            return False
        except Exception as e:
            logger.error(f"Error accessing S3: {e}")
            return False

    def check_bucket_accessibility(self) -> bool:
        """
        Check if the specific bucket is accessible.

        Returns:
            bool: True if bucket exists and is accessible, False otherwise
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket '{self.bucket_name}' is accessible.")
            return True
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                logger.error(f"Bucket '{self.bucket_name}' does not exist.")
            else:
                logger.error(
                    f"Bucket '{self.bucket_name}' is not accessible: {e.response['Error']['Message']}"
                )
            return False

    def check_write_policy(self) -> bool:
        """
        Check if write operations are possible in the bucket.

        Returns:
            bool: True if write is possible, False otherwise
        """
        try:
            test_key = ".depictio/write_test"
            self.s3_client.put_object(Bucket=self.bucket_name, Key=test_key, Body="test")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=test_key)
            logger.info("Write policy is correctly configured.")
            return True
        except ClientError as e:
            logger.error(f"Write policy check failed: {e.response['Error']['Message']}")
            return False

    def suggest_adjustments(self, checks: Optional[List[str]] = None) -> None:
        """
        Perform specified S3 checks and suggest adjustments.

        Args:
            checks: Optional list of checks to perform.
                    Options: ['s3', 'bucket', 'write']
        """
        if checks is None:
            checks = ["s3", "bucket", "write"]

        suggestions = []

        if "s3" in checks and not self.check_s3_accessibility():
            suggestions.append("Verify the endpoint URL, access key, and secret key.")

        if "bucket" in checks and not self.check_bucket_accessibility():
            suggestions.append(f"Ensure the bucket '{self.bucket_name}' exists and is accessible.")

        if "write" in checks and not self.check_write_policy():
            suggestions.append("Adjust bucket policies to allow write access for this client.")

        if suggestions:
            logger.error("Suggested Adjustments:")
            for suggestion in suggestions:
                logger.error(f"- {suggestion}")
            raise Exception("S3 storage is not correctly configured.")
        else:
            logger.info("No adjustments needed.")


class MinIOManager(S3ProviderBase):
    def __init__(self, config: MinioConfig):
        logger.info(f"Initializing MinIOManager with bucket '{config.bucket}'")
        super().__init__(config)


def S3_storage_checks(s3_config: MinioConfig, checks: Optional[List[str]] = None):
    """
    Flexible S3 storage checks.

    Args:
        s3_config: S3 configuration
        checks: Optional list of checks to perform.
                Options: ['s3', 'bucket', 'write']
    """
    logger.info("Checking S3 accessibility...")
    logger.info(f"S3 config: {s3_config}")
    minio_manager = MinIOManager(s3_config)
    logger.info("MinIOManager initialized.")
    minio_manager.suggest_adjustments(checks)


@validate_call
def turn_S3_config_into_polars_storage_options(cli_config: CLIConfig):
    """
    Convert S3 configuration into storage options for the client.
    """
    s3_config = cli_config.s3_storage
    return PolarsStorageOptions(
        endpoint_url=f"{s3_config.endpoint_url}:{s3_config.port}",
        aws_access_key_id=s3_config.root_user,
        aws_secret_access_key=s3_config.root_password,
    )
