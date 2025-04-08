from datetime import datetime
import hashlib
import html
import os
from pathlib import Path
from typing import Optional
import bleach
from bson import ObjectId
from pydantic import (
    BaseModel,
    Field,
    GetCoreSchemaHandler,
    field_serializer,
    model_validator,
    field_validator,
    ConfigDict,
)
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
    elif isinstance(item, Path):
        return str(item)
    elif isinstance(item, BaseModel):
        return item.model_dump_json(exclude_unset=True, by_alias=True)
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
    def __get_pydantic_core_schema__(
        cls, source: type, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """
        Defines the core schema for PyObjectId.
        """
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.union_schema(
                [core_schema.str_schema(), core_schema.is_instance_schema(ObjectId)]
            ),
        )

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        if isinstance(v, PyObjectId):
            return ObjectId(str(v))
        raise ValueError(f"Invalid ObjectId: {v}")


# class Description(BaseModel):
#     description: str


# class MongoModelWithoutMainId(BaseModel):

#     @classmethod
#     def from_mongo(cls, data: Dict[str, Any]) -> "MongoModelWithoutMainId":
#         """
#         Convert MongoDB document to Pydantic model,
#         handling nested _id conversions and special cases.
#         """
#         if not data:
#             return data

#         def convert_ids(document: Any) -> Any:
#             # Recursive conversion for nested structures
#             if isinstance(document, list):
#                 return [convert_ids(item) for item in document]

#             if isinstance(document, dict):
#                 # Create a new dict with converted keys and values
#                 converted = {}
#                 for key, value in document.items():
#                     # Convert nested structures
#                     converted_value = convert_ids(value)

#                     # Special handling for _id
#                     if key == '_id':
#                         converted['id'] = str(converted_value)
#                     else:
#                         converted[key] = converted_value

#                 return converted

#             # Convert other types to string if needed
#             return str(document) if isinstance(document, (ObjectId, bytes)) else document

#         # Apply conversion
#         converted_data = convert_ids(data)

#         # Handle hash separately if needed
#         hash_value = converted_data.pop('hash', None)

#         # Create model instance
#         instance = cls(**converted_data)

#         # Explicitly set hash if present
#         if hash_value is not None:
#             setattr(instance, "hash", hash_value)

#         return instance


class MongoModel(BaseModel):
    id: PyObjectId = Field(default=PyObjectId())
    description: Optional[str] = None
    flexible_metadata: Optional[dict] = None
    hash: Optional[str] = None
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=False,
    )

    # Customize serialization of ObjectId
    @field_serializer("id")
    def serialize_id(self, id: PyObjectId):
        return str(id)

    @model_validator(mode="before")
    @classmethod
    def ensure_id(cls, values: dict) -> dict:
        """
        Ensures the `_id` field uses the provided value or generates a new ObjectId.
        """
        logger.debug(f"Ensuring values: {values}")

        # If values is not a dict, skip processing and return as-is
        if not isinstance(values, dict):
            return values

        # If '_id' is provided, move it to 'id' and remove '_id'
        if "_id" in values:
            values["id"] = values.pop("_id")
        if "id" in values and values["id"] is not None:
            # If `id` is provided, validate and retain it
            logger.debug(f"Validating ID: {values['id']}")
            values["id"] = PyObjectId.validate(values["id"])
        else:
            # Generate a new ObjectId if no valid ID is provided
            values["id"] = PyObjectId()
        return values

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

        if not value:
            logger.debug("No description provided.")
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

    @classmethod
    def from_mongo(cls, data: dict):
        """We must convert _id into "id"."""
        if not data:
            return data

        # Helper function to convert nested documents
        def convert_ids(document):
            # logger.warning(f"Converting : {document}")
            if isinstance(document, list):
                return [convert_ids(item) for item in document]
            if isinstance(document, dict):
                document = {key: convert_ids(value) for key, value in document.items()}
                id = document.pop("_id", None)
                if id:
                    document["id"] = id
            if isinstance(document, str):
                return str(document)
            return document

        data = convert_ids(data)
        # Ensure 'hash' is explicitly retained
        hash_value = data.pop("hash", None)
        instance = cls(**data)
        if hash_value is not None:
            setattr(instance, "hash", hash_value)
        # else:
        # Compute hash if not present
        # setattr(instance, "hash", HashModel.compute_hash(data))
        return instance

    def to_json(self, **kwargs):
        parsed = self.model_dump(
            exclude_unset=True,
            by_alias=True,
            **kwargs,
        )

        parsed = convert_objectid_to_str(parsed)

        # Convert PosixPath to str
        for key, value in parsed.items():
            if isinstance(value, Path):
                parsed[key] = str(value)

        return parsed

    def mongo(self, **kwargs):
        exclude_unset = kwargs.pop("exclude_unset", False)
        by_alias = kwargs.pop("by_alias", True)

        parsed = self.model_dump(
            exclude_unset=exclude_unset,
            by_alias=by_alias,
            **kwargs,
        )
        logger.warning(f"Parsed: {parsed}")

        def convert_ids(obj):
            if isinstance(obj, dict):
                new_dict = {}
                for key, value in obj.items():
                    # Rename 'id' keys to '_id'
                    if key == "id":
                        new_key = "_id"
                        new_dict[new_key] = PyObjectId(str(value))
                    else:
                        new_key = key
                        # Recursively convert nested structures
                        new_dict[new_key] = convert_ids(value)

                return new_dict
            elif isinstance(obj, list):
                return [convert_ids(item) for item in obj]
            else:
                return obj

        parsed = convert_ids(parsed)
        logger.warning(f"Converted: {parsed}")

        # Convert PosixPath to str
        for key, value in parsed.items():
            if isinstance(value, Path):
                parsed[key] = str(value)
        logger.warning(f"Converted after path: {parsed}")

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
    value: str  # Store the hash string

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> "HashModel":
        if not re.match(r"^[a-fA-F0-9]{64}$", value):
            raise ValueError("Invalid hash")
        # Return an instance of HashModel
        return cls(value=value)

    @classmethod
    def compute_hash(cls, value: dict) -> str:
        hash_str = json.dumps(value, sort_keys=True).encode("utf-8")
        return hashlib.sha256(hash_str).hexdigest()
