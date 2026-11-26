"""Operator-run ingestion of official MPEP pages into ``legal_sources``.

Only ``scripts/ingest_mpep.py`` calls this; no request path does. Fetching is
limited to https pages under ``https://www.uspto.gov/web/offices/pac/mpep/``
(``check_mpep_url``), redirects are not followed, and requests are spaced out.
An operator can also ingest pages saved to a local directory (offline, or to
review exactly what will be stored first).

Idempotent per revision. Re-running the same edition and revision adds only
sections that are missing. A stored section is never rewritten: when the page
now prints different text under the same revision, it is reported as a
conflict and left as it was, so the operator can ingest it under a new
revision label instead. A new revision is a new source with its own rows.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.models.legal_sources import LegalSource, LegalSourceSection
from app.services.legal_sources.mpep import (
    MPEP_BASE_URL,
    DisallowedUrlError,
    ParsedSection,
    check_mpep_url,
    parse_mpep_page,
)

USER_AGENT = "SmartProBono-Counsel-MPEP-ingest (operator-run; contact: instance operator)"
MAX_PAGE_BYTES = 8 * 1024 * 1024


@dataclass
class IngestReport:
    pages: int = 0
    sections_seen: int = 0
    added: int = 0
    unchanged: int = 0
    conflicts: list[str] = field(default_factory=list)
    empty_pages: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "pages": self.pages,
            "sections_seen": self.sections_seen,
            "added": self.added,
            "unchanged": self.unchanged,
            "conflicts": list(self.conflicts),
            "empty_pages": list(self.empty_pages),
        }


class FetchError(RuntimeError):
    """A page could not be fetched as official HTML."""


async def fetch_pages(
    urls: Iterable[str], *, client: Any = None, delay_seconds: float = 1.0
) -> list[tuple[str, str]]:
    """Fetch each official page in order. Any non-200, redirect or non-HTML stops the run."""
    import httpx

    checked = [check_mpep_url(u) for u in urls]
    own = client is None
    http = client or httpx.AsyncClient(
        follow_redirects=False, timeout=30.0, headers={"User-Agent": USER_AGENT}
    )
    out: list[tuple[str, str]] = []
    try:
        for index, url in enumerate(checked):
            if index and delay_seconds:
                await asyncio.sleep(delay_seconds)
            response = await http.get(url)
            if response.status_code != 200:
                raise FetchError(f"{url}: HTTP {response.status_code}")
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type.lower():
                raise FetchError(f"{url}: not HTML ({content_type or 'no content type'})")
            if len(response.content) > MAX_PAGE_BYTES:
                raise FetchError(f"{url}: larger than {MAX_PAGE_BYTES} bytes")
            out.append((url, response.text))
    finally:
        if own:
            await http.aclose()
    return out


def pages_from_dir(directory: Path) -> list[tuple[str, str]]:
    """Saved pages, named as on the site (``s2106.html``), mapped back to their official URLs."""
    pages: list[tuple[str, str]] = []
    for path in sorted(directory.glob("*.html")):
        url = check_mpep_url(MPEP_BASE_URL + path.name)
        pages.append((url, path.read_text(encoding="utf-8", errors="replace")))
    return pages


async def get_or_create_source(
    session: Any,
    *,
    name: str,
    edition: str,
    revision: str,
    published_on: str | None,
    source_url: str,
    now: datetime,
) -> LegalSource:
    found = await session.execute(
        select(LegalSource).where(
            LegalSource.name == name,
            LegalSource.edition == edition,
            LegalSource.revision == revision,
        )
    )
    source: LegalSource | None = found.scalars().first()
    if source is None:
        source = LegalSource(
            id=str(uuid.uuid4()),
            name=name,
            edition=edition,
            revision=revision,
            published_on=published_on,
            source_url=source_url,
            created_at=now,
            fetched_at=now,
        )
        session.add(source)
        await session.flush()
    return source


async def ingest_pages(
    session: Any,
    pages: Iterable[tuple[str, str]],
    *,
    name: str,
    edition: str,
    revision: str,
    published_on: str | None,
    source_url: str,
    now: datetime | None = None,
    dry_run: bool = False,
) -> IngestReport:
    """Parse ``pages`` and store new sections under the given edition and revision."""
    if not name.strip() or not edition.strip() or not revision.strip():
        raise ValueError("name, edition and revision are required")
    now = now or datetime.utcnow()
    report = IngestReport()
    parsed: list[ParsedSection] = []
    for url, page_html in pages:
        report.pages += 1
        sections = parse_mpep_page(page_html, url)
        if not sections:
            report.empty_pages.append(url)
        parsed.extend(sections)
    report.sections_seen = len(parsed)

    source = await get_or_create_source(
        session,
        name=name.strip(),
        edition=edition.strip(),
        revision=revision.strip(),
        published_on=(published_on or "").strip() or None,
        source_url=check_mpep_url(source_url),
        now=now,
    )
    existing_rows = await session.execute(
        select(LegalSourceSection).where(LegalSourceSection.source_id == source.id)
    )
    existing = {row.section_id: row for row in existing_rows.scalars().all()}

    for section in parsed:
        stored = existing.get(section.section_id)
        if stored is not None:
            if stored.text_sha256 == section.text_sha256:
                report.unchanged += 1
            elif section.section_id not in report.conflicts:
                report.conflicts.append(section.section_id)
            continue
        row = LegalSourceSection(
            id=str(uuid.uuid4()),
            source_id=source.id,
            section_id=section.section_id,
            title=section.title[:500],
            text=section.text,
            text_sha256=section.text_sha256,
            url=section.url,
            revision_note=section.revision_note,
            fetched_at=now,
        )
        session.add(row)
        existing[section.section_id] = row
        report.added += 1

    source.fetched_at = now
    if dry_run:
        await session.rollback()
    else:
        await session.commit()
    return report


__all__ = [
    "DisallowedUrlError",
    "FetchError",
    "IngestReport",
    "fetch_pages",
    "ingest_pages",
    "pages_from_dir",
]
