"""Search the stored copy of public legal sources.

Plain SQL matching over ``legal_source_sections``: a section number finds
that section and its subsections; words find sections containing every word
(title or text), ranked by how often they occur, title matches first. This
runs entirely inside the database: it never calls a model, never touches the
tenant vector store or lexical index, and returns stored text only, with the
URL, revision and hash needed to check it against the official page.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import and_, func, or_, select

from app.models.legal_sources import LegalSource, LegalSourceSection

_SECTION_QUERY = re.compile(r"^(?:mpep\s*)?(?:§\s*)?(\d{3,4}(?:\.\d{1,2})?(?:\([a-z0-9]{1,3}\))*)$")
_WORD = re.compile(r"[a-z0-9][a-z0-9'’-]*", re.IGNORECASE)
_PREFILTER_LIMIT = 300
SNIPPET_CHARS = 280


def query_terms(q: str) -> list[str]:
    seen: list[str] = []
    for word in _WORD.findall(q.lower()):
        if len(word) >= 3 and word not in seen:
            seen.append(word)
    return seen[:8]


def section_number(q: str) -> str | None:
    match = _SECTION_QUERY.match(q.strip().lower())
    return match.group(1) if match else None


def snippet(text: str, terms: list[str]) -> str:
    lower = text.lower()
    positions = [lower.find(t) for t in terms if lower.find(t) >= 0]
    start = max(min(positions) - 80, 0) if positions else 0
    piece = text[start : start + SNIPPET_CHARS].strip()
    prefix = "…" if start > 0 else ""
    suffix = "…" if start + SNIPPET_CHARS < len(text) else ""
    return f"{prefix}{piece}{suffix}"


async def list_sources(session: Any) -> list[tuple[LegalSource, int]]:
    counts = (
        select(LegalSourceSection.source_id, func.count(LegalSourceSection.id).label("n"))
        .group_by(LegalSourceSection.source_id)
        .subquery()
    )
    rows = await session.execute(
        select(LegalSource, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.source_id == LegalSource.id)
        .order_by(LegalSource.created_at.desc())
    )
    return [(source, int(n)) for source, n in rows.all()]


async def default_source(session: Any) -> LegalSource | None:
    rows = await session.execute(
        select(LegalSource).order_by(LegalSource.created_at.desc()).limit(1)
    )
    source: LegalSource | None = rows.scalars().first()
    return source


async def search_sections(
    session: Any, source: LegalSource, q: str, limit: int = 20
) -> list[tuple[LegalSourceSection, str]]:
    """(section, snippet) pairs, best first."""
    number = section_number(q)
    if number is not None:
        rows = await session.execute(
            select(LegalSourceSection)
            .where(
                LegalSourceSection.source_id == source.id,
                or_(
                    LegalSourceSection.section_id == number,
                    LegalSourceSection.section_id.startswith(number + ".", autoescape=True),
                    LegalSourceSection.section_id.startswith(number + "(", autoescape=True),
                ),
            )
            .order_by(LegalSourceSection.section_id)
            .limit(limit)
        )
        return [(row, snippet(row.text, [])) for row in rows.scalars().all()]

    terms = query_terms(q)
    if not terms:
        return []
    title = func.lower(LegalSourceSection.title)
    body = func.lower(LegalSourceSection.text)
    conditions = [
        or_(title.contains(t, autoescape=True), body.contains(t, autoescape=True)) for t in terms
    ]
    rows = await session.execute(
        select(LegalSourceSection)
        .where(LegalSourceSection.source_id == source.id, and_(*conditions))
        .limit(_PREFILTER_LIMIT)
    )

    def score(row: LegalSourceSection) -> tuple[int, int, str]:
        t, b = row.title.lower(), row.text.lower()
        return (-sum(t.count(x) for x in terms), -sum(b.count(x) for x in terms), row.section_id)

    ranked = sorted(rows.scalars().all(), key=score)[:limit]
    return [(row, snippet(row.text, terms)) for row in ranked]


async def get_section(session: Any, section_pk: str) -> LegalSourceSection | None:
    row: LegalSourceSection | None = await session.get(LegalSourceSection, section_pk)
    return row
