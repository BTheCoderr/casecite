"""Patent Studio persistence: matter-scoped workspaces, append-only disclosure
versions and the claim-element chart.

Access mirrors the other work-product services: the owner, or a member of the
workspace's matter (walls already subtracted from membership), may read; only
the owner writes or deletes. Callers turn "no access" into a 404.

Free text is encrypted at rest with ``encryption_service``; the service only
decrypts when building a response for someone who may read it. Nothing here
interprets the text.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select

from app.models.patent import (
    DISCLOSURE_KEYS,
    ClaimElement,
    InventionDisclosure,
    PatentWorkspace,
)
from app.services.encryption import encryption_service

ELEMENT_TEXT_KEYS = ("element", "disclosureSupport", "reference", "referencePassage", "notes")


def _encrypt_json(value: dict[str, str]) -> str:
    return encryption_service.encrypt_string(json.dumps(value, sort_keys=True))


def _decrypt_json(value: str) -> dict[str, str]:
    loaded = json.loads(encryption_service.decrypt_string(value))
    return {str(k): str(v) for k, v in loaded.items()} if isinstance(loaded, dict) else {}


def disclosure_sha256(fields: dict[str, str]) -> str:
    """Hash of the canonical disclosure (every key, sorted), so an unchanged
    save is recognisable and a version can be identified without decrypting."""
    canonical = {k: fields.get(k, "") for k in DISCLOSURE_KEYS}
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


class PatentWorkspaceService:
    @staticmethod
    def can_read(ws: PatentWorkspace, user_id: str, matter_ids: set[str] | None) -> bool:
        if ws.owner_id == user_id:
            return True
        return bool(matter_ids and ws.matter_id in matter_ids)

    @staticmethod
    def role_for(ws: PatentWorkspace, user_id: str) -> str:
        return "owner" if ws.owner_id == user_id else "member"

    async def create(
        self, session: Any, *, owner_id: str, matter_id: str, title: str
    ) -> PatentWorkspace:
        now = datetime.utcnow()
        ws = PatentWorkspace(
            id=str(uuid.uuid4()),
            owner_id=owner_id,
            matter_id=matter_id,
            title=title.strip(),
            created_at=now,
            updated_at=now,
        )
        session.add(ws)
        await session.commit()
        await session.refresh(ws)
        return ws

    async def list_for_user(
        self, session: Any, user_id: str, matter_ids: set[str] | None, matter_id: str | None
    ) -> list[PatentWorkspace]:
        clause = PatentWorkspace.owner_id == user_id
        if matter_ids:
            clause = clause | PatentWorkspace.matter_id.in_(sorted(matter_ids))
        query = select(PatentWorkspace).where(clause)
        if matter_id is not None:
            query = query.where(PatentWorkspace.matter_id == matter_id)
        rows = await session.execute(query.order_by(PatentWorkspace.updated_at.desc()))
        return list(rows.scalars().all())

    async def get_accessible(
        self, session: Any, workspace_id: str, user_id: str, matter_ids: set[str] | None
    ) -> PatentWorkspace | None:
        ws: PatentWorkspace | None = await session.get(PatentWorkspace, workspace_id)
        if ws is None or not self.can_read(ws, user_id, matter_ids):
            return None
        return ws

    # ------------------------------------------------------------ workspace

    async def update(
        self,
        session: Any,
        ws: PatentWorkspace,
        *,
        title: str | None,
        reviewer_notes: str | None,
    ) -> PatentWorkspace:
        if title is not None:
            ws.title = title.strip()
        if reviewer_notes is not None:
            ws.reviewer_notes_enc = (
                encryption_service.encrypt_string(reviewer_notes) if reviewer_notes else None
            )
        ws.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(ws)
        return ws

    @staticmethod
    def reviewer_notes(ws: PatentWorkspace) -> str:
        if not ws.reviewer_notes_enc:
            return ""
        return encryption_service.decrypt_string(ws.reviewer_notes_enc)

    async def delete(self, session: Any, ws: PatentWorkspace) -> None:
        # Explicit so SQLite without foreign-key enforcement also drops the children.
        await session.execute(delete(ClaimElement).where(ClaimElement.workspace_id == ws.id))
        await session.execute(
            delete(InventionDisclosure).where(InventionDisclosure.workspace_id == ws.id)
        )
        await session.delete(ws)
        await session.commit()

    # ----------------------------------------------------------- disclosure

    async def latest_disclosure(
        self, session: Any, workspace_id: str
    ) -> InventionDisclosure | None:
        rows = await session.execute(
            select(InventionDisclosure)
            .where(InventionDisclosure.workspace_id == workspace_id)
            .order_by(InventionDisclosure.version.desc())
            .limit(1)
        )
        return rows.scalars().first()

    async def disclosure_versions(
        self, session: Any, workspace_id: str
    ) -> list[InventionDisclosure]:
        rows = await session.execute(
            select(InventionDisclosure)
            .where(InventionDisclosure.workspace_id == workspace_id)
            .order_by(InventionDisclosure.version.desc())
        )
        return list(rows.scalars().all())

    async def disclosure_count(self, session: Any, workspace_id: str) -> int:
        result = await session.execute(
            select(func.count(InventionDisclosure.id)).where(
                InventionDisclosure.workspace_id == workspace_id
            )
        )
        return int(result.scalar() or 0)

    async def save_disclosure(
        self, session: Any, ws: PatentWorkspace, fields: dict[str, str], user_id: str
    ) -> tuple[InventionDisclosure, bool]:
        """Append a version unless the content equals the latest one.
        Returns (version, created)."""
        canonical = {k: fields.get(k, "") for k in DISCLOSURE_KEYS}
        digest = disclosure_sha256(canonical)
        latest = await self.latest_disclosure(session, ws.id)
        if latest is not None and latest.content_sha256 == digest:
            return latest, False
        version = InventionDisclosure(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            version=(latest.version + 1) if latest else 1,
            fields_enc=_encrypt_json(canonical),
            content_sha256=digest,
            created_by=user_id,
            created_at=datetime.utcnow(),
        )
        session.add(version)
        ws.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(version)
        return version, True

    @staticmethod
    def disclosure_fields(version: InventionDisclosure) -> dict[str, str]:
        stored = _decrypt_json(version.fields_enc)
        return {k: stored.get(k, "") for k in DISCLOSURE_KEYS}

    # ---------------------------------------------------------- claim chart

    async def elements(self, session: Any, workspace_id: str) -> list[ClaimElement]:
        rows = await session.execute(
            select(ClaimElement)
            .where(ClaimElement.workspace_id == workspace_id)
            .order_by(ClaimElement.position)
        )
        return list(rows.scalars().all())

    async def replace_elements(
        self, session: Any, ws: PatentWorkspace, rows: list[dict[str, str]], user_id: str
    ) -> list[ClaimElement]:
        """Replace the chart with ``rows`` in order. ``verified`` always starts
        False: only server-side verification may set it."""
        await session.execute(delete(ClaimElement).where(ClaimElement.workspace_id == ws.id))
        now = datetime.utcnow()
        for position, row in enumerate(rows):
            element = ClaimElement(
                id=str(uuid.uuid4()),
                workspace_id=ws.id,
                position=position,
                payload_enc=_encrypt_json({k: row.get(k, "") for k in ELEMENT_TEXT_KEYS}),
                status=row.get("status", "unreviewed"),
                verified=False,
                updated_by=user_id,
                updated_at=now,
            )
            session.add(element)
        ws.updated_at = now
        await session.commit()
        return await self.elements(session, ws.id)

    @staticmethod
    def element_payload(element: ClaimElement) -> dict[str, str]:
        stored = _decrypt_json(element.payload_enc)
        return {k: stored.get(k, "") for k in ELEMENT_TEXT_KEYS}


patent_workspace_service = PatentWorkspaceService()
