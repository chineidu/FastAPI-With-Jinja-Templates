"""Utility functions for validating operations.

inspired by:
https://betterstack.com/community/guides/scaling-python/uploading-files-using-fastapi/#building-comprehensive-file-validation-systems
"""

from pathlib import Path

from fastapi import UploadFile

from src.schemas.types import DocumentValidationResult

MAX_SIZE_BYTES: int = 10 * 1024 * 1024  # 10MB in bytes


class DocumentValidator:
    def __init__(self, max_size: int = MAX_SIZE_BYTES) -> None:
        """Initialize the DocumentValidator with a maximum file size.

        Parameters
        ----------
        max_size : int, optional
            Maximum allowed file size in bytes, by default MAX_SIZE_BYTES (10MB)
        """

        self.max_size = max_size
        self.allowed_extensions: set[str] = {".pdf", ".txt", ".json"}

    async def validate_file(self, file: UploadFile) -> DocumentValidationResult:
        """Check if the document file is valid"""
        result: DocumentValidationResult = {"valid": True, "errors": []}

        # Check if user selected a file
        if not file.filename or file.filename.strip() == "":
            result["valid"] = False
            result["errors"].append("No file selected")
            return result

        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.allowed_extensions:
            result["valid"] = False
            result["errors"].append(
                f"File extension '{file_ext}' not allowed. Use: {', '.join(self.allowed_extensions)}"
            )

        # Read file to check size
        content = await file.read()
        await file.seek(0)  # Reset file pointer for later use

        # Check file size
        file_size: int = len(content)
        if file_size > self.max_size:
            result["valid"] = False
            result["errors"].append(f"File too large ({file_size:,} bytes). Maximum: {self.max_size:,} bytes")

        return result
