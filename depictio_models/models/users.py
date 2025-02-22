from typing import List, Optional, Union
from bson import ObjectId
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from depictio_models.models.base import MongoModel
from depictio_models.logging import logger


class Token(MongoModel):
    access_token: str
    token_lifetime: str = "short-lived"
    expire_datetime: str
    name: Optional[str] = None
    hash: Optional[str] = None


class Group(MongoModel):
    name: str


class UserBase(MongoModel):
    email: EmailStr
    is_admin: bool = False
    groups: List[Group]


class User(UserBase):
    tokens: List[Token] = Field(default_factory=list)
    current_access_token: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    last_login: Optional[str] = None
    registration_date: Optional[str] = None
    password: str

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
            return all(
                getattr(self, field) == getattr(other, field)
                for field in self.model_fields.keys()
                if field not in ["user_id", "registration_time"]
            )
        return False

    def turn_to_userbase(self):
        model_dump = self.model_dump()
        userbase = UserBase(
            email=model_dump["email"], is_admin=model_dump["is_admin"], groups=model_dump["groups"]
        )
        return userbase


class Permission(BaseModel):
    owners: List[UserBase] = []  # Default to an empty list
    editors: List[UserBase] = []  # Default to an empty list
    viewers: List[Union[UserBase, str]] = []  # Allow string wildcard "*" in viewers

    def dict(self, **kwargs):
        # Generate list of owner and viewer dictionaries
        owners_list = [owner.model_dump(**kwargs) for owner in self.owners]
        editors_list = [editor.model_dump(**kwargs) for editor in self.editors]
        viewers_list = [
            viewer.model_dump(**kwargs) if isinstance(viewer, UserBase) else viewer
            for viewer in self.viewers
        ]
        return {"owners": owners_list, "editors": editors_list, "viewers": viewers_list}

    # Step 1: Convert lists to UserBase or validate items
    @field_validator("owners", "editors", "viewers", mode="before")
    def convert_list_to_userbase(cls, v):
        if not isinstance(v, list):
            raise ValueError(f"Expected a list, got {type(v)}")

        result = []
        logger.debug(f"Converting list to UserBase: {v}")
        for item in v:
            logger.debug(f"Converting {item} to UserBase")
            if isinstance(item, dict):
                # keep only id, email, is_admin, groups
                item = {
                    key: value
                    for key, value in item.items()
                    if key in ["id", "email", "is_admin", "groups"]
                }
                logger.debug(f"Filtered dictionary: {item}")

                result.append(UserBase(**item))  # Convert dictionary to UserBase
            elif isinstance(item, str) and item == "*":
                result.append(item)  # Allow wildcard "*" for viewers
            elif isinstance(item, UserBase):
                result.append(item)  # Already a UserBase instance
            else:
                raise ValueError(
                    "Owners, editors, and viewers must be UserBase instances or valid types"
                )
        logger.debug(f"Converted list to UserBase: {result}")
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
