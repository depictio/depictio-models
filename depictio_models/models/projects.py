from datetime import datetime
import os
import re
from typing import List, Optional
from pydantic import field_validator, model_validator
import hashlib
import json

from depictio_models.models.users import Permission
from depictio_models.models.workflows import Workflow
from depictio_models.models.base import MongoModel, convert_objectid_to_str
from depictio_models.config import DEPICTIO_CONTEXT


class Project(MongoModel):
    name: str
    data_management_platform_project_url: Optional[str] = None
    workflows: List[Workflow]
    yaml_config_path: str
    permissions: Permission
    is_public: bool = False
    hash: Optional[str] = None
    registration_time: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v:
            raise ValueError("Project name cannot be empty")
        return v

    @model_validator(mode="before")
    def compute_hash(cls, values: dict) -> dict:
        """
        Compute the hash of the project configuration.
        """
        # Compute the hash of the project configuration after removing all the "registration_time" fields in project and nested objects
        values.pop("registration_time", None)
        for workflow in values["workflows"]:
            workflow.pop("registration_time", None)
            for data_collection in workflow["data_collections"]:
                data_collection.pop("registration_time", None)

        hash_str = hashlib.md5(
            json.dumps(convert_objectid_to_str(values), sort_keys=True).encode()
        ).hexdigest()
        values["hash"] = hash_str
        return values

    @field_validator("yaml_config_path")
    @classmethod
    def validate_yaml_config_path(cls, v):
        if DEPICTIO_CONTEXT.lower() == "cli":
            # Check if looks like a valid path but do not check if it exists
            if not os.path.isabs(v):
                raise ValueError("Path must be absolute")
            return v
        else:
            if not v:
                raise ValueError("Path cannot be empty")
            return v

    @field_validator("data_management_platform_project_url")
    @classmethod
    def validate_data_management_platform_project_url(cls, v):
        # Check if looks like a valid URL
        if not re.match(r"https?://", v):
            raise ValueError("Invalid URL")
        return v
