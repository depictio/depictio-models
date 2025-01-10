from typing import List, Optional, Set, Union
from bson import ObjectId
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from depictio_models.models.base import MongoModel, PyObjectId
from depictio_models.logging import logger


##################
# Authentication #
##################


class Token(MongoModel):
    id: PyObjectId = Field(default_factory=None, alias="_id")
    access_token: str
    token_lifetime: str = "short-lived"
    expire_datetime: str
    name: Optional[str] = None
    hash: Optional[str] = None
    # scope: Optional[str] = None
    # user_id: PyObjectId

    @model_validator(mode="before")
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
    id: PyObjectId = Field(default_factory=None, alias="_id")
    email: EmailStr
    is_admin: bool = False
    groups: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
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

    @model_validator(mode="before")
    def set_default_id(cls, values):
        if values is None or "_id" not in values or values["_id"] is None:
            return values  # Ensure we don't proceed if values is None
        values["_id"] = PyObjectId()
        return values

    @field_validator("password", mode="before")
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
            return all(getattr(self, field) == getattr(other, field) for field in self.model_fields.keys() if field not in ["user_id", "registration_time"])
        return False

    @model_validator(mode="before")
    def add_admin_to_group(cls, values):
        if values.get("is_admin"):
            group_ids = values.get("groups", [])
            if "admin" not in group_ids:
                group_ids.append("admin")
            values["groups"] = group_ids
        return values


class Group(BaseModel):
    user_id: PyObjectId = Field(default_factory=None, alias="_id")
    name: str
    members: Set[User]  # Set of User objects instead of ObjectId

    @field_validator("members", mode="before")
    def ensure_unique_users(cls, user):
        if not isinstance(user, User):
            raise ValueError(f"Each member must be an instance of User, got {type(user)}")
        return user

    # This function ensures there are no duplicate users in the group
    @model_validator(mode="before")
    def ensure_unique_member_ids(cls, values):
        members = values.get("members", [])
        unique_members = {member.id: member for member in members}.values()
        return {"members": set(unique_members)} 

    # This function validates that each user_id in the members is unique
    @model_validator(mode="before")
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
    editors: List[UserBase] = []  # Default to an empty list
    viewers: List[Union[UserBase, str]] = []  # Allow string wildcard "*" in viewers

    def dict(self, **kwargs):
        # Generate list of owner and viewer dictionaries
        owners_list = [owner.model_dump(**kwargs) for owner in self.owners]
        editors_list = [editor.model_dump(**kwargs) for editor in self.editors]
        viewers_list = [viewer.model_dump(**kwargs) if isinstance(viewer, UserBase) else viewer for viewer in self.viewers]
        return {"owners": owners_list, "editors": editors_list, "viewers": viewers_list}

    # Step 1: Convert lists to UserBase or validate items
    @field_validator("owners", "editors", "viewers", mode="before")
    def convert_list_to_userbase(cls, v):
        if not isinstance(v, list):
            raise ValueError(f"Expected a list, got {type(v)}")
        
        result = []
        for item in v:
            logger.debug(f"Converting {item} to UserBase")
            if isinstance(item, dict):
                result.append(UserBase(**item))  # Convert dictionary to UserBase
            elif isinstance(item, str) and item == "*":
                result.append(item)  # Allow wildcard "*" for viewers
            elif isinstance(item, UserBase):
                result.append(item)  # Already a UserBase instance
            else:
                raise ValueError("Owners, editors, and viewers must be UserBase instances or valid types")
        return result

    # Step 2: Validate permissions after field-level validation
    @model_validator(mode="after")
    def ensure_owners_and_viewers_are_unique(cls, values):
        owners = values.owners
        editors = values.editors
        viewers = values.viewers
        logger.debug(f"Owners: {owners}")
        logger.debug(f"Editors: {editors}")
        logger.debug(f"Viewers: {viewers}")

        owner_ids = {owner.id for owner in owners}
        editor_ids = {editor.id for editor in editors if isinstance(editor, UserBase)}
        viewer_ids = {viewer.id for viewer in viewers if isinstance(viewer, UserBase)}

        if not owner_ids.isdisjoint(editor_ids):
            raise ValueError("A User cannot be both an owner and an editor.")
        if not owner_ids.isdisjoint(viewer_ids):
            raise ValueError("A User cannot be both an owner and a viewer.")
        if not editor_ids.isdisjoint(viewer_ids):
            raise ValueError("A User cannot be both an editor and a viewer.")

        return values
