from datetime import timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src import create_logger
from src.api.core.auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_password_hash,
)
from src.api.core.exceptions import HTTPError
from src.api.core.responses import MsgSpecJSONResponse
from src.config import app_settings
from src.db.models import DBUser, aget_db
from src.db.repositories.user_repository import UserRepository
from src.schemas.db.models import BaseUserSchema, UserCreateSchema, UserSchema

if TYPE_CHECKING:
    pass

logger = create_logger(name=__name__)
ACCESS_TOKEN_EXPIRE_MINUTES: int = app_settings.ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(tags=["auth"], default_response_class=MsgSpecJSONResponse)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    request: Request,  # Required by SlowAPI  # noqa: ARG001
    user: UserCreateSchema,
    db: AsyncSession = Depends(aget_db),
) -> UserCreateSchema:
    """Register a new user.

    Parameters
    ----------
    user: UserCreateSchema
        Data required to create a new user (e.g. username, email, password).
    db: AsyncSession, optional
        Asynchronous database session dependency used to query and persist user data
        (default is provided by dependency injection).

    Returns
    -------
    UserCreateSchema
        Schema representation of the newly created user.
    """
    # Check if username exists
    user_repo = UserRepository(db=db)
    db_user: DBUser | None = await user_repo.aget_user_by_username(username=user.username)
    if db_user:
        raise HTTPError(
            status_code=status.HTTP_400_BAD_REQUEST,
            details="Username already exists. Please use a unique username",
        )
    # Check if email exists
    db_user = await user_repo.aget_user_by_email(email=user.email)
    if db_user:
        raise HTTPError(
            status_code=status.HTTP_400_BAD_REQUEST,
            details="Email already exists. Please use a unique email",
        )

    # === Create new user ===
    password_hash: str = get_password_hash(user.password.get_secret_value())  # type: ignore
    user_info = UserSchema(**user.model_dump(), password_hash=password_hash)
    print(f"DEBUG: Creating user: {user_info}")

    new_user = await user_repo.acreate_user(user=user_info)
    if not new_user:
        raise HTTPError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details="Failed to create new user due to an internal error.",
        )
    return UserCreateSchema(
        external_id=user.external_id,
        firstname=user.firstname,
        lastname=user.lastname,
        username=user.username,
        email=user.email,
        password=user.password,
        tier=user.tier,
        credits=user.credits,
        status=user.status,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/token", status_code=status.HTTP_200_OK)
async def login_for_access_token(
    request: Request,  # Required by SlowAPI  # noqa: ARG001
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(aget_db),
) -> dict[str, str]:
    """
    Authenticate a user and return an OAuth2 bearer access token.
    Validates credentials supplied via an OAuth2PasswordRequestForm (dependency-injected by FastAPI).
    On successful authentication a JWT access token is created and returned in the OAuth2 bearer format.

    Parameters
    ----------
    form_data: OAuth2PasswordRequestForm
        Dependency-injected form containing 'username' and 'password' fields.
        Provided by FastAPI via Depends().

    Returns
    -------
    dict[str, str]

    """
    logger.info("Authenticating user...")

    user: DBUser | None = await authenticate_user(
        db=db,
        username=form_data.username,  # form requires 'username' field
        password=form_data.password,
    )
    if not user:
        raise HTTPError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            details="Incorrect username of password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logger.info(f"user {user.username!r} authenticated successfully.")
    access_token_expires: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "tier": user.tier},
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", status_code=status.HTTP_200_OK)
async def get_current_user(
    request: Request,  # Required by SlowAPI  # noqa: ARG001
    current_user: BaseUserSchema = Depends(get_current_active_user),
) -> BaseUserSchema:
    """
    Endpoint to get the current logged-in user. This endpoint is protected
    and requires a valid JWT token.

    Returns:
    -------
    BaseUserSchema
        The current logged-in user's details.
    """

    return BaseUserSchema(
        external_id=current_user.external_id,
        firstname=current_user.firstname,
        lastname=current_user.lastname,
        username=current_user.username,
        email=current_user.email,
        tier=current_user.tier,
        credits=current_user.credits,
        status=current_user.status,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )
