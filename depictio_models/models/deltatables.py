from datetime import datetime
from typing import Dict, List, Optional, Union
from bson import ObjectId
from pydantic import (
    BaseModel,
    field_validator,
    model_validator,
)
from depictio_models.models.users import UserBase
from depictio_models.models.base import MongoModel, PyObjectId


class DeltaTableColumn(BaseModel):
    name: str
    type: str
    description: Optional[str] = None  # Optional description
    specs: Optional[Dict] = None

    class Config:
        extra = "forbid"  # Reject unexpected fields

    @field_validator("type")
    def validate_column_type(cls, v):
        allowed_values = [
            "string",
            "utf8",
            "object",
            "int64",
            "float64",
            "bool",
            "date",
            "datetime",
            "time",
            "category",
        ]
        if v.lower() not in allowed_values:
            raise ValueError(f"column_type must be one of {allowed_values}")
        return v


class Aggregation(MongoModel):
    aggregation_time: datetime = datetime.now()
    aggregation_by: UserBase
    aggregation_version: int = 1
    aggregation_hash: str
    aggregation_columns_specs: List[DeltaTableColumn] = []

    # @field_validator("aggregation_time", pre=True, always=True)
    # def validate_creation_time(cls, value):
    #     if type(value) is not datetime:
    #         try:
    #             dt = datetime.fromisoformat(value)
    #             return dt.strftime("%Y-%m-%d %H:%M:%S")
    #         except ValueError:
    #             raise ValueError("Invalid datetime format")
    #     else:
    #         return value.strftime("%Y-%m-%d %H:%M:%S")

    @field_validator("aggregation_version")
    def validate_version(cls, value):
        if not isinstance(value, int):
            raise ValueError("version must be an integer")
        return value


class FilterCondition(BaseModel):
    class Config:
        extra = "forbid"  # Reject unexpected fields

    above: Optional[Union[int, float, str]] = None
    equal: Optional[Union[int, float, str]] = None
    under: Optional[Union[int, float, str]] = None


class DeltaTableQuery(MongoModel):
    columns: List[str]
    filters: Dict[str, FilterCondition]
    sort: Optional[List[str]] = []
    limit: Optional[int] = None
    offset: Optional[int] = None

class Test(BaseModel):
    test: str

class DeltaTableAggregated(MongoModel):
    # id: Optional[PyObjectId] = None
    data_collection_id: PyObjectId
    delta_table_location: str
    aggregation: List[Aggregation] = []

    # def __eq__(self, other):
    #     if isinstance(other, DeltaTableAggregated):
    #         return all(getattr(self, field) == getattr(other, field) for field in self.model_fields.keys() if field not in ["id"])
    #     return NotImplemented

    # @model_validator(mode="before")
    # def validate_delta_table_location(cls, v):
    #     """
    #     Validate the delta_table_location field to ensure it starts with 's3://' and ends with the data_collection_id.
    #     """
    #     # check if v starts with 's3://' and ends with the data_collection_id
    #     if not v["delta_table_location"].startswith("s3://"):
    #         raise ValueError("delta_table_location must start with 's3://'")
    #     if not v["delta_table_location"].endswith(str(v["data_collection_id"])):
    #         raise ValueError("delta_table_location must end with the data_collection_id")


class UpsertDeltaTableAggregated(BaseModel):
    data_collection_id: PyObjectId
    delta_table_location: str
    update: bool = False