import pytest
from datetime import datetime
from pathlib import Path
from bson import ObjectId
from depictio_models.models.base import convert_objectid_to_str

def test_convert_dict())):
    input_data = {
        "id": ObjectId("507f1f77bcf86cd799439011"),
        "name": "test",
        "created_at": datetime(2023, 1, 1, 12, 0, 0),
        "path": Path("/some/path")
    }
    expected_output = {
        "id": "507f1f77bcf86cd799439011",
        "name": "test",
        "created_at": "2023-01-01 12:00:00",
        "path": "/some/path"
    }
    assert convert_objectid_to_str(input_data) == expected_output

def test_convert_list():
    input_data = [
        ObjectId("507f1f77bcf86cd799439011"),
        datetime(2023, 1, 1, 12, 0, 0),
        Path("/some/path"),
        "test"
    ]
    expected_output = [
        "507f1f77bcf86cd799439011",
        "2023-01-01 12:00:00",
        "/some/path",
        "test"
    ]
    assert convert_objectid_to_str(input_data) == expected_output

def test_convert_objectid():
    input_data = ObjectId("507f1f77bcf86cd799439011")
    expected_output = "507f1f77bcf86cd799439011"
    assert convert_objectid_to_str(input_data) == expected_output

def test_convert_datetime():
    input_data = datetime(2023, 1, 1, 12, 0, 0)
    expected_output = "2023-01-01 12:00:00"
    assert convert_objectid_to_str(input_data) == expected_output

def test_convert_path():
    input_data = Path("/some/path")
    expected_output = "/some/path"
    assert convert_objectid_to_str(input_data) == expected_output

def test_convert_other():
    input_data = "test"
    expected_output = "test"
    assert convert_objectid_to_str(input_data) == expected_output
