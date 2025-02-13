from datetime import datetime
import os
from pathlib import Path
from typing import Dict, List, Optional
import re
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)
from depictio_models.models.files import File
from depictio_models.models.base import DirectoryPath, MongoModel, PyObjectId
from depictio_models.models.data_collections import DataCollection
from depictio_models.logging import logger


DEPICTIO_CONTEXT = os.getenv("DEPICTIO_CONTEXT")
logger.info(f"DEPICTIO_CONTEXT: {DEPICTIO_CONTEXT}")


class WorkflowDataLocation(MongoModel):
    structure: str
    locations: List[str]
    runs_regex: Optional[str] = None

    @field_validator("structure", mode="before")
    def validate_mode(cls, value):
        if value not in ["flat", "sequencing-runs"]:
            raise ValueError("structure must be either 'flat' or 'sequencing-runs'")
        return value

    @field_validator("locations", mode="after")
    def validate_and_recast_parent_runs_location(cls, value):
        if DEPICTIO_CONTEXT.lower() == "cli":
            # Recast to List[DirectoryPath] and validate

            env_var_pattern = re.compile(r"\{([A-Z0-9_]+)\}")

            expanded_paths = []
            for location in value:
                matches = env_var_pattern.findall(location)
                for match in matches:
                    env_value = os.environ.get(match)
                    logger.debug(f"Original path: {location}")
                    logger.debug(f"Expanded path: {location.replace(f'{{{match}}}', env_value)}")

                    if not env_value:
                        raise ValueError(f"Environment variable '{match}' is not set for path '{location}'.")
                    # Replace the placeholder with the actual value
                    location = location.replace(f"{{{match}}}", env_value)
                expanded_paths.append(location)

            # Validate the expanded paths if in CLI context
            return [DirectoryPath(path=Path(location)).path for location in expanded_paths]
        else:
            return value

    @model_validator(mode="before")
    def validate_regex(cls, values):
        # only if mode is 'sequencing-runs' - check mode first
        if values["structure"] == "sequencing-runs":
            logger.warning("DEPICTIO CONTEXT: %s", DEPICTIO_CONTEXT)
            logger.warning(f"Values: {values}")
            if not values["runs_regex"]:
                raise ValueError("runs_regex is required when mode is 'sequencing-runs'")
            # just check if the regex is valid
            try:
                re.compile(values["runs_regex"])
                return values
            except re.error:
                raise ValueError("Invalid runs_regex pattern")


class WorkflowConfig(MongoModel):
    version: Optional[str] = None
    workflow_parameters: Optional[Dict] = None


class WorkflowRunScan(BaseModel):
    stats: Dict[str, int]
    files_id: Dict[str, List[PyObjectId]]
    scan_time: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class WorkflowRun(MongoModel):
    workflow_id: PyObjectId
    run_tag: str
    files_id: List[PyObjectId] = []
    workflow_config_id: PyObjectId
    run_location: str
    creation_time: str
    last_modification_time: str
    # execution_profile: Optional[Dict]
    # generate default value for registration_time as current time and format as string
    registration_time: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_hash: str = None
    scan_results: Optional[List[WorkflowRunScan]] = []

    # @field_validator("workflow_config_id", mode="before")
    # def validate_workflow_config(cls, value):
    #     # if not isinstance(value, PyObjectId):
    #     #     raise ValueError("workflow_config_id must be a PyObjectId")
    #     return value

    @field_validator("run_location", mode="after")
    def validate_and_recast_parent_runs_location(cls, value):
        if DEPICTIO_CONTEXT == "CLI":
            # Recast to List[DirectoryPath] and validate

            env_var_pattern = re.compile(r"\{([A-Z0-9_]+)\}")

            expanded_paths = []
            location = value
            matches = env_var_pattern.findall(location)
            for match in matches:
                env_value = os.environ.get(match)
                logger.debug(f"Original path: {location}")
                logger.debug(f"Expanded path: {location.replace(f'{{{match}}}', env_value)}")

                if not env_value:
                    raise ValueError(f"Environment variable '{match}' is not set for path '{location}'.")
                # Replace the placeholder with the actual value
                location = location.replace(f"{{{match}}}", env_value)
            expanded_paths.append(location)

            # Validate the expanded paths if in CLI context
            return DirectoryPath(path=Path(location)).path
        else:
            return value

    @field_validator("run_hash", mode="before")
    def validate_hash(cls, value):
        # tolerate empty hash or hash of length 64
        if len(value) == 0 or len(value) == 64:
            return value

    # @model_validator(mode="before")
    # def set_default_id(cls, values):
    #     if values is None or "id" not in values or values["id"] is None:
    #         return values  # Ensure we don't proceed if values is None
    #     values["id"] = PyObjectId()
    #     return values

    @field_validator("files_id", mode="before")
    def validate_files(cls, value):
        if not isinstance(value, list):
            raise ValueError("files must be a list")
        # if not all(isinstance(file, PyObjectId) for file in value):
        #     raise ValueError("files must be a list of PyObjectId")
        return value

    @field_validator("workflow_config_id", mode="before")
    def validate_workflow_config(cls, value):
        if isinstance(value, PyObjectId):
            return value
        if isinstance(value, str):
            return PyObjectId(value)
        # if not isinstance(value, PyObjectId):
        #     raise ValueError("workflow_config_id must be a PyObjectId")
        return value

    @field_validator("creation_time", mode="before")
    def validate_creation_time(cls, value):
        # check if compliant with %Y-%m-%d %H:%M:%S" format
        if type(value) is not datetime:
            try:
                dt = datetime.fromisoformat(value)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ValueError("Invalid datetime format")

    @field_validator("last_modification_time", mode="before")
    def validate_last_modification_time(cls, value):
        # check if compliant with %Y-%m-%d %H:%M:%S" format
        if type(value) is not datetime:
            try:
                dt = datetime.fromisoformat(value)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ValueError("Invalid datetime format")

    @field_validator("registration_time", mode="before")
    def validate_registration_time(cls, value):
        # check if compliant with %Y-%m-%d %H:%M:%S" format
        if type(value) is not datetime:
            try:
                dt = datetime.fromisoformat(value)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ValueError("Invalid datetime format")


class WorkflowEngine(BaseModel):
    name: str
    version: Optional[str] = None

    class Config:
        extra = "forbid"  # Reject unexpected fields

    @field_validator("name", mode="before")
    def validate_workflow_engine_value(cls, value):
        allowed_values = [
            "snakemake",
            "nextflow",
            "toil",
            "cwltool",
            "arvados",
            "streamflow",
            "galaxy",
            "airflow",
            "dagster",
            "python",
            "shell",
            "r",
            "julia",
            "matlab",
            "perl",
            "java",
            "c",
            "c++",
            "go",
            "rust",
        ]
        if value not in allowed_values:
            raise ValueError(f"workflow_engine must be one of {allowed_values}")
        return value


class WorkflowCatalog(BaseModel):
    name: Optional[str]
    url: Optional[str]

    class Config:
        extra = "forbid"  # Reject unexpected fields

    @field_validator("url", mode="before")
    def validate_workflow_catalog_url(cls, value):
        if not re.match(r"^(https?|git)://", value):
            raise ValueError("Invalid URL")
        return value

    @field_validator("name", mode="before")
    def validate_workflow_catalog_name(cls, value):
        if value not in ["workflowhub", "nf-core", "smk-wf-catalog"]:
            raise ValueError("Invalid workflow catalog name")


class Workflow(MongoModel):
    name: str
    engine: WorkflowEngine
    version: Optional[str] = None
    catalog: Optional[WorkflowCatalog] = None
    workflow_tag: Optional[str] = None
    # description: Optional[Description] = None
    repository_url: Optional[str]
    data_collections: List[DataCollection]
    runs: Optional[Dict[str, WorkflowRun]] = dict()
    config: Optional[WorkflowConfig] = Field(default_factory=WorkflowConfig)
    data_location: WorkflowDataLocation
    registration_time: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @field_validator("version", mode="before")
    def validate_version(cls, value):
        if not value:
            return None
        if not isinstance(value, str):
            raise ValueError("version must be a string")
        return value

    # @field_validator("description", mode="before")
    # def parse_description(cls, value):
    #     """
    #     Automatically convert a string into a Description object during validation.
    #     """
    #     logger.info(f"Value: {value}")
    #     logger.info(f"Type: {type(value)}")
    #     if not value:
    #         return None
    #     # if isinstance(value, dict):
    #     #     return Description(**value)
    #     if isinstance(value, str):
    #         return Description(description=value)
    #     if isinstance(value, Description):
    #         return value
    #     raise ValueError("Invalid type for description, expected str or Description.")

    @model_validator(mode="before")
    @classmethod
    def generate_workflow_tag(cls, values):
        engine = values.get("engine")
        name = values.get("name")
        catalog = values.get("catalog")
        logger.debug(f"Engine: {engine}, Name: {name}, Catalog: {catalog}")
        values["workflow_tag"] = f"{engine.get('name')}/{name}"
        if catalog:
            catalog_name = catalog.get("name")
            if catalog_name == "nf-core":
                values["workflow_tag"] = f"{catalog_name}/{name}"
        return values

    # @model_validator(mode="before")
    # def compute_and_assign_hash(cls, values):
    #     # Copy the values to avoid mutating the input directly
    #     values_copy = values.copy()
    #     # Remove the hash field to avoid including it in the hash computation
    #     values_copy.pop("hash", None)
    #     # Compute the hash of the values
    #     computed_hash = HashModel.compute_hash(values_copy)
    #     # Assign the computed hash directly as a string
    #     values["hash"] = computed_hash
    #     return values

    def __eq__(self, other):
        if isinstance(other, Workflow):
            return all(getattr(self, field) == getattr(other, field) for field in self.model_fields.keys() if field not in ["id", "registration_time"])
        return NotImplemented

    @field_validator("name", mode="before")
    def validate_name(cls, value):
        if not value:
            raise ValueError("name is required")
        return value

    @field_validator("engine", mode="before")
    def validate_engine(cls, value):
        if not value:
            raise ValueError("engine is required")
        return value

    @field_validator("repository_url", mode="before")
    def validate_repository(cls, value):
        if not re.match(r"^(https?|git)://", value):
            raise ValueError("Invalid repository URL")
        return value

    # @field_validator("id", mode="before")
    # def validate_id(cls, id):
    #     if not id:
    #         raise ValueError("id is required")
    #     return id

    @model_validator(mode="before")
    def set_workflow_tag(cls, values):
        # print(f"Received values: {values}")

        engine = values.get("engine")
        name = values.get("name")
        if engine and name:
            values["workflow_tag"] = f"{engine}/{name}"
        return values

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

    @field_validator("data_collections", mode="before")
    def validate_data_collections(cls, value):
        if not isinstance(value, list):
            raise ValueError("data_collections must be a list")
        return value

    @field_validator("runs", mode="before")
    def validate_runs(cls, value):
        if not isinstance(value, dict):
            raise ValueError("runs must be a dictionary")
        return value

    # @field_validator("permissions", mode="before")
    # def set_default_permissions(cls, value, values):
    #     if not value:
    #         # Here we initialize the owners to include the creator by default.
    #         # This assumes that `creator_id` or a similar field exists in the `Workflow` model.
    #         workflow_creator = values.get("creator_id")
    #         if workflow_creator:
    #             return Permission(owners={workflow_creator}, viewers=set())
    #     return value
