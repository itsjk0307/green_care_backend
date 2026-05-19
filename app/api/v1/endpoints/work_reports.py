from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_strict_admin, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.work_report import (
    WorkReportComplete,
    WorkReportCreate,
    WorkReportListResponse,
    WorkReportResponse,
    WorkReportStatusUpdate,
)
from app.services.work_report_service import (
    complete_work_report,
    create_work_report,
    get_work_report_by_id,
    get_work_reports,
    update_work_report_status,
)
from app.services.storage_service import save_image

router = APIRouter(prefix="/work-reports", tags=["work-reports"])
def _parse_json_array_objects(value: str | None, field_name: str) -> list[dict] | None:
    if value is None or value.strip() == "":
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON for {field_name}.",
        ) from err
    if parsed is None:
        return None
    if not isinstance(parsed, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a JSON array.",
        )
    if not all(isinstance(item, dict) for item in parsed):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a JSON array of objects.",
        )
    return parsed


def _parse_work_types_json(raw: str) -> list[str]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="work_types must be valid JSON.",
        ) from err
    if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="work_types must be a JSON array of strings.",
        )
    return parsed


def _parse_gps_route_json(raw: str | None) -> list[dict] | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="gps_route must be valid JSON.",
        ) from err
    if not isinstance(parsed, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="gps_route must be a JSON array.",
        )
    if not all(isinstance(item, dict) for item in parsed):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="gps_route must be a JSON array of objects.",
        )
    return parsed


@router.post("/", response_model=ApiResponse[WorkReportResponse], status_code=status.HTTP_201_CREATED)
async def create_work_report_endpoint(
    course_id: uuid.UUID = Form(...),
    work_types: str = Form(
        ...,
        description='JSON array of work type keys, e.g. ["mowing","watering"]',
    ),
    zone_coordinates: str | None = Form(
        default=None,
        description="Optional JSON array of coordinate objects",
    ),
    gps_latitude: float | None = Form(default=None),
    gps_longitude: float | None = Form(default=None),
    mark_type: str | None = Form(default=None),
    pin_x: float | None = Form(default=None),
    pin_y: float | None = Form(default=None),
    notes: str | None = Form(default=None),
    before_image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[WorkReportResponse]:
    wt_list = _parse_work_types_json(work_types)
    zc = _parse_json_array_objects(zone_coordinates, "zone_coordinates")
    payload = WorkReportCreate.model_validate(
        {
            "course_id": course_id,
            "work_types": wt_list,
            "zone_coordinates": zc,
            "mark_type": mark_type,
            "pin_x": pin_x,
            "pin_y": pin_y,
            "gps_latitude": gps_latitude,
            "gps_longitude": gps_longitude,
            "notes": notes,
        }
    )
    before_path = await save_image(before_image, folder="work_reports")
    created = await create_work_report(
        db=db,
        worker_id=current_user.id,
        course_id=payload.course_id,
        work_types=payload.work_types,
        before_image_path=before_path,
        zone_coordinates=payload.zone_coordinates,
        mark_type=payload.mark_type,
        pin_x=payload.pin_x,
        pin_y=payload.pin_y,
        gps_latitude=payload.gps_latitude,
        gps_longitude=payload.gps_longitude,
        notes=payload.notes,
    )
    return ApiResponse[WorkReportResponse](
        success=True,
        message="Work report created successfully.",
        data=created,
    )


@router.post(
    "/{report_id}/complete",
    response_model=ApiResponse[WorkReportResponse],
    status_code=status.HTTP_200_OK,
)
async def complete_work_report_endpoint(
    report_id: uuid.UUID,
    notes: str | None = Form(default=None),
    gps_route: str | None = Form(
        default=None,
        description="Optional JSON array of {lat,lng,timestamp} objects",
    ),
    after_image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[WorkReportResponse]:
    gr = _parse_gps_route_json(gps_route)
    complete_payload = WorkReportComplete(notes=notes, gps_route=gr)
    after_path = await save_image(after_image, folder="work_reports")
    updated = await complete_work_report(
        db=db,
        report_id=report_id,
        worker_id=current_user.id,
        after_image_path=after_path,
        gps_route=complete_payload.gps_route,
        notes=complete_payload.notes,
    )
    return ApiResponse[WorkReportResponse](
        success=True,
        message="Work report marked complete and submitted for review.",
        data=updated,
    )


@router.get("/", response_model=ApiResponse[WorkReportListResponse], status_code=status.HTTP_200_OK)
async def list_work_reports_endpoint(
    course_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[WorkReportListResponse]:
    data = await get_work_reports(
        db=db,
        user_id=current_user.id,
        role=current_user.role.value,
        course_id=course_id,
        status_filter=status,
        page=page,
        limit=limit,
    )
    return ApiResponse[WorkReportListResponse](
        success=True,
        message="Work reports fetched successfully.",
        data=data,
    )


@router.get("/{report_id}", response_model=ApiResponse[WorkReportResponse], status_code=status.HTTP_200_OK)
async def get_work_report_endpoint(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[WorkReportResponse]:
    report = await get_work_report_by_id(
        db=db,
        report_id=report_id,
        user_id=current_user.id,
        role=current_user.role.value,
    )
    return ApiResponse[WorkReportResponse](
        success=True,
        message="Work report fetched successfully.",
        data=report,
    )


@router.patch(
    "/{report_id}/status",
    response_model=ApiResponse[WorkReportResponse],
    status_code=status.HTTP_200_OK,
)
async def update_work_report_status_endpoint(
    report_id: uuid.UUID,
    payload: WorkReportStatusUpdate,
    admin_user: User = Depends(get_current_strict_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[WorkReportResponse]:
    updated = await update_work_report_status(
        db=db,
        report_id=report_id,
        status_value=payload.status,
        admin_user_id=admin_user.id,
    )
    return ApiResponse[WorkReportResponse](
        success=True,
        message="Work report status updated successfully.",
        data=updated,
    )
