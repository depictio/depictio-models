
from datetime import datetime
import re
from typing import List
from pydantic import BaseModel, field_validator

class TokenData(BaseModel):
    name: str
    access_token: str
    expire_datetime: str

    @field_validator("access_token")
    def validate_access_token(cls, v):
        if not v:
            raise ValueError("Access token cannot be empty")
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
    id: str
    groups: List[str]
    token: TokenData

class CLIConfig(BaseModel):
    api_base_url: str
    user: UserCLIConfig

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