from typing import Dict, List, Optional, Set, Union
from bson import ObjectId
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    validator,
    root_validator,
)

from depictio_models.models.base import MongoModel, PyObjectId



##################
# Authentication #
##################


class Token(MongoModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    access_token: str
    token_lifetime: str = "short-lived"
    expire_datetime: str
    name: Optional[str] = None
    hash: Optional[str] = None
    # scope: Optional[str] = None
    # user_id: PyObjectId

    @root_validator(pre=True)
    def set_default_id(cls, values):
        if values is None or "_id" not in values or values["_id"] is None:
            return values  # Ensure we don't proceed if values is None
        values["_id"] = PyObjectId()
        return values
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: lambda v: str(v)}


###################
# User management #
###################


class UserBase(MongoModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    email: EmailStr
    is_admin: bool = False
    groups: List[str] = Field(default_factory=list)

    @root_validator(pre=True)
    def set_default_id(cls, values):
        if values is None or "_id" not in values or values["_id"] is None:
            return values  # Ensure we don't proceed if values is None
        values["_id"] = PyObjectId()
        return values

class User(UserBase):
    # id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    # user_id: Optional[PyObjectId] = None
    # username: str
    # email: EmailStr
    tokens: List[Token] = Field(default_factory=list)
    current_access_token: Optional[str] = None
    is_active: bool = True
    # is_admin: bool = False
    is_verified: bool = False
    last_login: Optional[str] = None
    registration_date: Optional[str] = None
    # groups: Optional[List[PyObjectId]] = Field(default_factory=list)
    password: str

    @root_validator(pre=True)
    def set_default_id(cls, values):
        if values is None or "_id" not in values or values["_id"] is None:
            return values  # Ensure we don't proceed if values is None
        values["_id"] = PyObjectId()
        return values

    @validator("password", pre=True)
    def hash_password(cls, v):
        # check that the password is hashed
        if v.startswith("$2b$"):
            return v

    class Config:
        json_encoders = {ObjectId: lambda v: str(v)}

    def __hash__(self):
        # Hash based on the unique user_id
        return hash(self.id)

    def __eq__(self, other):
        # Equality based on the unique user_id
        if isinstance(other, User):
            return all(getattr(self, field) == getattr(other, field) for field in self.__fields__.keys() if field not in ["user_id", "registration_time"])
        return False

    @root_validator
    def add_admin_to_group(cls, values):
        if values.get("is_admin"):
            group_ids = values.get("groups", [])
            if "admin" not in group_ids:
                group_ids.append("admin")
            values["groups"] = group_ids
        return values


class Group(BaseModel):
    user_id: PyObjectId = Field(default_factory=PyObjectId)
    name: str
    members: Set[User]  # Set of User objects instead of ObjectId

    @validator("members", each_item=True, pre=True)
    def ensure_unique_users(cls, user):
        if not isinstance(user, User):
            raise ValueError(f"Each member must be an instance of User, got {type(user)}")
        return user

    # This function ensures there are no duplicate users in the group
    @root_validator(pre=True)
    def ensure_unique_member_ids(cls, values):
        members = values.get("members", [])
        unique_members = {member.id: member for member in members}.values()
        return {"members": set(unique_members)} 

    # This function validates that each user_id in the members is unique
    @root_validator
    def check_user_ids_are_unique(cls, values):
        seen = set()
        members = values.get("members", [])
        for member in members:
            if member.id in seen:
                raise ValueError("Duplicate user_id found in group members.")
            seen.add(member.id)
        return values

class Permission(BaseModel):
    owners: List[UserBase] = []  # Default to an empty list
    viewers: Optional[List[Union[UserBase, str]]] = []  # Allow string wildcard "*" in viewers

    def dict(self, **kwargs):
        # Generate list of owner and viewer dictionaries
        owners_list = [owner.dict(**kwargs) for owner in self.owners]
        viewers_list = [viewer.dict(**kwargs) if isinstance(viewer, UserBase) else viewer for viewer in self.viewers]
        return {"owners": owners_list, "viewers": viewers_list}

    @validator("owners", "viewers", pre=True, each_item=True)
    def convert_dict_to_user(cls, v):
        if isinstance(v, dict):
            return UserBase(**v)  # Assuming `UserBase` can be instantiated from a dict
        elif isinstance(v, str) and v == "*":
            return v  # Allow wildcard "*" for public workflows in viewers
        elif not isinstance(v, UserBase):
            raise ValueError("Owners must be UserBase instances, and viewers must be either UserBase or '*'")
        return v

    @root_validator(pre=True)
    def validate_permissions(cls, values):
        owners = values.get("owners", [])
        viewers = values.get("viewers", [])
        # Uncomment the following line if you want to enforce at least one owner.
        # if not owners:
        #     raise ValueError("At least one owner is required.")
        return values

    # Here we ensure that there are no duplicate users across owners and viewers
    @root_validator
    def ensure_owners_and_viewers_are_unique(cls, values):
        owners = values.get("owners", [])
        viewers = values.get("viewers", [])
        owner_ids = {owner.id for owner in owners}
        viewer_ids = {viewer.id for viewer in viewers if isinstance(viewer, UserBase)}

        if not owner_ids.isdisjoint(viewer_ids):
            raise ValueError("A User cannot be both an owner and a viewer.")

        return values