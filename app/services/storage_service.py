from __future__ import annotations

import io
import uuid
from datetime import datetime
from pathlib import Path

import aiofiles
import aiofiles.os
from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE_BYTES = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024


async def validate_image(file: UploadFile) -> bool:
    filename = file.filename or ""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image extension. Allowed: jpg, jpeg, png, webp.",
        )

    content = await file.read()
    if not content or len(content) > MAX_IMAGE_SIZE_BYTES:
        await file.seek(0)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image size must be <= {settings.MAX_IMAGE_SIZE_MB}MB.",
        )

    try:
        with Image.open(io.BytesIO(content)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError):
        await file.seek(0)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid image.",
        )

    await file.seek(0)
    return True


async def save_image(file: UploadFile, folder: str = "uploads") -> str:
    await validate_image(file)

    extension = (file.filename or "jpg").rsplit(".", 1)[-1].lower()
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_name = f"{uuid.uuid4()}_{timestamp}.{extension}"

    today = datetime.utcnow()
    relative_dir = Path(folder) / today.strftime("%Y") / today.strftime("%m") / today.strftime("%d")
    absolute_dir = Path(settings.LOCAL_STORAGE_PATH) / relative_dir
    absolute_dir.mkdir(parents=True, exist_ok=True)

    absolute_path = absolute_dir / unique_name
    relative_path = (relative_dir / unique_name).as_posix()

    try:
        content = await file.read()
        async with aiofiles.open(absolute_path, "wb") as output:
            await output.write(content)
        await file.seek(0)
        return relative_path
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save image to storage.",
        ) from error


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
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete image from storage.",
        ) from error


async def save_detection_images(
    files: list[UploadFile],
    detection_id: uuid.UUID,
) -> list[tuple[str, float]]:
    """Save exactly 6 images under detections/YYYY/MM/DD/{detection_id}/image_N.ext. Returns [(relative_path, size_mb), ...]."""
    if len(files) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exactly 6 images required for disease detection analysis",
        )

    today = datetime.utcnow()
    relative_base = (
        Path("detections")
        / today.strftime("%Y")
        / today.strftime("%m")
        / today.strftime("%d")
        / str(detection_id)
    )
    absolute_base = Path(settings.LOCAL_STORAGE_PATH) / relative_base
    absolute_base.mkdir(parents=True, exist_ok=True)

    results: list[tuple[str, float]] = []
    for index, file in enumerate(files, start=1):
        await validate_image(file)
        extension = (file.filename or "jpg").rsplit(".", 1)[-1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            extension = "jpg"
        filename = f"image_{index}.{extension}"
        absolute_path = absolute_base / filename
        relative_path = (relative_base / filename).as_posix()

        try:
            content = await file.read()
            size_mb = round(len(content) / (1024 * 1024), 4)
            async with aiofiles.open(absolute_path, "wb") as output:
                await output.write(content)
            await file.seek(0)
            results.append((relative_path, size_mb))
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save detection images to storage.",
            ) from error

    return results
