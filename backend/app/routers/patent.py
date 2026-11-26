"""Patent Studio endpoints (Counsel): matter-scoped workspaces holding an
invention disclosure (append-only versions) and a claim-element evidence chart.

Access follows the other work-product routers: the owner or a member of the
workspace's matter may read; the owner alone writes and deletes. Anyone else —
including a walled user — gets 404, never 403. Every workspace is filed under
a matter the caller can access at creation time.

These endpoints store what a reviewer typed. They do not call a model, verify
references or draw any conclusion about patentability. Audit entries carry ids,
versions and counts only — never disclosure or claim text.
"""

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import NotFoundError
from app.models.patent import ClaimElement, InventionDisclosure, PatentWorkspace
from app.routers._matter_deps import accessible_matter_ids
from app.services.audit import AuditEventType, audit_service
from app.services.auth import TokenData
from app.services.patent import patent_workspace_service as svc
from app.services.permissions import require_permission
from app.utils.ip_resolution import get_client_ip

router = APIRouter(prefix="/patent-workspaces", tags=["patent-studio"])

MAX_ELEMENTS = 50
ElementStatus = Literal["unreviewed", "candidate", "gap", "unclear"]


# ------------------------------------------------------------------ schemas


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DisclosureFields(_Strict):
    title: str = Field("", max_length=12000)
    problem: str = Field("", max_length=12000)
    solution: str = Field("", max_length=12000)
    alternatives: str = Field("", max_length=12000)
    disclosures: str = Field("", max_length=12000)
    contributions: str = Field("", max_length=12000)
    officeAction: str = Field("", max_length=12000)


class ClaimElementIn(_Strict):
    element: str = Field("", max_length=6000)
    disclosureSupport: str = Field("", max_length=6000)
    reference: str = Field("", max_length=1000)
    referencePassage: str = Field("", max_length=6000)
    status: ElementStatus = "unreviewed"
    notes: str = Field("", max_length=6000)


class WorkspaceCreate(_Strict):
    matter_id: str = Field(..., min_length=1, max_length=36)
    title: str = Field(..., min_length=1, max_length=200)


class WorkspaceUpdate(_Strict):
    title: str | None = Field(None, min_length=1, max_length=200)
    reviewer_notes: str | None = Field(None, max_length=12000)


class DisclosureSave(_Strict):
    fields: DisclosureFields


class ElementsReplace(_Strict):
    elements: list[ClaimElementIn] = Field(default_factory=list, max_length=MAX_ELEMENTS)


class DisclosureVersionOut(BaseModel):
    version: int
    content_sha256: str
    created_by: str
    created_at: datetime


class DisclosureOut(DisclosureVersionOut):
    fields: DisclosureFields


class ClaimElementOut(BaseModel):
    id: str
    position: int
    element: str
    disclosureSupport: str
    reference: str
    referencePassage: str
    status: str
    notes: str
    verified: bool


class WorkspaceSummary(BaseModel):
    id: str
    matter_id: str
    title: str
    role: str
    created_at: datetime
    updated_at: datetime | None


class WorkspaceList(BaseModel):
    workspaces: list[WorkspaceSummary]


class WorkspaceDetail(WorkspaceSummary):
    reviewer_notes: str
    disclosure: DisclosureOut | None
    disclosure_versions: int
    elements: list[ClaimElementOut]


class DisclosureSaved(BaseModel):
    created: bool
    disclosure: DisclosureOut


class DisclosureVersionList(BaseModel):
    versions: list[DisclosureVersionOut]


# ------------------------------------------------------------------ helpers


async def _audit(
    request: Request,
    current_user: TokenData,
    event_type: AuditEventType,
    action: str,
    workspace_id: str,
    **details: Any,
) -> None:
    """Ids, versions and counts only — never disclosure or claim text."""
    await audit_service.log_event(
        event_type=event_type,
        user_id=current_user.user_id,
        user_email=current_user.email,
        resource_type="patent_workspace",
        resource_id=workspace_id,
        ip_address=get_client_ip(request),
        details={"action": action, **details},
    )


async def _require_readable(
    db: AsyncSession, workspace_id: str, user: TokenData, matter_ids: set[str]
) -> PatentWorkspace:
    ws = await svc.get_accessible(db, workspace_id, user.user_id, matter_ids)
    if ws is None:
        raise NotFoundError("Patent workspace not found")
    return ws


async def _require_owned(
    db: AsyncSession, workspace_id: str, user: TokenData, matter_ids: set[str]
) -> PatentWorkspace:
    ws = await _require_readable(db, workspace_id, user, matter_ids)
    if ws.owner_id != user.user_id:
        raise NotFoundError("Patent workspace not found")
    return ws


def _summary(ws: PatentWorkspace, user_id: str) -> WorkspaceSummary:
    return WorkspaceSummary(
        id=ws.id,
        matter_id=ws.matter_id,
        title=ws.title,
        role=svc.role_for(ws, user_id),
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )


def _disclosure_out(version: InventionDisclosure) -> DisclosureOut:
    return DisclosureOut(
        version=version.version,
        content_sha256=version.content_sha256,
        created_by=version.created_by,
        created_at=version.created_at,
        fields=DisclosureFields(**svc.disclosure_fields(version)),
    )


def _element_out(element: ClaimElement) -> ClaimElementOut:
    return ClaimElementOut(
        id=element.id,
        position=element.position,
        status=element.status,
        verified=bool(element.verified),
        **svc.element_payload(element),
    )


async def _detail(db: AsyncSession, ws: PatentWorkspace, user_id: str) -> WorkspaceDetail:
    latest = await svc.latest_disclosure(db, ws.id)
    elements = await svc.elements(db, ws.id)
    return WorkspaceDetail(
        **_summary(ws, user_id).model_dump(),
        reviewer_notes=svc.reviewer_notes(ws),
        disclosure=_disclosure_out(latest) if latest else None,
        disclosure_versions=await svc.disclosure_count(db, ws.id),
        elements=[_element_out(e) for e in elements],
    )


# ---------------------------------------------------------------- endpoints


@router.get("", response_model=WorkspaceList)
async def list_patent_workspaces(
    matter_id: str | None = Query(None, max_length=36),
    current_user: TokenData = require_permission("contracts.use"),
    db: AsyncSession = Depends(get_db),
    matter_ids: set[str] = Depends(accessible_matter_ids),
) -> WorkspaceList:
    """Workspaces the caller owns or can see through a matter, optionally one matter's."""
    rows = await svc.list_for_user(db, current_user.user_id, matter_ids, matter_id)
    return WorkspaceList(workspaces=[_summary(ws, current_user.user_id) for ws in rows])


@router.post("", response_model=WorkspaceDetail, status_code=201)
async def create_patent_workspace(
    body: WorkspaceCreate,
    request: Request,
    current_user: TokenData = require_permission("contracts.use"),
    db: AsyncSession = Depends(get_db),
    matter_ids: set[str] = Depends(accessible_matter_ids),
) -> WorkspaceDetail:
    if body.matter_id not in matter_ids:
        raise NotFoundError("Matter not found")
    ws = await svc.create(
        db, owner_id=current_user.user_id, matter_id=body.matter_id, title=body.title
    )
    await _audit(
        request,
        current_user,
        AuditEventType.DATA_MODIFICATION,
        "patent_workspace_created",
        ws.id,
        matter_id=ws.matter_id,
    )
    return await _detail(db, ws, current_user.user_id)


@router.get("/{workspace_id}", response_model=WorkspaceDetail)
async def get_patent_workspace(
    workspace_id: str,
    current_user: TokenData = require_permission("contracts.use"),
    db: AsyncSession = Depends(get_db),
    matter_ids: set[str] = Depends(accessible_matter_ids),
) -> WorkspaceDetail:
    ws = await _require_readable(db, workspace_id, current_user, matter_ids)
    return await _detail(db, ws, current_user.user_id)


@router.patch("/{workspace_id}", response_model=WorkspaceDetail)
async def update_patent_workspace(
    workspace_id: str,
    body: WorkspaceUpdate,
    request: Request,
    current_user: TokenData = require_permission("contracts.use"),
    db: AsyncSession = Depends(get_db),
    matter_ids: set[str] = Depends(accessible_matter_ids),
) -> WorkspaceDetail:
    ws = await _require_owned(db, workspace_id, current_user, matter_ids)
    ws = await svc.update(db, ws, title=body.title, reviewer_notes=body.reviewer_notes)
    await _audit(
        request,
        current_user,
        AuditEventType.DATA_MODIFICATION,
        "patent_workspace_updated",
        ws.id,
        changed=sorted(body.model_dump(exclude_unset=True)),
    )
    return await _detail(db, ws, current_user.user_id)


@router.delete("/{workspace_id}")
async def delete_patent_workspace(
    workspace_id: str,
    request: Request,
    current_user: TokenData = require_permission("contracts.use"),
    db: AsyncSession = Depends(get_db),
    matter_ids: set[str] = Depends(accessible_matter_ids),
) -> dict[str, str]:
    ws = await _require_owned(db, workspace_id, current_user, matter_ids)
    await svc.delete(db, ws)
    await _audit(
        request,
        current_user,
        AuditEventType.DATA_DELETION,
        "patent_workspace_deleted",
        workspace_id,
    )
    return {"status": "deleted", "id": workspace_id}


@router.post("/{workspace_id}/disclosures", response_model=DisclosureSaved)
async def save_disclosure(
    workspace_id: str,
    body: DisclosureSave,
    request: Request,
    current_user: TokenData = require_permission("contracts.use"),
    db: AsyncSession = Depends(get_db),
    matter_ids: set[str] = Depends(accessible_matter_ids),
) -> DisclosureSaved:
    """Append a new version; an unchanged disclosure returns the latest (created=false)."""
    ws = await _require_owned(db, workspace_id, current_user, matter_ids)
    version, created = await svc.save_disclosure(
        db, ws, body.fields.model_dump(), current_user.user_id
    )
    if created:
        await _audit(
            request,
            current_user,
            AuditEventType.DATA_MODIFICATION,
            "invention_disclosure_saved",
            ws.id,
            version=version.version,
        )
    return DisclosureSaved(created=created, disclosure=_disclosure_out(version))


@router.get("/{workspace_id}/disclosures", response_model=DisclosureVersionList)
async def list_disclosure_versions(
    workspace_id: str,
    current_user: TokenData = require_permission("contracts.use"),
    db: AsyncSession = Depends(get_db),
    matter_ids: set[str] = Depends(accessible_matter_ids),
) -> DisclosureVersionList:
    ws = await _require_readable(db, workspace_id, current_user, matter_ids)
    versions = await svc.disclosure_versions(db, ws.id)
    return DisclosureVersionList(
        versions=[
            DisclosureVersionOut(
                version=v.version,
                content_sha256=v.content_sha256,
                created_by=v.created_by,
                created_at=v.created_at,
            )
            for v in versions
        ]
    )


@router.get("/{workspace_id}/disclosures/{version}", response_model=DisclosureOut)
async def get_disclosure_version(
    workspace_id: str,
    version: int,
    current_user: TokenData = require_permission("contracts.use"),
    db: AsyncSession = Depends(get_db),
    matter_ids: set[str] = Depends(accessible_matter_ids),
) -> DisclosureOut:
    ws = await _require_readable(db, workspace_id, current_user, matter_ids)
    for v in await svc.disclosure_versions(db, ws.id):
        if v.version == version:
            return _disclosure_out(v)
    raise NotFoundError("Disclosure version not found")


@router.put("/{workspace_id}/claim-elements", response_model=list[ClaimElementOut])
async def replace_claim_elements(
    workspace_id: str,
    body: ElementsReplace,
    request: Request,
    current_user: TokenData = require_permission("contracts.use"),
    db: AsyncSession = Depends(get_db),
    matter_ids: set[str] = Depends(accessible_matter_ids),
) -> list[ClaimElementOut]:
    """Replace the claim chart, in order. No field can mark a row verified."""
    ws = await _require_owned(db, workspace_id, current_user, matter_ids)
    rows = await svc.replace_elements(
        db, ws, [e.model_dump() for e in body.elements], current_user.user_id
    )
    await _audit(
        request,
        current_user,
        AuditEventType.DATA_MODIFICATION,
        "claim_elements_saved",
        ws.id,
        count=len(rows),
    )
    return [_element_out(e) for e in rows]
