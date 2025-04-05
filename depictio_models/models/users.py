from datetime import datetime
from typing import List, Optional, Union
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    HttpUrl,
    field_serializer,
    field_validator,
    model_validator,
)
from beanie import Document, Link, PydanticObjectId

from depictio_models.models.base import MongoModel
from depictio_models.logging import logger
from depictio_models.models.s3 import S3DepictioCLIConfig


class TokenData(BaseModel):
    name: Optional[str] = None
    token_lifetime: str = "short-lived"
    token_type: str = "bearer"
    sub: PydanticObjectId

    @field_serializer("sub")
    def serialize_sub(self, sub: PydanticObjectId) -> str:
        return str(sub)


class Token(TokenData):
    access_token: str
    expire_datetime: str


class TokenBeanie(Document):
    user_id: PydanticObjectId  # Reference to User's ObjectId
    access_token: str
    token_type: str = "bearer"
    token_lifetime: str = "short-lived"
    expire_datetime: datetime
    name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    model_config = {"arbitrary_types_allowed": True}

    class Settings:
        name = "tokens"  # Collection name
        use_revision = True  # Track document revisions

    # Field serializers for Pydantic v2
    @field_serializer("id")
    def serialize_id(self, id: PydanticObjectId) -> str:
        return str(id)

    @field_serializer("user_id")
    def serialize_user_id(self, user_id: PydanticObjectId) -> str:
        return str(user_id)

    # For consistent responses in the API
    def to_response_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": int((self.expire_datetime - datetime.now()).total_seconds()),
            "expires_at": self.expire_datetime,
            "created_at": self.created_at,
        }


class GroupBeanie(Document):
    name: str

    class Settings:
        name = "groups"  # Collection name
        use_revision = True  # Track document revisions


class Group(MongoModel):
    name: str


class UserBaseGroupLess(MongoModel):
    email: EmailStr
    is_admin: bool = False


class UserBaseCLIConfig(UserBaseGroupLess):
    token: Token


class GroupWithUsers(MongoModel):
    name: str
    users: List[UserBaseGroupLess] = []


class UserBase(UserBaseGroupLess):
    groups: List[Group]


class GroupUI(Group):
    users: List[UserBaseGroupLess] = []


class UserBaseGropLessBeanie(Document):
    email: EmailStr
    is_admin: bool = False


class UserBaseCLIConfigBeanie(UserBaseGropLessBeanie):
    token: TokenBeanie


class CLIConfig(BaseModel):
    user: UserBaseCLIConfigBeanie
    base_url: HttpUrl
    s3: S3DepictioCLIConfig


class UserBaseBeanie(UserBaseGropLessBeanie):
    groups: List[Link[GroupBeanie]]


class UserBeanie(UserBaseBeanie):
    # tokens: List[Link[TokenBeanie]] = Field(default_factory=list)
    # current_access_token: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    last_login: Optional[str] = None
    registration_date: Optional[str] = None
    password: str

    class Settings:
        name = "users"  # Collection name
        use_revision = True  # Track document revisions

    @field_validator("password", mode="before")
    def hash_password(cls, v):
        # check that the password is hashed
        if v.startswith("$2b$"):
            return v

    def turn_to_userbase(self):
        model_dump = self.model_dump()
        userbase = UserBaseBeanie(
            email=model_dump["email"], is_admin=model_dump["is_admin"], groups=model_dump["groups"]
        )
        return userbase

    def turn_to_userbasegroupless(self):
        model_dump = self.model_dump()
        userbase = UserBaseGropLessBeanie(
            email=model_dump["email"], is_admin=model_dump["is_admin"]
        )
        return userbase


class User(UserBase):
    tokens: List[Token] = Field(default_factory=list)
    current_access_token: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    last_login: Optional[str] = None
    registration_date: Optional[str] = None
    password: str
    # model_config = ConfigDict(

    # )

    @field_validator("password", mode="before")
    def hash_password(cls, v):
        # check that the password is hashed
        if v.startswith("$2b$"):
            return v

    # class ConfigDict:
    #     json_encoders = {ObjectId: lambda v: str(v)}

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

    def turn_to_userbasegroupless(self):
        model_dump = self.model_dump()
        userbase = UserBaseGroupLess(email=model_dump["email"], is_admin=model_dump["is_admin"])
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
