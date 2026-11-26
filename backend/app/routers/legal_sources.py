"""Public legal sources (Counsel): read the operator-ingested copy of official
text, starting with the MPEP.

Read-only. Every signed-in user with ``tools.research`` may read it, because the
text is public government material, not tenant data. Responses carry the
official URL, the edition and revision the operator recorded, the section's own
revision marker, the fetch time and the SHA-256 of the stored text, so every
excerpt can be checked against its source. Nothing here calls a model or
fetches from the network; ingestion is an operator task
(``scripts/ingest_mpep.py``).
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import NotFoundError
from app.models.legal_sources import LegalSource, LegalSourceSection
from app.services.auth import TokenData
from app.services.legal_sources import search as source_search
from app.services.permissions import require_permission

router = APIRouter(prefix="/legal-sources", tags=["legal-sources"])


class LegalSourceOut(BaseModel):
    id: str
    name: str
    edition: str
    revision: str
    published_on: str | None
    source_url: str
    fetched_at: datetime
    section_count: int


class LegalSourceList(BaseModel):
    sources: list[LegalSourceOut]


class SectionHit(BaseModel):
    id: str
    section_id: str
    title: str
    revision_note: str
    url: str
    text_sha256: str
    fetched_at: datetime
    snippet: str


class SectionSearchResult(BaseModel):
    source: LegalSourceOut | None
    query: str
    results: list[SectionHit]


class SectionDetail(BaseModel):
    id: str
    section_id: str
    title: str
    revision_note: str
    url: str
    text_sha256: str
    fetched_at: datetime
    text: str
    source: LegalSourceOut


def _source_out(source: LegalSource, count: int) -> LegalSourceOut:
    return LegalSourceOut(
        id=source.id,
        name=source.name,
        edition=source.edition,
        revision=source.revision,
        published_on=source.published_on,
        source_url=source.source_url,
        fetched_at=source.fetched_at,
        section_count=count,
    )


def _hit(row: LegalSourceSection, text_snippet: str) -> SectionHit:
    return SectionHit(
        id=row.id,
        section_id=row.section_id,
        title=row.title,
        revision_note=row.revision_note,
        url=row.url,
        text_sha256=row.text_sha256,
        fetched_at=row.fetched_at,
        snippet=text_snippet,
    )


async def _sources(db: AsyncSession) -> dict[str, LegalSourceOut]:
    return {s.id: _source_out(s, n) for s, n in await source_search.list_sources(db)}


@router.get("", response_model=LegalSourceList)
async def list_legal_sources(
    current_user: TokenData = require_permission("tools.research"),
    db: AsyncSession = Depends(get_db),
) -> LegalSourceList:
    """Ingested sources, newest first, with their section counts (empty until an operator ingests)."""
    return LegalSourceList(sources=list((await _sources(db)).values()))


@router.get("/sections", response_model=SectionSearchResult)
async def search_legal_source_sections(
    q: str = Query(..., min_length=2, max_length=200),
    source_id: str | None = Query(None, max_length=36),
    limit: int = Query(20, ge=1, le=50),
    current_user: TokenData = require_permission("tools.research"),
    db: AsyncSession = Depends(get_db),
) -> SectionSearchResult:
    """A section number (``2106.04``) or words; defaults to the newest source."""
    sources = await _sources(db)
    if source_id is not None:
        source = await db.get(LegalSource, source_id)
        if source is None:
            raise NotFoundError("Source not found")
    else:
        source = await source_search.default_source(db)
    if source is None:
        return SectionSearchResult(source=None, query=q, results=[])
    hits = await source_search.search_sections(db, source, q, limit=limit)
    return SectionSearchResult(
        source=sources.get(source.id), query=q, results=[_hit(r, sn) for r, sn in hits]
    )


@router.get("/sections/{section_pk}", response_model=SectionDetail)
async def get_legal_source_section(
    section_pk: str,
    current_user: TokenData = require_permission("tools.research"),
    db: AsyncSession = Depends(get_db),
) -> SectionDetail:
    row = await source_search.get_section(db, section_pk)
    if row is None:
        raise NotFoundError("Section not found")
    source = (await _sources(db))[row.source_id]
    return SectionDetail(
        id=row.id,
        section_id=row.section_id,
        title=row.title,
        revision_note=row.revision_note,
        url=row.url,
        text_sha256=row.text_sha256,
        fetched_at=row.fetched_at,
        text=row.text,
        source=source,
    )
