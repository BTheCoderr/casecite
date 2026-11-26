"""Matter-scoped encrypted snapshots; no model or document-provider calls."""

import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import ConflictError, NotFoundError
from app.models.matters import Matter
from app.models.patent import PatentSnapshot
from app.models.patent_schemas import PatentSnapshotResponse, PatentWorksheet
from app.services import matters
from app.services.encryption import encryption_service


def require_preview() -> None:
    if not (settings.debug and settings.patent_preview_enabled):
        raise NotFoundError("Patent storage preview is unavailable")


async def require_matter(
    db: AsyncSession, matter_id: str, user_id: str, *, write: bool = False
) -> Matter:
    require_preview()
    if not await matters.is_member(db, matter_id, user_id):
        raise NotFoundError("Matter not found")
    matter = await matters.get_matter(db, matter_id)
    if matter is None or (write and matter.owner_id != user_id):
        raise NotFoundError("Matter not found")
    if write and (matter.legal_hold or matter.retention_days is not None):
        raise ConflictError("Patent preview cannot write to a matter with hold or retention settings")
    return matter


def encode_snapshot(row_id: str, matter_id: str, worksheet: PatentWorksheet) -> str:
    payload = {"id": row_id, "matter_id": matter_id, "worksheet": worksheet.model_dump()}
    return encryption_service.encrypt_string(json.dumps(payload, ensure_ascii=False))


def decode_snapshot(row: PatentSnapshot) -> PatentSnapshotResponse:
    payload = json.loads(encryption_service.decrypt_string(row.ciphertext))
    if payload["id"] != row.id or payload["matter_id"] != row.matter_id:
        raise ValueError("Patent snapshot identity mismatch")
    return PatentSnapshotResponse(
        id=row.id,
        matter_id=row.matter_id,
        created_by=row.created_by,
        worksheet=PatentWorksheet.model_validate(payload["worksheet"]),
    )


async def save_snapshot(
    db: AsyncSession, matter_id: str, user_id: str, worksheet: PatentWorksheet
) -> PatentSnapshot:
    await require_matter(db, matter_id, user_id, write=True)
    row_id = str(uuid.uuid4())
    row = PatentSnapshot(
        id=row_id,
        matter_id=matter_id,
        created_by=user_id,
        ciphertext=encode_snapshot(row_id, matter_id, worksheet),
    )
    db.add(row)
    await db.flush()
    return row


async def read_latest(db: AsyncSession, matter_id: str, user_id: str) -> PatentSnapshot | None:
    await require_matter(db, matter_id, user_id)
    result = await db.execute(
        select(PatentSnapshot)
        .where(PatentSnapshot.matter_id == matter_id)
        .order_by(PatentSnapshot.created_at.desc(), PatentSnapshot.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
