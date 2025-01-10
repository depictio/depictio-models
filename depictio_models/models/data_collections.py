from typing import List, Optional, Union
import bleach
import re
from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from depictio_models.models.base import MongoModel, PyObjectId
from depictio_models.models.data_collections_types.jbrowse import DCJBrowse2Config
from depictio_models.models.data_collections_types.table import DCTableConfig


class WildcardRegexBase(BaseModel):
    name: str
    wildcard_regex: str

    @field_validator("wildcard_regex")
    def validate_files_regex(cls, v):
        try:
            re.compile(v)
            return v
        except re.error:
            raise ValueError("Invalid regex pattern")


class Regex(BaseModel):
    pattern: str
    type: str
    wildcards: Optional[List[WildcardRegexBase]] = None

    @field_validator("pattern")
    def validate_files_regex(cls, v):
        try:
            re.compile(v)
            return v
        except re.error:
            raise ValueError("Invalid regex pattern")

    @field_validator("type")
    def validate_type(cls, v):
        allowed_values = ["file-based", "path-based"]
        if v.lower() not in allowed_values:
            raise ValueError(f"type must be one of {allowed_values}")
        return v


class TableJoinConfig(BaseModel):
    on_columns: List[str]
    how: Optional[str]
    with_dc: List[str]
    # lsuffix: str
    # rsuffix: str

    @field_validator("how")
    def validate_join_how(cls, v):
        allowed_values = ["inner", "outer", "left", "right"]
        if v.lower() not in allowed_values:
            raise ValueError(f"join_how must be one of {allowed_values}")
        return v


class DataCollectionConfig(MongoModel):
    type: str
    metatype: Optional[str] = None
    regex: Regex
    dc_specific_properties: Union[DCTableConfig, DCJBrowse2Config]
    join: Optional[TableJoinConfig] = None

    @field_validator("type")
    def validate_type(cls, v):
        allowed_values = ["table", "jbrowse2"]
        if v.lower() not in allowed_values:
            raise ValueError(f"type must be one of {allowed_values}")
        return v

    # @field_validator("dc_specific_properties", mode="before")
    # def set_correct_type(cls, v, values):
    #     if "type" in values:
    #         if values["type"].lower() == "table":
    #             return DCTableConfig(**v)
    #         elif values["type"].lower() == "jbrowse2":
    #             return DCJBrowse2Config(**v)
    #     raise ValueError("Unsupported type")


class DataCollection(MongoModel):
    # id: PyObjectId = Field(default_factory=None, alias="_id")
    data_collection_tag: str
    description: str = None
    config: DataCollectionConfig
    

    # class Config:
    #     arbitrary_types_allowed = True
    #     json_encoders = {
    #         ObjectId: lambda oid: str(oid),  # or `str` for simplicity
    #     }

    @field_validator("description", mode="before")
    def sanitize_description(cls, value):
        # Strip any HTML tags and attributes
        sanitized = bleach.clean(value, tags=[], attributes={}, strip=True)
        return sanitized

    def __eq__(self, other):
        if isinstance(other, DataCollection):
            return all(getattr(self, field) == getattr(other, field) for field in self.__fields__.keys() if field not in ["id", "registration_time"])
        return NotImplemented
