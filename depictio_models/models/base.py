from datetime import datetime
import hashlib
from pathlib import Path, PosixPath
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field, GetCoreSchemaHandler, model_validator
import re

import json

from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


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
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.union_schema([core_schema.str_schema(), core_schema.is_instance_schema(ObjectId)])
        )

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError(f"Invalid ObjectId: {v}")

    # @classmethod
    # def __get_pydantic_json_schema__(cls, core_schema: core_schema.CoreSchema, handler: GetCoreSchemaHandler) -> JsonSchemaValue:
    #     """
    #     Customizes how PyObjectId is represented in JSON schema.
    #     """
    #     json_schema = handler(core_schema)
    #     json_schema.update(type="string", format="objectid")
    #     return json_schema


    # def __str__(self):
    #     """
    #     Convert ObjectId to string when serialized.
    #     """
    #     return str(super().__str__())

    # @classmethod
    # def __get_validators__(cls):
    #     yield cls.validate

    # @classmethod
    # def validate(cls, v):
    #     if not ObjectId.is_valid(v):
    #         raise ValueError("Invalid ObjectId")
    #     return ObjectId(v)

    # @classmethod
    # def __modify_schema__(cls, field_schema):
    #     field_schema.update(type="string")


class MongoModel(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")  # Handles MongoDB `_id`


    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: lambda oid: str(oid),
            PosixPath: lambda path: str(path),
        }

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


    @model_validator(mode="before")
    @classmethod
    def ensure_id(cls, values: dict) -> dict:
        """
        Ensures the `_id` field uses the provided value or generates a new ObjectId.
        """
        if "_id" in values and values["_id"] is not None:
            # If `_id` is provided, validate and retain it
            values["_id"] = PyObjectId.validate(values["_id"])
        elif "id" in values and values["id"] is not None:
            # If `id` is provided, validate and retain it
            values["_id"] = PyObjectId.validate(values["id"])
        else:
            # Generate a new ObjectId if no valid ID is provided
            values["_id"] = PyObjectId()
        return values

# class MongoModel(BaseModel):
#     class Config:
#         allow_population_by_field_name = True
#         json_encoders = {
#             datetime: lambda dt: dt.isoformat(),
#             ObjectId: lambda oid: str(oid),
#             PosixPath: lambda path: str(path),
#         }

#     @classmethod
#     def from_mongo(cls, data: dict):
#         """We must convert _id into "id"."""
#         if not data:
#             return data

#         # Helper function to convert nested documents
#         def convert_ids(document):
#             if isinstance(document, list):
#                 return [convert_ids(item) for item in document]
#             if isinstance(document, dict):
#                 document = {key: convert_ids(value) for key, value in document.items()}
#                 id = document.pop("_id", None)
#                 if id:
#                     document["id"] = id
#             return document

#         data = convert_ids(data)
#         return cls(**data)

#     def mongo(self, **kwargs):
#         exclude_unset = kwargs.pop("exclude_unset", False)
#         by_alias = kwargs.pop("by_alias", True)

#         parsed = self.dict(
#             exclude_unset=exclude_unset,
#             by_alias=by_alias,
#             **kwargs,
#         )

#         # Mongo uses `_id` as default key. We should stick to that as well.
#         if "_id" not in parsed and "id" in parsed:
#             parsed["_id"] = parsed.pop("id")

#         # Convert PosixPath to str
#         for key, value in parsed.items():
#             if isinstance(value, Path):
#                 parsed[key] = str(value)

#         return parsed


class DirectoryPath(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> str:
        path = Path(value)
        if not path.exists():
            raise ValueError(f"The directory '{value}' does not exist.")
        if not path.is_dir():
            raise ValueError(f"'{value}' is not a directory.")
        return value


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
