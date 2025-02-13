import os
from pathlib import Path
from typing import List, Optional, Union
import bleach
import re
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)

from depictio_models.models.base import MongoModel, PyObjectId
from depictio_models.models.data_collections_types.jbrowse import DCJBrowse2Config
from depictio_models.models.data_collections_types.table import DCTableConfig

from depictio_models.logging import logger

DEPICTIO_CONTEXT = os.getenv("DEPICTIO_CONTEXT")
logger.info(f"DEPICTIO_CONTEXT: {DEPICTIO_CONTEXT}")


class WildcardRegexBase(BaseModel):
    name: str
    wildcard_regex: str

    class Config:
        extra = "forbid"  # Reject unexpected fields

    @field_validator("wildcard_regex")
    def validate_files_regex(cls, v):
        try:
            re.compile(v)
            return v
        except re.error:
            raise ValueError("Invalid regex pattern")


class Regex(BaseModel):
    pattern: str
    # type: str
    wildcards: Optional[List[WildcardRegexBase]] = None

    class Config:
        extra = "forbid"  # Reject unexpected fields

    @field_validator("pattern")
    def validate_files_regex(cls, v):
        try:
            re.compile(v)
            return v
        except re.error:
            raise ValueError("Invalid regex pattern")

    # @field_validator("type")
    # def validate_type(cls, v):
    #     allowed_values = ["file-based", "path-based"]
    #     if v.lower() not in allowed_values:
    #         raise ValueError(f"type must be one of {allowed_values}")
    #     return v


class ScanRecursive(BaseModel):
    regex_config: Regex
    max_depth: Optional[int] = None
    ignore: Optional[List[str]] = None

    class Config:
        extra = "forbid"


class ScanSingle(BaseModel):
    filename: str

    class Config:
        extra = "forbid"

    @field_validator("filename")
    def validate_filename(cls, v):
        # validate filename & check if it exists
        if not Path(v).exists():
            raise ValueError(f"File {v} does not exist")
        return v


class Scan(BaseModel):
    mode: str
    scan_parameters: Union[ScanRecursive, ScanSingle]

    @field_validator("mode")
    def validate_mode(cls, v):
        allowed_values = ["recursive", "single"]
        if v.lower() not in allowed_values:
            raise ValueError(f"mode must be one of {allowed_values}")
        return v
    
    @model_validator(mode="before")
    def validate_join(cls, values):
        type_value = values.get("mode").lower()  # normalize to lowercase for comparison
        if type_value == "recursive":
            values["scan_parameters"] = ScanRecursive(**values["scan_parameters"])
        elif type_value == "single":
            values["scan_parameters"] = ScanSingle(**values["scan_parameters"])
        return values


class TableJoinConfig(BaseModel):
    on_columns: List[str]
    how: Optional[str]
    with_dc: List[str]
    # lsuffix: str
    # rsuffix: str

    class Config:
        extra = "forbid"  # Reject unexpected fields

    @field_validator("how")
    def validate_join_how(cls, v):
        allowed_values = ["inner", "outer", "left", "right"]
        if v.lower() not in allowed_values:
            raise ValueError(f"join_how must be one of {allowed_values}")
        return v


class DataCollectionConfig(MongoModel):
    type: str
    metatype: Optional[str] = None
    scan: Scan
    dc_specific_properties: Union[DCTableConfig, DCJBrowse2Config]
    join: Optional[TableJoinConfig] = None

    @field_validator("type", mode="before")
    def validate_type(cls, v):
        allowed_values = ["table", "jbrowse2"]
        lower_v = v.lower()
        if lower_v not in allowed_values:
            raise ValueError(f"type must be one of {allowed_values}")
        return lower_v  # return the normalized lowercase value

    @model_validator(mode="before")
    def validate_join(cls, values):
        type_value = values.get("type").lower()  # normalize to lowercase for comparison
        if type_value == "table":
            values["dc_specific_properties"] = DCTableConfig(**values["dc_specific_properties"])
        elif type_value == "jbrowse2":
            values["dc_specific_properties"] = DCJBrowse2Config(**values["dc_specific_properties"])
        return values


class DataCollection(MongoModel):
    data_collection_tag: str
    # description: Optional[Description] = None
    config: DataCollectionConfig


    def __eq__(self, other):
        if isinstance(other, DataCollection):
            return all(getattr(self, field) == getattr(other, field) for field in self.model_fields.keys() if field not in ["id", "registration_time"])
        return NotImplemented
    
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

