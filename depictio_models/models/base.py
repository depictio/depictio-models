from datetime import datetime
import hashlib
import html
import os
from pathlib import Path, PosixPath
from typing import Optional
import bleach
from bson import ObjectId
from pydantic import BaseModel, Field, GetCoreSchemaHandler, model_validator, field_validator
import re

import json

from pydantic_core import core_schema

from depictio_models.logging import logger


def convert_objectid_to_str(item):
    if isinstance(item, dict):
        return {key: convert_objectid_to_str(value) for key, value in item.items()}
    elif isinstance(item, list):
        return [convert_objectid_to_str(elem) for elem in item]
    elif isinstance(item, ObjectId):
        return str(item)
    elif isinstance(item, datetime):
        return item.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return item


# Custom JSON encoder
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, PyObjectId):
            return str(obj)
        return super().default(obj)


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source: type, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        """
        Defines the core schema for PyObjectId.
        """
        return core_schema.no_info_after_validator_function(cls.validate, core_schema.union_schema([core_schema.str_schema(), core_schema.is_instance_schema(ObjectId)]))

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError(f"Invalid ObjectId: {v}")


# class Description(BaseModel):
#     description: str



class MongoModel(BaseModel):
    id: PyObjectId = Field(default=PyObjectId())  # Handles MongoDB `_id`
    # id: PyObjectId = Field(default=PyObjectId(), alias="_id")  # Handles MongoDB `_id`
    description : Optional[str] = None

    @field_validator("description")
    def sanitize_description(cls, value):
        """
        Sanitizes the input to ensure it is plain text and neutralizes any code.
        Converts special characters to their HTML-safe equivalents to neutralize code execution.
        Ensures no HTML tags or JavaScript can persist in the sanitized description.
        """
        # If value is a Description instance, extract the string
        # if isinstance(value, Description):
        #     value = value.description

        logger.info(f"DEBUG - Description: {value}")

        if not value:
            logger.info("No description provided.")
            return None

        # Step 1: Convert special characters to their HTML-safe equivalents
        neutralized = html.escape(value)

        # Step 2: Use bleach to remove all HTML tags and attributes
        sanitized = bleach.clean(neutralized, tags=[], attributes={}, strip=True)

        # Step 3: Check if HTML tags were successfully removed
        if any(char in sanitized for char in ("<", ">", "&lt;", "&gt;")):
            raise ValueError("Description contains disallowed HTML content.")

        # Step 4: Enforce a maximum character length
        if len(sanitized) > 1000:
            raise ValueError("Description must be less than 1000 characters.")

        return sanitized

    class Config:
        extra = "forbid"
        # allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: lambda oid: str(oid),
            PosixPath: lambda path: str(path),
        }

    @model_validator(mode="before")
    @classmethod
    def ensure_id(cls, values: dict) -> dict:
        """
        Ensures the `_id` field uses the provided value or generates a new ObjectId.
        """
        # If values is not a dict, skip processing and return as-is
        if not isinstance(values, dict):
            return values

        logger.info(f"Ensuring ID: {values}")
        if "_id" in values and values["_id"] is not None:
            # If `_id` is provided, validate and retain it
            values["id"] = PyObjectId.validate(values["_id"])
        elif "id" in values and values["id"] is not None:
            # If `id` is provided, validate and retain it
            values["id"] = PyObjectId.validate(values["id"])
        else:
            # Generate a new ObjectId if no valid ID is provided
            values["id"] = PyObjectId()
        return values

    @classmethod
    def from_mongo(cls, data: dict):
        """We must convert _id into "id"."""
        if not data:
            return data

        # Helper function to convert nested documents
        def convert_ids(document):
            if isinstance(document, list):
                return [convert_ids(item) for item in document]
            if isinstance(document, dict):
                document = {key: convert_ids(value) for key, value in document.items()}
                id = document.pop("_id", None)
                if id:
                    document["id"] = id
            return document

        data = convert_ids(data)
        return cls(**data)

    def mongo(self, **kwargs):
        exclude_unset = kwargs.pop("exclude_unset", False)
        by_alias = kwargs.pop("by_alias", True)

        parsed = self.model_dump(
            exclude_unset=exclude_unset,
            by_alias=by_alias,
            **kwargs,
        )

        # Mongo uses `_id` as default key. We should stick to that as well.
        if "_id" not in parsed and "id" in parsed:
            parsed["_id"] = parsed.pop("id")

        # Convert PosixPath to str
        for key, value in parsed.items():
            if isinstance(value, Path):
                parsed[key] = str(value)

        return parsed




class DirectoryPath(BaseModel):
    path: str

    @field_validator("path", mode="before")
    def validate_path(cls, v):
        # Ensure the path is valid
        if not isinstance(v, (str, Path)):
            raise ValueError(f"Invalid type for path: {type(v)}. Must be a string or Path.")
        v = Path(v)  # Ensure it's a Path object
        if not v.exists():
            raise ValueError(f"The directory '{v}' does not exist.")
        if not v.is_dir():
            raise ValueError(f"'{v}' is not a directory.")
        if not os.access(v, os.R_OK):
            raise ValueError(f"'{v}' is not readable.")
        return str(v)  # Return validated Path object


class HashModel(BaseModel):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> str:
        if not re.match(r"^[a-fA-F0-9]{64}$", value):
            raise ValueError("Invalid hash")
        return value

    @classmethod
    def compute_hash(cls, value: dict) -> str:
        hash_str = json.dumps(value, sort_keys=True).encode("utf-8")
        return hashlib.sha256(hash_str).hexdigest()
