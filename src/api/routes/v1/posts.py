from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src import create_logger
from src.api.core.auth import (
    get_current_active_user,
)
from src.api.core.exceptions import HTTPError
from src.api.core.ratelimit import get_rate_limiter
from src.api.core.responses import MsgSpecJSONResponse
from src.config import app_settings
from src.db.models import aget_db
from src.db.repositories.post_repository import PostRepository
from src.schemas.db.models import PostCreateSchema, PostSchema, UserSchema
from src.utilities.utils import make_slug

if TYPE_CHECKING:
    pass

logger = create_logger(name=__name__)
templates = Jinja2Templates(directory="src/templates")
ACCESS_TOKEN_EXPIRE_MINUTES: int = app_settings.ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(tags=["posts"], default_response_class=MsgSpecJSONResponse)


@router.post("/posts", status_code=status.HTTP_201_CREATED)
async def create_post(
    request: Request,  # Required by SlowAPI  # noqa: ARG001
    post_data: PostCreateSchema,
    db: AsyncSession = Depends(aget_db),
    rate_limiter=Depends(get_rate_limiter),  # noqa: ANN001, ARG001
    current_user: UserSchema = Depends(get_current_active_user),
) -> PostSchema:
    """Create a new post."""
    post_repo = PostRepository(db=db)
    if not post_repo:
        raise HTTPError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details="Post repository is currently unavailable. Please try again later.",
        )

    if not current_user.id:
        raise HTTPError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            details="User authentication required to create a post.",
        )
    # Create a new post instance
    new_post = PostSchema(
        user_id=current_user.id,
        title=post_data.title,
        post=post_data.post,
        tags=post_data.tags,
        slug=make_slug(post_data.title),
        allow_comments=post_data.allow_comments,
    )

    # Persist the new post to the database
    post_id: int = await post_repo.acreate_post(new_post)
    if not post_id:
        raise HTTPError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details="Failed to create the post. Please try again.",
        )
    return new_post


# /json comes before /{post_id} to avoid path conflicts with the post ID parameter.
# Otherwise, FastAPI may interpret "json" as a post ID, leading to routing errors.
@router.get("/posts/json", status_code=status.HTTP_200_OK)
async def list_posts_json(
    request: Request,  # noqa: ARG001
    db: AsyncSession = Depends(aget_db),
    current_user: UserSchema = Depends(get_current_active_user),  # noqa: ARG001
) -> dict[str, list[PostSchema]]:
    """List posts for the authenticated user as JSON."""
    post_repo = PostRepository(db=db)
    if not post_repo:
        raise HTTPError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details="Post repository is currently unavailable. Please try again later.",
        )

    if not current_user.id:
        raise HTTPError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            details="User authentication required to list posts.",
        )
    _posts, idx = await post_repo.aget_posts_cursor(user_id=current_user.id, limit=20)
    if _posts is None:
        raise HTTPError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details="Failed to retrieve posts. Please try again.",
        )
    # Convert and filter out any None results from failed validation
    posts = [post_repo.convert_DBPost_to_schema(post) for post in _posts]
    valid_posts = [p for p in posts if p is not None]
    return {"posts": valid_posts}


@router.get("/posts/{post_id}", status_code=status.HTTP_200_OK)
async def get_post(
    request: Request,  # noqa: ARG001
    post_id: int,
    db: AsyncSession = Depends(aget_db),
    current_user: UserSchema = Depends(get_current_active_user),  # noqa: ARG001
) -> PostSchema:
    """Retrieve a post by its ID."""
    post_repo = PostRepository(db=db)
    if not post_repo:
        raise HTTPError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details="Post repository is currently unavailable. Please try again later.",
        )
    _post = await post_repo.aget_post_by_id(id=post_id)
    if not _post:
        raise HTTPError(
            status_code=status.HTTP_404_NOT_FOUND,
            details="Post not found.",
        )
    post = post_repo.convert_DBPost_to_schema(_post)
    if not post:
        raise HTTPError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details="Failed to retrieve the post. Please try again.",
        )
    return post


@router.get("/posts", status_code=status.HTTP_200_OK)
async def list_posts(
    request: Request,
    db: AsyncSession = Depends(aget_db),
    current_user: UserSchema = Depends(get_current_active_user),  # noqa: ARG001
) -> Any:
    """List posts for the authenticated user via cursor-based pagination."""
    post_repo = PostRepository(db=db)
    if not post_repo:
        raise HTTPError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details="Post repository is currently unavailable. Please try again later.",
        )

    if not current_user.id:
        raise HTTPError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            details="User authentication required to list posts.",
        )
    _posts, idx = await post_repo.aget_posts_cursor(user_id=current_user.id, limit=20)
    if _posts is None:
        raise HTTPError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details="Failed to retrieve posts. Please try again.",
        )
    posts = [post_repo.convert_DBPost_to_schema(post) for post in _posts]
    return templates.TemplateResponse(
        request,
        "index.html",
        {"request": request, "posts": posts, "title": ""},
    )
