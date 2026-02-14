import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from anyio import open_file
from fastapi import APIRouter, File, Request, UploadFile, status
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from src import ROOT, create_logger
from src.api.core.exceptions import HTTPError
from src.api.core.responses import MsgSpecJSONResponse
from src.utilities.validators import DocumentValidator

logger = create_logger(name=__name__)
templates = Jinja2Templates(directory="src/templates")
router = APIRouter(tags=["login"], default_response_class=MsgSpecJSONResponse)

# Create validator instance (It can also be created once in lifespan and reused
# across requests for better performance)
doc_validator = DocumentValidator(max_size=25 * 1024 * 1024)  # 25MB limit
# Define a chunk size to control memory usage (e.g., 1MB)
CHUNK_SIZE = 1024 * 1024

# Create upload directory

UPLOAD_DIR = ROOT / "uploads"
try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Upload directory: {UPLOAD_DIR.absolute()}")
except PermissionError:
    logger.warning(
        f"Permission denied when creating 'uploads' directory at {UPLOAD_DIR}. File uploads may fail."
    )
except Exception as e:
    logger.error(f"Unexpected error creating 'uploads' directory at {UPLOAD_DIR}: {e}")


@router.get("/login", status_code=status.HTTP_200_OK)
async def login_page(request: Request) -> Response:
    """Render the login page."""
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request, "title": "Login"},
    )


@router.get("/signup", status_code=status.HTTP_200_OK)
async def signup_page(request: Request) -> Response:
    """Render the signup / register page."""
    return templates.TemplateResponse(
        request,
        "signup.html",
        {"request": request, "title": "Sign Up"},
    )


@router.post("/upload/single")
async def upload_single_file(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload a single file with validation"""
    # Validate the file first
    validation = await doc_validator.validate_file(file)

    if not validation["valid"]:
        raise HTTPError(status_code=status.HTTP_400_BAD_REQUEST, details=json.dumps(validation["errors"]))

    # Create unique filename to prevent conflicts
    file_ext = Path(file.filename).suffix if file.filename else ""
    unique_filename: str = f"{uuid.uuid4()}{file_ext}"
    file_path: Path = UPLOAD_DIR / unique_filename

    try:
        # Use async file I/O to write the uploaded file
        async with await open_file(file_path, "wb") as f:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                # Write the chunk to disk asynchronously
                await f.write(chunk)

    except Exception as e:
        raise HTTPError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details=f"Failed to save file: {str(e)}"
        ) from e

    return {
        "success": True,
        "original_filename": file.filename,
        "stored_filename": unique_filename,
        "content_type": file.content_type,
        "size": file.size,
        "upload_time": datetime.now().isoformat(),
        "location": str(file_path),
    }
