import os
import re
from typing import List, Optional
from pydantic import field_validator

from depictio_models.models.users import Permission
from depictio_models.models.workflows import Workflow
from depictio_models.models.base import MongoModel


class Project(MongoModel):
    name: str
    description: Optional[str] = None
    data_management_platform_project_url: Optional[str] = None
    workflows: List[Workflow]
    depictio_version: str
    yaml_config_path: str
    permissions: Permission

    @field_validator("depictio_version")
    @classmethod
    def validate_version(cls, v):
        # Using a simple regex pattern to validate semantic versioning
        pattern = r"^v\d+\.\d+\.\d+$"
        if not re.match(pattern, v):
            raise ValueError("Invalid version number, must be in format X.Y.Z where X, Y, Z are integers")
        return v
    
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
