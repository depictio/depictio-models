from datetime import datetime
import os
from typing import List, Optional
from pydantic import (
    Field,
    FilePath,
    field_validator,
    model_validator,
)
from depictio_models.models.data_collections import DataCollection, WildcardRegexBase
from depictio_models.models.users import Permission
from depictio_models.models.base import MongoModel, PyObjectId


class WildcardRegex(WildcardRegexBase):
    value: str


# class FileBase(MongoModel):
#     file_location: FilePath
#     filename: str
#     creation_time: datetime
#     modification_time: datetime
#     run_id: PyObjectId
#     data_collection_id: PyObjectId
#     registration_time: datetime = datetime.now()
# file_hash: Optional[str] = None


class File(MongoModel):
    # id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    # id: Optional[PyObjectId] = None
    # S3_location: Optional[str] = None
    # S3_key_hash: Optional[str] = None
    # trackId: Optional[str] = None
    file_location: FilePath
    filename: str
    creation_time: datetime
    modification_time: datetime
    run_id: PyObjectId
    data_collection_id: PyObjectId
    registration_time: datetime = datetime.now()
    file_hash: str
    # file_hash: Optional[str] = None
    # wildcards: Optional[List[WildcardRegex]]


    @field_validator("filename")
    def validate_filename(cls, v):
        if not v:
            raise ValueError("Filename cannot be empty")
        return v

    @field_validator("file_hash")
    def validate_hash(cls, v):
        if not v:
            raise ValueError("Hash cannot be empty")
        if len(v) != 64:
            raise ValueError("Invalid hash value, must be 32 characters long")
        return v

    @model_validator(mode="before")
    def set_default_id(cls, values):
        if values is None or "id" not in values or values["id"] is None:
            return values  # Ensure we don't proceed if values is None
        values["id"] = PyObjectId()
        return values

    @field_validator("creation_time", mode="before")
    def validate_creation_time(cls, value):
        if type(value) is not datetime:
            try:
                dt = datetime.fromisoformat(value)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ValueError("Invalid datetime format")
        else:
            return value.strftime("%Y-%m-%d %H:%M:%S")

    @field_validator("modification_time", mode="before")
    def validate_modification_time(cls, value):
        if type(value) is not datetime:
            try:
                dt = datetime.fromisoformat(value)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ValueError("Invalid datetime format")
        else:
            return value.strftime("%Y-%m-%d %H:%M:%S")

    @field_validator("file_location")
    def validate_location(cls, value):
        if not os.path.exists(value):
            raise ValueError(f"The file '{value}' does not exist.")
        if not os.path.isfile(value):
            raise ValueError(f"'{value}' is not a file.")
        if not os.access(value, os.R_OK):
            raise ValueError(f"'{value}' is not readable.")
        return value

    # TODO: Implement file hashing to ensure file integrity
    # @field_validator("file_hash")
    # def validate_file_hash(cls, value):
    #     if value is not None:
    #         if not isinstance(value, str):
    #             raise ValueError("file_hash must be a string")
    #     return value
