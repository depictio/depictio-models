from datetime import datetime
import os
from typing import Dict, List, Optional
import bleach
import re
from bson import ObjectId
from pydantic import (
    BaseModel,
    Field,
    validator,
    root_validator,
)
from models.files import File
from models.users import Permission
from models.base import DirectoryPath, HashModel, MongoModel, PyObjectId
from models.data_collections import DataCollection
class WorkflowConfig(MongoModel):
    # id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    # parent_runs_location: List[DirectoryPath]
    # FIXME: Change parent_runs_location to a list of DirectoryPath
    parent_runs_location: List[str]
    workflow_version: Optional[str]
    config: Optional[Dict]
    runs_regex: Optional[str]

    # Update below to allow for multiple run locations and check that they exist
    @validator("parent_runs_location")
    def validate_run_location(cls, value):
        if not isinstance(value, list):
            raise ValueError("run_location must be a list")
        for location in value:
            if not os.path.exists(location):
                raise ValueError(f"The directory '{location}' does not exist.")
                # logger.warning(f"The directory '{location}' does not exist.")
            if not os.path.isdir(location):
                raise ValueError(f"'{location}' is not a directory.")
                # logger.warning(f"'{location}' is not a directory.")
            if not os.access(location, os.R_OK):
                raise ValueError(f"'{location}' is not readable.")
                # logger.warning(f"'{location}' is not readable.")
        return value

    @validator("runs_regex")
    def validate_regex(cls, v):
        try:
            re.compile(v)
            return v
        except re.error:
            raise ValueError("Invalid regex pattern")


class WorkflowRun(MongoModel):
    id: Optional[PyObjectId] = None
    # id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    workflow_id: PyObjectId
    run_tag: str
    files: List[File] = []
    workflow_config: WorkflowConfig
    run_location: DirectoryPath
    execution_time: datetime
    execution_profile: Optional[Dict]
    registration_time: datetime = datetime.now()


    @root_validator(pre=True)
    def set_default_id(cls, values):
        if values is None or "id" not in values or values["id"] is None:
            return values  # Ensure we don't proceed if values is None
        values["id"] = PyObjectId()
        return values

    @validator("files")
    def validate_files(cls, value):
        if not isinstance(value, list):
            raise ValueError("files must be a list")
        return value

    @validator("workflow_config")
    def validate_workflow_config(cls, value):
        if not isinstance(value, WorkflowConfig):
            raise ValueError("workflow_config must be a WorkflowConfig")
        return value

    @validator("execution_time", pre=True, always=True)
    def validate_creation_time(cls, value):
        if type(value) is not datetime:
            try:
                dt = datetime.fromisoformat(value)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ValueError("Invalid datetime format")
        else:
            return value.strftime("%Y-%m-%d %H:%M:%S")

    @validator("registration_time", pre=True, always=True)
    def validate_registration_time(cls, value):
        if type(value) is not datetime:
            try:
                dt = datetime.fromisoformat(value)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ValueError("Invalid datetime format")
        else:
            return value.strftime("%Y-%m-%d %H:%M:%S")


class WorkflowSystem(BaseModel):
    workflow_language: str
    engine_version: Optional[str]
    workflow_engine: Optional[str]

    @validator("workflow_engine")
    def validate_workflow_engine_value(cls, value):
        allowed_values = [
            "snakemake",
            "nextflow",
            "toil",
            "cwltool",
            "arvados",
            "streamflow",
        ]
        if value not in allowed_values:
            raise ValueError(f"workflow_engine must be one of {allowed_values}")
        return value

    @validator("workflow_language")
    def validate_workflow_language_value(cls, value):
        allowed_values = [
            "snakemake",
            "nextflow",
            "CWL",
            "galaxy",
            "smk",
            "nf",
        ]
        if value not in allowed_values:
            raise ValueError(f"workflow_language must be one of {allowed_values}")
        return value


class Workflow(MongoModel):
    # id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    # id: Optional[PyObjectId] = Field(default=None, alias='_id')
    name: str
    engine: str
    workflow_tag: str
    # workflow_engine: WorkflowSystem
    description: str
    repository_url: Optional[str]
    data_collections: List[DataCollection]
    runs: Optional[Dict[str, WorkflowRun]] = dict()
    config: WorkflowConfig
    registration_time: datetime = datetime.now()
    # data_collection_ids: Optional[List[str]] = []
    permissions: Optional[Permission] = {"owners": [], "viewers": []}
    hash: Optional[str] = None  # Change this to expect a string


    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: lambda oid: str(oid),  # or `str` for simplicity
        }




    @root_validator(pre=True)
    def compute_and_assign_hash(cls, values):
        # Copy the values to avoid mutating the input directly
        values_copy = values.copy()
        # Remove the hash field to avoid including it in the hash computation
        values_copy.pop('hash', None)
        # Compute the hash of the values
        computed_hash = HashModel.compute_hash(values_copy)
        # Assign the computed hash directly as a string
        values['hash'] = computed_hash
        return values


    def __eq__(self, other):
        if isinstance(other, Workflow):
            return all(getattr(self, field) == getattr(other, field) for field in self.__fields__.keys() if field not in ["id", "registration_time"])
        return NotImplemented

    @validator("name", pre=True, always=True)
    def validate_name(cls, value):
        if not value:
            raise ValueError("name is required")
        return value

    @validator("engine", pre=True, always=True)
    def validate_engine(cls, value):
        if not value:
            raise ValueError("engine is required")
        return value

    @validator("repository_url", pre=True, always=True)
    def validate_repository(cls, value):
        if not re.match(r"^(https?|git)://", value):
            raise ValueError("Invalid repository URL")
        return value

    # @validator("id", pre=True, always=True)
    # def validate_id(cls, id):
    #     if not id:
    #         raise ValueError("id is required")
    #     return id

    @root_validator(pre=True)
    def set_workflow_tag(cls, values):
        # print(f"Received values: {values}")

        engine = values.get("engine")
        name = values.get("name")
        if engine and name:
            values["workflow_tag"] = f"{engine}/{name}"
        return values



    @validator("description", pre=True, always=True)
    def sanitize_description(cls, value):
        # Strip any HTML tags and attributes
        sanitized = bleach.clean(value, tags=[], attributes={}, strip=True)
        # Ensure it's not overly long
        max_length = 500  # Set as per your needs
        return sanitized[:max_length]

    @validator("data_collections")
    def validate_data_collections(cls, value):
        if not isinstance(value, list):
            raise ValueError("data_collections must be a list")
        return value

    @validator("runs")
    def validate_runs(cls, value):
        if not isinstance(value, dict):
            raise ValueError("runs must be a dictionary")
        return value

    # @validator("permissions", always=True)
    # def set_default_permissions(cls, value, values):
    #     if not value:
    #         # Here we initialize the owners to include the creator by default.
    #         # This assumes that `creator_id` or a similar field exists in the `Workflow` model.
    #         workflow_creator = values.get("creator_id")
    #         if workflow_creator:
    #             return Permission(owners={workflow_creator}, viewers=set())
    #     return value
