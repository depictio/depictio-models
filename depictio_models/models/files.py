from datetime import datetime
import os
from typing import Dict, List, Optional
from pydantic import (
    BaseModel,
    Field,
    FilePath,
    field_validator,
    model_validator,
)
from depictio_models.models.data_collections import DataCollection, WildcardRegexBase
from depictio_models.models.users import Permission
from depictio_models.models.base import MongoModel, PyObjectId
from depictio_models.logging import logger
from depictio_models.config import DEPICTIO_CONTEXT


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
    file_location: FilePath
    filename: str
    creation_time: str
    modification_time: str
    run_id: Optional[PyObjectId] = None
    data_collection_id: PyObjectId
    registration_time: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_hash: str
    filesize: int
    permissions: Permission

    # id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    # id: Optional[PyObjectId] = None
    # S3_location: Optional[str] = None
    # S3_key_hash: Optional[str] = None
    # trackId: Optional[str] = None

    # file_hash: Optional[str] = None
    # wildcards: Optional[List[WildcardRegex]]

    @field_validator("filename")
    def validate_filename(cls, v):
        if not v:
            raise ValueError("Filename cannot be empty")
        return v

    @field_validator("filesize")
    def validate_size(cls, v):
        if v < 0:
            raise ValueError("File size cannot be negative")
        if v == 0:
            raise ValueError("File size cannot be zero")
        return v

    @field_validator("file_hash")
    def validate_hash(cls, v):
        if not v:
            raise ValueError("Hash cannot be empty")
        if len(v) != 64:
            raise ValueError("Invalid hash value, must be 32 characters long")
        return v

    # @model_validator(mode="before")
    # def set_default_id(cls, values):
    #     if values is None or "id" not in values or values["id"] is None:
    #         return values  # Ensure we don't proceed if values is None
    #     values["id"] = PyObjectId()
    #     return values

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
        if DEPICTIO_CONTEXT.lower() == "cli":
            if not os.path.exists(value):
                raise ValueError(f"The file '{value}' does not exist.")
            if not os.path.isfile(value):
                raise ValueError(f"'{value}' is not a file.")
            if not os.access(value, os.R_OK):
                raise ValueError(f"'{value}' is not readable.")
            return value
        else:
            if not value:
                raise ValueError("File location cannot be empty")
            return value

    # TODO: Implement file hashing to ensure file integrity
    # @field_validator("file_hash")
    # def validate_file_hash(cls, value):
    #     if value is not None:
    #         if not isinstance(value, str):
    #             raise ValueError("file_hash must be a string")
    #     return value


class FileScanResult(BaseModel):
    file: File
    scan_result: Dict[str, str]
    scan_time: str

    class Config:
        extra = "forbid"
        allow_population_by_field_name = False

    @field_validator("scan_result")
    def validate_scan_result(cls, value):
        if not isinstance(value, dict):
            raise ValueError("Scan result must be a dictionary")

        # value must contain following keys: "result", "reason"
        if "result" not in value:
            raise ValueError("Scan result must contain 'result' key")
        if "reason" not in value:
            raise ValueError("Scan result must contain 'reason' key")
        if value["result"] not in ["success", "failure"]:
            raise ValueError("Scan result must be one of ['success', 'failure']")
        if value["reason"] not in ["added", "skipped", "updated", "failed"]:
            raise ValueError("Scan reason must be one of ['added', 'skipped', 'updated', 'failed']")
        return value

    @field_validator("scan_time", mode="before")
    def validate_modification_time(cls, value):
        if type(value) is not datetime:
            try:
                dt = datetime.fromisoformat(value)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ValueError("Invalid datetime format")
        else:
            return value.strftime("%Y-%m-%d %H:%M:%S")
