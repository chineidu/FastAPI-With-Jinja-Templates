from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from src import create_logger
from src.api.core.responses import MsgSpecJSONResponse

logger = create_logger(name=__name__)
templates = Jinja2Templates(directory="src/templates")
router = APIRouter(tags=["root"], default_response_class=MsgSpecJSONResponse)
TTL: int = 30  # seconds

mock_posts: list[dict[str, Any]] = [
    {
        "title": "My First Post",
        "post": "This is the content of my first post.",
        "tags": ["introduction", "welcome"],
        "allow_comments": True,
    },
    {
        "title": "Understanding FastAPI and Jinja2",
        "post": "Integrating Jinja2 templates with FastAPI provides a powerful way to serve server-side rendered pages efficiently. Today we explore how to pass context variables seamlessly.",
        "tags": ["fastapi", "python", "webdev"],
        "allow_comments": True,
    },
    {
        "title": "The Power of Native CSS Variables",
        "post": "Native CSS custom properties make implementing dark mode incredibly straightforward without relying on bloated external JavaScript libraries.",
        "tags": ["css", "frontend", "design"],
        "allow_comments": False,
    },
    {
        "title": "Architecture Decision Records Explained",
        "post": "Documenting software architectural choices using ADRs helps engineering teams understand the 'why' behind the code, preserving context for future developers.",
        "tags": ["architecture", "engineering", "best-practices"],
        "allow_comments": True,
    },
]


@router.get("/", status_code=status.HTTP_200_OK)
async def root() -> dict[str, str]:
    """Root endpoint for basic health check."""
    return {"message": "API is up and running!"}


@router.get("/blog", status_code=status.HTTP_200_OK)
async def blog(request: Request) -> Response:
    """Public blog homepage with no posts (unauthenticated access)."""
    return templates.TemplateResponse(
        request,
        "index.html",
        {"request": request, "posts": []},
    )


@router.get("/home", status_code=status.HTTP_200_OK)
async def home(request: Request) -> Response:
    """Root endpoint for basic health check."""
    return templates.TemplateResponse(
        request,
        "index.html",
        {"request": request, "posts": mock_posts},
    )


@router.get("/posts-viewer", status_code=status.HTTP_200_OK)
async def posts_viewer(request: Request) -> Response:
    """Posts viewer page with authentication support."""
    try:
        return templates.TemplateResponse(
            request,
            "posts.html",
            {"request": request},
        )
    except Exception as e:
        logger.exception(f"Error rendering template: {e}")
        raise
