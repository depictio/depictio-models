import os
import re
import bleach
import html
from typing import List, Optional
from pydantic import field_validator

from depictio_models.models.users import Permission
from depictio_models.models.workflows import Workflow
from depictio_models.models.base import MongoModel
from depictio_models.logging import logger

class Project(MongoModel):
    name: str
    # description: Optional[Description] = None  # Store as a plain string in YAML
    # description: Optional[str] = None
    data_management_platform_project_url: Optional[str] = None
    workflows: List[Workflow]
    # depictio_version: str
    yaml_config_path: str
    permissions: Permission
    hash: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v:
            raise ValueError("Project name cannot be empty")
        return v
    
    @field_validator("hash")
    @classmethod
    def validate_hash(cls, v):
        if v:
            # hashlib.md5().encode().hexdigest() - 32 characters
            if len(v) != 32:
                raise ValueError("Invalid hash value, must be 32 characters long")
        return None


    # @field_validator("depictio_version")
    # @classmethod
    # def validate_version(cls, v):
    #     # Using a simple regex pattern to validate semantic versioning
    #     pattern = r"^v\d+\.\d+\.\d+$"
    #     if not re.match(pattern, v):
    #         raise ValueError("Invalid version number, must be in format X.Y.Z where X, Y, Z are integers")
    #     return v
    
    @field_validator("yaml_config_path")
    @classmethod
    def validate_yaml_config_path(cls, v):
        # Check if looks like a valid path but do not check if it exists
        if not os.path.isabs(v):
            raise ValueError("Path must be absolute")
        return v

    @field_validator("data_management_platform_project_url")
    @classmethod
    def validate_data_management_platform_project_url(cls, v):
        # Check if looks like a valid URL
        if not re.match(r"https?://", v):
            raise ValueError("Invalid URL")
        return v

    # @field_validator("description", mode="before")
    # def parse_description(cls, value):
    #     """
    #     Automatically convert a string into a Description object during validation.
    #     """
    #     logger.info(f"Value: {value}")
    #     logger.info(f"Type: {type(value)}")
    #     if not value:
    #         return None
    #     if isinstance(value, dict):
    #         return Description(description=value)
    #     if isinstance(value, Description):
    #         return value
    #     raise ValueError("Invalid type for description, expected str or Description.")


    # @field_validator("description")
    # def sanitize_description(cls, value):
    #     """
    #     Sanitizes the input to ensure it is plain text and neutralizes any code.
    #     Converts special characters to their HTML-safe equivalents to neutralize code execution.
    #     """
    #     # Convert special characters to HTML-safe equivalents
    #     neutralized = html.escape(value)

    #     # Sanitize the input to strip all HTML tags or attributes
    #     sanitized = bleach.clean(neutralized, tags=[], attributes={}, strip=True)

    #     if len(sanitized) > 1000:
    #         raise ValueError("Description must be less than 1000 characters.")

    #     return sanitized
    
    # @model_validator(mode="before")
    # @classmethod
    # def ensure_id(cls, values: dict) -> dict:
    #     """
    #     Ensures the `id` field uses the provided value or generates a new ObjectId.
    #     """
    #     if "_id" in values and values["_id"] is not None:
    #         # If `_id` is provided, validate and retain it
    #         values["_id"] = PyObjectId.validate(values["_id"])
    #     elif "id" in values and values["id"] is not None:
    #         # If `id` is provided, validate and retain it
    #         values["_id"] = PyObjectId.validate(values["id"])
    #     else:
    #         # Generate a new ObjectId if no valid ID is provided
    #         values["_id"] = PyObjectId()
    #     return values

    # class Config:
    #     allow_population_by_field_name = True
    #     json_encoders = {
    #         ObjectId: str,  # Convert ObjectId to string
    #         PyObjectId: str,
    #         datetime: lambda dt: dt.isoformat(),  # Convert datetime to ISO format
    #     }
