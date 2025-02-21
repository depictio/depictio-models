import re
from pydantic import BaseModel, field_validator


class PolarsStorageOptions(BaseModel):
    endpoint_url: str
    aws_access_key_id: str
    aws_secret_access_key: str
    use_ssl: str = "false"
    signature_version: str = "s3v4"
    region: str = "us-east-1"
    AWS_ALLOW_HTTP: str = "true"
    AWS_S3_ALLOW_UNSAFE_RENAME: str = "true"

    @field_validator("endpoint_url")
    def validate_endpoint_url(cls, v):
        if not v:
            raise ValueError("Endpoint URL cannot be empty")
        if not re.match(r"^https?://[^/]+:\d+", v):
            raise ValueError("Invalid URL format : http://localhost:9000")
        return v

    @field_validator("aws_access_key_id")
    def validate_aws_access_key_id(cls, v):
        if not v:
            raise ValueError("AWS access key ID cannot be empty")
        return v

    @field_validator("aws_secret_access_key")
    def validate_aws_secret_access_key(cls, v):
        if not v:
            raise ValueError("AWS secret access key cannot be empty")
        return v

    @field_validator("use_ssl")
    def validate_use_ssl(cls, v):
        if not isinstance(v, str):
            raise ValueError("use_ssl must be a string")
        if v.lower() not in ["true", "false"]:
            raise ValueError("use_ssl must be 'true' or 'false'")
        return v

    @field_validator("signature_version")
    def validate_signature_version(cls, v):
        if not v:
            raise ValueError("Signature version cannot be empty")
        return v

    @field_validator("region")
    def validate_region(cls, v):
        if not v:
            raise ValueError("Region cannot be empty")
        return v

    @field_validator("AWS_ALLOW_HTTP")
    def validate_AWS_ALLOW_HTTP(cls, v):
        if not isinstance(v, str):
            raise ValueError("AWS_ALLOW_HTTP must be a string")
        if v.lower() not in ["true", "false"]:
            raise ValueError("AWS_ALLOW_HTTP must be 'true' or 'false'")
        return v

    @field_validator("AWS_S3_ALLOW_UNSAFE_RENAME")
    def validate_AWS_S3_ALLOW_UNSAFE_RENAME(cls, v):
        if not isinstance(v, str):
            raise ValueError("AWS_S3_ALLOW_UNSAFE_RENAME must be a string")
        if v.lower() not in ["true", "false"]:
            raise ValueError("AWS_S3_ALLOW_UNSAFE_RENAME must be 'true' or 'false'")
        return v


class MinIOS3Config(BaseModel):
    """Configuration model for MinIO S3 storage.

    This model defines the required configuration for connecting to a MinIO S3 server.
    The configuration includes connection details and credentials.
    """

    provider: str = "minio"  # Only MinIO is supported currently
    bucket: str  # Name of the bucket to use
    endpoint: str = "http://localhost"  # MinIO server endpoint URL
    port: int = 9000  # MinIO server port
    minio_root_user: str  # MinIO root username
    minio_root_password: str  # MinIO root password

    class Config:
        extra = "forbid"  # Reject any unexpected fields

    @field_validator("provider")
    def validate_provider(cls, v):
        if v.lower() != "minio":
            raise ValueError("Only MinIO is supported as a provider")
        return v

    @field_validator("port")
    def validate_port(cls, v):
        if not 0 < v < 65536:
            raise ValueError("Port number must be between 1 and 65535")
        return v

    @field_validator("endpoint")
    def validate_internal_endpoint(cls, v):
        if not v:
            raise ValueError("Endpoint cannot be empty")
        if not re.match(r"^https?://[^/]+", v):
            raise ValueError("Invalid URL format")
        return v

    @field_validator("bucket")
    def validate_bucket(cls, v):
        if not v:
            raise ValueError("Bucket name cannot be empty")
        # Could add more bucket name validation rules here if needed
        return v

    @field_validator("minio_root_user")
    def validate_root_user(cls, v):
        if not v:
            raise ValueError("Root user cannot be empty")
        return v

    @field_validator("minio_root_password")
    def validate_root_password(cls, v):
        if not v:
            raise ValueError("Root password cannot be empty")
        # Could add password strength validation if needed
        return v
