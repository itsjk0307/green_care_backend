from __future__ import annotations

import io
import os
import uuid
from datetime import date, datetime
from pathlib import Path

import aiofiles
import aiofiles.os
from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
FIELD_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png"}
DRONE_SCAN_CONTENT_TYPES = {"image/jpeg", "image/png"}
DRONE_SCAN_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_IMAGE_SIZE_BYTES = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


async def _read_and_validate(
    file: UploadFile,
    allowed: set[str],
    label: str = "image",
) -> bytes:
    """Read the full file content, validate extension + size + PIL, return bytes.

    The caller should NOT call file.read() again — this function returns the
    bytes so they can be written directly, avoiding a double-read.
    """
    filename = file.filename or ""
    ext = _extension(filename)
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid {label} extension '{ext}'. "
                f"Allowed: {', '.join(sorted(allowed))}."
            ),
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded {label} file is empty.",
        )
    if len(content) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image size must be <= {settings.MAX_IMAGE_SIZE_MB} MB.",
        )

    try:
        with Image.open(io.BytesIO(content)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file is not a valid {label}.",
        )

    return content


async def validate_image(file: UploadFile) -> bool:
    """Validate a generic image upload (extension + size + PIL).
    Seeks back to 0 after reading so the caller can read again if needed.
    """
    await _read_and_validate(file, ALLOWED_EXTENSIONS)
    await file.seek(0)
    return True


async def save_image(file: UploadFile, folder: str = "uploads") -> str:
    """Save a validated image under storage/images/<folder>/YYYY/MM/DD/.
    Returns the path relative to LOCAL_STORAGE_PATH.
    """
    content = await _read_and_validate(file, ALLOWED_EXTENSIONS)

    ext = _extension(file.filename or "jpg") or "jpg"
    today = datetime.utcnow()
    unique_name = f"{uuid.uuid4()}_{today.strftime('%Y%m%d%H%M%S')}.{ext}"

    relative_dir = (
        Path(folder) / today.strftime("%Y") / today.strftime("%m") / today.strftime("%d")
    )
    absolute_dir = Path(settings.LOCAL_STORAGE_PATH) / relative_dir
    os.makedirs(str(absolute_dir), exist_ok=True)

    absolute_path = absolute_dir / unique_name
    relative_path = (relative_dir / unique_name).as_posix()

    try:
        async with aiofiles.open(absolute_path, "wb") as out:
            await out.write(content)
        return relative_path
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save image to storage.",
        ) from exc


async def save_report_image(file: UploadFile, suffix: str = "_before") -> str:
    """Save a work-report image.

    Destination: storage/images/reports/YYYY/MM/DD/{uuid}{suffix}.jpg
    Returns path relative to LOCAL_STORAGE_PATH, e.g.:
        reports/2026/05/28/{uuid}_before.jpg
    The static mount at /storage serves this as:
        /storage/images/reports/2026/05/28/{uuid}_before.jpg
    """
    content = await _read_and_validate(file, ALLOWED_EXTENSIONS, label="report image")

    today = datetime.utcnow()
    unique_name = f"{uuid.uuid4()}{suffix}.jpg"
    relative_dir = (
        Path("reports") / today.strftime("%Y") / today.strftime("%m") / today.strftime("%d")
    )
    absolute_dir = Path(settings.LOCAL_STORAGE_PATH) / relative_dir
    os.makedirs(str(absolute_dir), exist_ok=True)

    absolute_path = absolute_dir / unique_name
    relative_path = (relative_dir / unique_name).as_posix()

    try:
        async with aiofiles.open(absolute_path, "wb") as out:
            await out.write(content)
        return relative_path
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save report image to storage.",
        ) from exc


async def save_field_photo(file: UploadFile) -> str:
    """Save a field photo (jpg/jpeg/png only).

    Destination: storage/images/field/YYYY/MM/DD/{uuid}.jpg
    Returns path relative to LOCAL_STORAGE_PATH, e.g.:
        field/2026/05/28/{uuid}.jpg
    The static mount at /storage serves this as:
        /storage/images/field/2026/05/28/{uuid}.jpg
    """
    content = await _read_and_validate(file, FIELD_PHOTO_EXTENSIONS, label="field photo")

    today = datetime.utcnow()
    unique_name = f"{uuid.uuid4()}.jpg"
    relative_dir = (
        Path("field") / today.strftime("%Y") / today.strftime("%m") / today.strftime("%d")
    )
    absolute_dir = Path(settings.LOCAL_STORAGE_PATH) / relative_dir
    os.makedirs(str(absolute_dir), exist_ok=True)

    absolute_path = absolute_dir / unique_name
    relative_path = (relative_dir / unique_name).as_posix()

    try:
        async with aiofiles.open(absolute_path, "wb") as out:
            await out.write(content)
        return relative_path
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save field photo to storage.",
        ) from exc


def build_image_url(image_path: str) -> str:
    """Convert a path relative to LOCAL_STORAGE_PATH into a /storage/images/... URL.

    Examples:
        reports/2026/05/28/{uuid}_before.jpg  →  /storage/images/reports/2026/05/28/{uuid}_before.jpg
        field/2026/05/28/{uuid}.jpg           →  /storage/images/field/2026/05/28/{uuid}.jpg
    """
    if not image_path:
        return ""
    normalized = image_path.lstrip("/\\")
    return f"/storage/images/{normalized}"


def get_image_full_path(image_path: str) -> str:
    normalized = image_path.lstrip("/\\")
    full_path = (Path(settings.LOCAL_STORAGE_PATH) / normalized).resolve()
    return str(full_path)


async def delete_image(image_path: str) -> bool:
    normalized = image_path.lstrip("/\\")
    absolute_path = Path(settings.LOCAL_STORAGE_PATH) / normalized

    if not await aiofiles.ospath.exists(absolute_path):
        return False

    try:
        await aiofiles.os.remove(absolute_path)
        return True
    except FileNotFoundError:
        return False
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete image from storage.",
        ) from exc


def _storage_root() -> Path:
    """Project storage/ directory (parent of LOCAL_STORAGE_PATH images/ folder)."""
    return Path(settings.LOCAL_STORAGE_PATH).resolve().parent


async def validate_drone_scan_image(file: UploadFile) -> None:
    content_type = (file.content_type or "").lower()
    filename = file.filename or ""
    ext = _extension(filename)

    if content_type not in DRONE_SCAN_CONTENT_TYPES and ext not in DRONE_SCAN_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image/jpeg and image/png files are allowed for drone scans.",
        )
    await _read_and_validate(file, DRONE_SCAN_EXTENSIONS, label="drone scan image")
    await file.seek(0)


async def save_drone_scan_image(
    file: UploadFile,
    scan_date: date,
) -> tuple[str, int, int]:
    """Save drone scan image to storage/drone_scans/YYYY/MM/DD/{uuid}.jpg.
    Returns (relative_path, width, height).
    """
    content_type = (file.content_type or "").lower()
    filename = file.filename or ""
    ext = _extension(filename)

    if content_type not in DRONE_SCAN_CONTENT_TYPES and ext not in DRONE_SCAN_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image/jpeg and image/png files are allowed for drone scans.",
        )

    content = await _read_and_validate(file, DRONE_SCAN_EXTENSIONS, label="drone scan image")

    unique_name = f"{uuid.uuid4()}.jpg"
    relative_dir = (
        Path("drone_scans")
        / scan_date.strftime("%Y")
        / scan_date.strftime("%m")
        / scan_date.strftime("%d")
    )
    absolute_dir = _storage_root() / relative_dir
    os.makedirs(str(absolute_dir), exist_ok=True)

    absolute_path = absolute_dir / unique_name
    relative_path = (relative_dir / unique_name).as_posix()

    try:
        async with aiofiles.open(absolute_path, "wb") as out:
            await out.write(content)

        with Image.open(io.BytesIO(content)) as img:
            width, height = img.size

        return relative_path, width, height
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save drone scan image to storage.",
        ) from exc


async def validate_issue_image(file: UploadFile) -> None:
    content_type = (file.content_type or "").lower()
    filename = file.filename or ""
    ext = _extension(filename)

    if content_type not in DRONE_SCAN_CONTENT_TYPES and ext not in DRONE_SCAN_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image/jpeg and image/png files are allowed for issue photos.",
        )
    await _read_and_validate(file, DRONE_SCAN_EXTENSIONS, label="issue image")
    await file.seek(0)


async def save_issue_image(file: UploadFile) -> str:
    """Save issue image to storage/issues/YYYY/MM/DD/{uuid}.jpg.
    Returns relative path from storage root.
    """
    content_type = (file.content_type or "").lower()
    filename = file.filename or ""
    ext = _extension(filename)

    if content_type not in DRONE_SCAN_CONTENT_TYPES and ext not in DRONE_SCAN_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image/jpeg and image/png files are allowed for issue photos.",
        )

    content = await _read_and_validate(file, DRONE_SCAN_EXTENSIONS, label="issue image")

    today = datetime.utcnow()
    relative_dir = (
        Path("issues") / today.strftime("%Y") / today.strftime("%m") / today.strftime("%d")
    )
    unique_name = f"{uuid.uuid4()}.jpg"
    absolute_dir = _storage_root() / relative_dir
    os.makedirs(str(absolute_dir), exist_ok=True)

    absolute_path = absolute_dir / unique_name
    relative_path = (relative_dir / unique_name).as_posix()

    try:
        async with aiofiles.open(absolute_path, "wb") as out:
            await out.write(content)
        return relative_path
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save issue image to storage.",
        ) from exc


async def delete_storage_file(relative_path: str) -> bool:
    """Delete a file under the project storage/ root (e.g. issues/..., drone_scans/...)."""
    normalized = relative_path.lstrip("/\\")
    absolute_path = _storage_root() / normalized

    if not await aiofiles.ospath.exists(absolute_path):
        return False

    try:
        await aiofiles.os.remove(absolute_path)
        return True
    except FileNotFoundError:
        return False
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file from storage.",
        ) from exc
