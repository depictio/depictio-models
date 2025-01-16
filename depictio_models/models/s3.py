from datetime import datetime
import re
from typing import List, Optional
from pydantic import BaseModel, field_validator

from depictio_models.models.base import PyObjectId


class MinIOS3Config(BaseModel):
    provider: str = "minio"
    bucket: str
    # region: str
    endpoint: str = "http://localhost"
    port: int = 9000
    minio_root_user: str
    minio_root_password: str

    class Config:
        extra = "forbid"  # Reject unexpected fields

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
        return v

    # @field_validator("region")
    # def validate_region(cls, v):
    #     if not v:
    #         raise ValueError("Region cannot be empty")
    #     return v
    
    @field_validator("minio_root_user")
    def validate_root_user(cls, v):
        if not v:
            raise ValueError("Root user cannot be empty")
        return v
    
    @field_validator("minio_root_password")
    def validate_root_password(cls, v):
        if not v:
            raise ValueError("Root password cannot be empty")
        return v
    
    @field_validator("endpoint")
    def validate_internal_endpoint(cls, v):
        if not v:
            raise ValueError("Endpoint cannot be empty")
        if not re.match(r"^https?://[^/]+", v):
            raise ValueError("Invalid URL format")
        return v