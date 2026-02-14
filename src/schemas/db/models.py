from datetime import datetime
from typing import Any, ClassVar
from uuid import uuid4

from pydantic import ConfigDict, EmailStr, Field, SecretStr, field_validator

from src.schemas.base import BaseSchema
from src.schemas.types import APIKeyScopeEnum, PostStatusEnum, RoleTypeEnum, TierEnum, UserStatusEnum


class BaseUserSchema(BaseSchema):
    """Schema representing a user."""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None},
    )

    id: int | None = Field(default=None)
    external_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique external identifier for the user."
    )
    firstname: str = Field(description="First name of the user.")
    lastname: str = Field(description="Last name of the user.")
    username: str = Field(description="Unique username for the user.")
    email: EmailStr = Field(description="Email address of the user.")
    tier: TierEnum = Field(default=TierEnum.FREE, description="The tier type")
    roles: list[RoleTypeEnum] = Field(default_factory=list)
    credits: float = Field(default=0.0, le=1_000_000.0, ge=0.0)
    status: UserStatusEnum = Field(default=UserStatusEnum.ACTIVE, description="Status of the guest user.")
    is_active: bool = Field(default=True, description="Indicates if the guest user is active.")
    created_at: datetime | None = Field(default=None, description="Creation date and time of the guest user.")
    updated_at: datetime | None = Field(
        default=None, description="Last update date and time of the guest user."
    )

    @field_validator("roles", mode="before")
    @classmethod
    def convert_roles(cls, v: Any) -> list[RoleTypeEnum]:
        """Convert DBRole objects or strings to RoleTypeEnum."""
        if not v:
            return []

        result = []
        for role in v:
            if isinstance(role, str):
                result.append(RoleTypeEnum(role))
            elif hasattr(role, "name"):  # DBRole object
                result.append(RoleTypeEnum(role.name))
            else:
                result.append(role)
        return result


class GuestUserSchema(BaseSchema):
    """Schema representing a guest/anonymous user with limited access."""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None},
    )

    id: int | None = None
    external_id: str = Field(default="guest", description="External identifier for the guest user.")
    firstname: str = Field(default="Guest", description="First name of the user.")
    lastname: str = Field(default="User", description="Last name of the user.")
    username: str = Field(default="guest_user", description="Username for the guest user.")
    email: EmailStr = Field(default="guest@anonymous.local")
    tier: TierEnum = Field(default=TierEnum.GUEST, description="Tier of the guest user.")
    credits: float = Field(default=0.0, description="Credits available for the guest user.")
    status: UserStatusEnum = Field(default=UserStatusEnum.ACTIVE, description="Status of the guest user.")
    is_active: bool = Field(default=True, description="Indicates if the guest user is active.")
    created_at: datetime | None = Field(default=None, description="Creation date and time of the guest user.")
    updated_at: datetime | None = Field(
        default=None, description="Last update date and time of the guest user."
    )


class UserCreateSchema(BaseUserSchema):
    """Schema representing a database user with password."""

    password: SecretStr = Field(
        description="Plaintext password for the user. Will be hashed before storage.", min_length=8
    )

    # Fetching and updating model config to add example
    _custom_model_config: ClassVar[ConfigDict] = BaseSchema.model_config.copy()
    _json_schema_extra: ClassVar[dict[str, Any]] = {
        "example": {
            "firstname": "example_firstname",
            "lastname": "example_lastname",
            "username": "example_username",
            "email": "user@example.com",
            "password": "securepassword123",
        }
    }
    _custom_model_config.update({"json_schema_extra": _json_schema_extra})
    model_config = _custom_model_config


class UserSchema(BaseUserSchema):
    """Schema representing a database user."""

    password_hash: str


class APIUpdateSchema(BaseSchema):
    """Schema representing the update of an API key."""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None},
    )

    id: int | None = Field(default=None, description="Unique identifier of the API key.")
    name: str | None = Field(default=None, description="Name of the API key.")
    requests_per_minute: int | None = Field(
        default=None, description="Request limit per minute for the API key."
    )
    expires_at: datetime | None = Field(default=None, description="Expiration date and time of the API key.")
    is_active: bool | None = Field(default=None, description="Active status of the API key.")


class APIKeySchema(APIUpdateSchema):
    """Schema representing a database API key."""

    user_id: int | None = Field(description="ID of the user owning the API key.")
    key_prefix: str = Field(description="Prefix of the API key.")
    key_hash: str = Field(description="Hashed value of the API key.")
    scopes: list[APIKeyScopeEnum] = Field(
        default_factory=list,
        description="List of scopes/permissions assigned to the API key.",
    )

    # System Managed Fields
    created_at: datetime | None = Field(default=None, description="Creation date and time of the API key.")
    updated_at: datetime | None = Field(default=None, description="Last update date and time of the API key.")
    last_used_at: datetime | None = Field(default=None, description="Last used date and time of the API key.")


class RoleSchema(BaseSchema):
    """Role schema."""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None},
    )

    id: int | None = Field(default=None, description="Unique identifier of the role.")
    name: RoleTypeEnum = Field(description="Name of the role.")
    description: str | None = Field(default=None, description="Description of the role.")
    created_at: datetime | None = Field(default=None, description="Creation date and time of the role.")
    updated_at: datetime | None = Field(default=None, description="Last update date and time of the role.")


ROLES: dict[str, RoleSchema] = {
    "admin": RoleSchema(name=RoleTypeEnum.ADMIN, description="Administrator with full access"),
    "user": RoleSchema(name=RoleTypeEnum.USER, description="Regular user with standard access"),
    "guest": RoleSchema(name=RoleTypeEnum.GUEST, description="Guest user with limited access"),
}


class PostCreateSchema(BaseSchema):
    """Schema representing a blog post."""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None},
    )
    title: str = Field(description="Title of the post.")
    post: str = Field(description="Content of the post.")
    tags: list[str] = Field(default_factory=list, description="List of tags associated with the post.")
    allow_comments: bool = Field(default=True, description="Indicates if comments are allowed on the post.")

    # Fetching and updating model config to add example
    _custom_model_config: ClassVar[ConfigDict] = BaseSchema.model_config.copy()
    _json_schema_extra: ClassVar[dict[str, Any]] = {
        "example": {
            "title": "My First Post",
            "post": "This is the content of my first post.",
            "tags": ["introduction", "welcome"],
            "allow_comments": True,
        }
    }
    _custom_model_config.update({"json_schema_extra": _json_schema_extra})
    model_config = _custom_model_config


class PostSchema(PostCreateSchema):
    """Schema representing a blog post."""

    id: int | None = Field(default=None, description="Unique identifier of the post.")
    user_id: int = Field(description="ID of the user who created the post.")
    author: str | None = Field(default="Anonymous", description="Username of the author.")
    slug: str = Field(description="URL-friendly slug for the post.")
    status: PostStatusEnum = Field(
        default=PostStatusEnum.DRAFT, description="Publication status of the post."
    )
    allow_comments: bool = Field(default=True, description="Indicates if comments are allowed on the post.")
    is_pinned: bool = Field(
        default=False, description="Indicates if the post is pinned to the top of the list."
    )
    published_at: datetime | None = Field(
        default_factory=datetime.now, description="Publication date and time of the post."
    )
    updated_at: datetime | None = Field(default=None, description="Last update date and time of the post.")
    deleted_at: datetime | None = Field(default=None, description="Deletion date and time of the post.")

    @field_validator("status", mode="before")
    @classmethod
    def convert_status(cls, v: Any) -> PostStatusEnum:
        """Convert string to PostStatusEnum."""
        if isinstance(v, str):
            return PostStatusEnum(v)
        return v
