from datetime import datetime
import re
from typing import List
from pydantic import BaseModel, field_validator

from depictio_models.models.base import PyObjectId
from depictio_models.models.s3 import MinIOS3Config
from depictio_models.models.users import Group


class TokenData(BaseModel):
    name: str
    access_token: str
    expire_datetime: str

    class Config:
        extra = "forbid"  # Reject unexpected fields

    @field_validator("access_token")
    def validate_access_token(cls, v):
        if not v:
            raise ValueError("Access token cannot be empty")

        # Basic format check for JWT: should have three dot-separated parts
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Access token is not a valid JWT format (should contain three parts separated by dots)")

        # Validate that each part appears to be a Base64URL encoded string
        base64url_pattern = re.compile(r"^[A-Za-z0-9_-]+$")
        for part in parts:
            if not part or not base64url_pattern.fullmatch(part):
                raise ValueError("One of the JWT parts is not properly Base64URL-encoded")

        return v

    @field_validator("expire_datetime")
    def validate_expire_datetime(cls, v):
        if not v:
            raise ValueError("Expire datetime cannot be empty")
        else:
            try:
                if datetime.strptime(v, "%Y-%m-%d %H:%M:%S") < datetime.now():
                    raise ValueError("Token has expired")
            except ValueError:
                raise ValueError("Incorrect data format, should be YYYY-MM-DD HH:MM:SS")
        return v


class UserCLIConfig(BaseModel):
    email: str
    is_admin: bool
    id: PyObjectId
    groups: List[Group]
    token: TokenData

    class Config:
        extra = "forbid"  # Reject unexpected fields

    @field_validator("id")
    # turn the id into a string
    def validate_id(cls, v):
        return str(v)

    # @field_validator("groups")
    # # turn the groups into a list of strings (group ids)
    # def validate_groups(cls, v):
    #     return [{"id": str(group.id), "name": group.name} for group in v]

    @field_validator("email")
    def validate_email(cls, v):
        if not v:
            raise ValueError("Email cannot be empty")
        # check if the email is in the correct format
        # regex pattern from https://emailregex.com/
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v


class CLIConfig(BaseModel):
    api_base_url: str
    user: UserCLIConfig
    s3_storage: MinIOS3Config


    class Config:
        extra = "forbid"  # Reject unexpected fields

    @field_validator("api_base_url")
    def validate_api_base_url(cls, v):
        """
        Validates that the URL starts with http:// or https:// and,
        optionally, ends with a port number.
        """
        pattern = r"^https?:\/\/[^\/\s]+(?::\d+)?$"
        if not re.match(pattern, v):
            raise ValueError("Invalid URL format")
        return v
