"""Opt-in development-only patent snapshot endpoints."""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.patent_schemas import PatentSnapshotResponse, PatentWorksheet
from app.services import patent
from app.services.audit import AuditEventType, audit_service
from app.services.auth import TokenData
from app.services.permissions import require_permission
from app.utils.ip_resolution import get_client_ip

router = APIRouter(prefix="/matters", tags=["patent-preview"])


@router.post("/{matter_id}/patent-snapshots", response_model=PatentSnapshotResponse, status_code=201)
async def save_patent_snapshot(
    matter_id: str, worksheet: PatentWorksheet, request: Request, response: Response,
    current_user: TokenData = require_permission("matters.manage"),
    db: AsyncSession = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    row = await patent.save_snapshot(db, matter_id, current_user.user_id, worksheet)
    await audit_service.log_event(
        event_type=AuditEventType.DATA_MODIFICATION,
        user_id=current_user.user_id, user_email=current_user.email,
        resource_type="patent_snapshot", resource_id=row.id,
        ip_address=get_client_ip(request),
        details={"action": "patent_snapshot_saved", "matter_id": matter_id},
    )
    return patent.decode_snapshot(row)


@router.get("/{matter_id}/patent-snapshots/latest", response_model=PatentSnapshotResponse | None)
async def latest_patent_snapshot(
    matter_id: str, request: Request, response: Response,
    current_user: TokenData = require_permission("documents.view"),
    db: AsyncSession = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    row = await patent.read_latest(db, matter_id, current_user.user_id)
    if row is None:
        return None
    await audit_service.log_event(
        event_type=AuditEventType.DATA_ACCESS, user_id=current_user.user_id,
        user_email=current_user.email, resource_type="patent_snapshot", resource_id=row.id,
        ip_address=get_client_ip(request), details={"action": "patent_snapshot_read", "matter_id": matter_id},
    )
    return patent.decode_snapshot(row)
