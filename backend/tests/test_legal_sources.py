"""Public legal sources (Counsel): MPEP page parsing, the official-URL
allowlist, operator ingestion (idempotent per revision, never rewriting a
stored section) and the read-only search API.

No network: pages come from ``tests/fixtures/mpep``, which copies the layout of
an official MPEP page with section numbers (99xx) that do not exist in the
MPEP and placeholder text, so no invented legal text sits next to a real
section number.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-32chars!")
os.environ.setdefault("ENCRYPTION_SALT", "test-salt-16chars!")
os.environ.setdefault("DEBUG", "true")

import asyncio
from datetime import datetime
from pathlib import Path

import httpx
import pytest
from app.models.legal_sources import LegalSource, LegalSourceSection
from app.services.legal_sources.ingest import (
    FetchError,
    fetch_pages,
    ingest_pages,
    pages_from_dir,
)
from app.services.legal_sources.mpep import (
    DisallowedUrlError,
    check_mpep_url,
    discover_section_pages,
    parse_mpep_page,
    sha256_text,
)
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from tests.helpers import _sync_engine, headers, make_user

FIXTURES = Path(__file__).parent / "fixtures" / "mpep"
PAGE = (FIXTURES / "s9990.html").read_text(encoding="utf-8")
PAGE_URL = "https://www.uspto.gov/web/offices/pac/mpep/s9990.html"
INDEX_URL = "https://www.uspto.gov/web/offices/pac/mpep/mpep-9900.html"
BASE = "/api/v1/legal-sources"
EDITION = "Synthetic Fixture Edition"


# ------------------------------------------------------------------ parser


def test_parser_reads_headings_and_drops_navigation_scripts_and_contents():
    sections = parse_mpep_page(PAGE, PAGE_URL)
    assert [(s.section_id, s.title, s.revision_note) for s in sections] == [
        ("9990", "Synthetic Fixture Section", "R-01.2030"),
        ("9990.01", "Synthetic Subsection One", "R-02.2031"),
        ("9990.01(a)", "Synthetic Lettered Subsection", "R-02.2031"),
    ]
    first, _, lettered = sections
    assert first.text.startswith("FIXTURE TEXT ALPHA.")
    assert "I. FIXTURE HEADING" in first.text and "FIXTURE TEXT BETA" in first.text
    assert lettered.text == "FIXTURE TEXT DELTA about a widget."  # the reserved slot ends it
    every = "\n".join(s.text for s in sections)
    for leaked in ("Skip over navigation", "PATENTS", "var nav", "Footer navigation", "[top]"):
        assert leaked not in every
    assert "Another Synthetic Section" not in every  # the trailing table of contents
    assert all(s.url == PAGE_URL for s in sections)
    assert first.text_sha256 == sha256_text(first.text)


def test_parser_finds_nothing_rather_than_guessing_on_an_unknown_layout():
    assert parse_mpep_page("<html><body><p>Hello</p></body></html>", PAGE_URL) == []


def test_only_official_mpep_pages_are_allowed():
    assert check_mpep_url("https://WWW.USPTO.GOV/web/offices/pac/mpep/s2106.html") == (
        "https://www.uspto.gov/web/offices/pac/mpep/s2106.html"
    )
    for bad in (
        "http://www.uspto.gov/web/offices/pac/mpep/s2106.html",
        "https://www.uspto.gov.example.com/web/offices/pac/mpep/s2106.html",
        "https://uspto.gov/web/offices/pac/mpep/s2106.html",
        "https://www.uspto.gov/web/offices/pac/mpep/../x.html",
        "https://www.uspto.gov/web/offices/pac/mpep/sub/s2106.html",
        "https://www.uspto.gov/web/offices/pac/mpep/s2106.html?x=1",
        "https://www.uspto.gov/web/offices/pac/mpep/s2106.html#frag",
        "https://user@www.uspto.gov/web/offices/pac/mpep/s2106.html",
        "https://www.uspto.gov:8443/web/offices/pac/mpep/s2106.html",
        "https://www.uspto.gov/web/offices/pac/mpep/mpep-2100.pdf",
        "file:///etc/passwd",
    ):
        with pytest.raises(DisallowedUrlError):
            check_mpep_url(bad)
        with pytest.raises(DisallowedUrlError):
            parse_mpep_page(PAGE, bad)


def test_chapter_index_discovery_keeps_only_official_section_pages():
    index = (FIXTURES / "mpep-9900.html").read_text(encoding="utf-8")
    assert discover_section_pages(index, INDEX_URL) == [
        "https://www.uspto.gov/web/offices/pac/mpep/s9990.html",
        "https://www.uspto.gov/web/offices/pac/mpep/s9991.html",
        "https://www.uspto.gov/web/offices/pac/mpep/s9992-9993.html",
    ]


# ------------------------------------------------------------------ fetching


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


def test_fetch_returns_official_html_and_refuses_redirects_errors_and_non_html():
    seen: list[str] = []

    def ok(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, text=PAGE, headers={"content-type": "text/html; charset=utf-8"})

    pages = asyncio.run(fetch_pages([PAGE_URL], client=_client(ok), delay_seconds=0))
    assert pages == [(PAGE_URL, PAGE)] and seen == [PAGE_URL]

    def redirect(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://example.com/"})

    def not_html(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="{}", headers={"content-type": "application/json"})

    for handler in (redirect, not_html):
        with pytest.raises(FetchError):
            asyncio.run(fetch_pages([PAGE_URL], client=_client(handler), delay_seconds=0))

    def never(request: httpx.Request) -> httpx.Response:  # pragma: no cover - must not run
        raise AssertionError("fetched a disallowed URL")

    with pytest.raises(DisallowedUrlError):
        asyncio.run(
            fetch_pages(["https://example.com/s1.html"], client=_client(never), delay_seconds=0)
        )


def test_saved_pages_map_back_to_official_urls():
    pages = pages_from_dir(FIXTURES)
    assert [u for u, _ in pages] == [
        "https://www.uspto.gov/web/offices/pac/mpep/mpep-9900.html",
        "https://www.uspto.gov/web/offices/pac/mpep/s9990.html",
    ]


# ------------------------------------------------------------------ ingestion


@pytest.fixture
def tables():
    """The two tables on the suite's SQLite file, emptied around each test."""
    from app.models.base import Base

    engine = _sync_engine()
    meta = Base.metadata
    meta.create_all(
        engine,
        tables=[meta.tables["legal_sources"], meta.tables["legal_source_sections"]],
        checkfirst=True,
    )

    def wipe():
        with Session(engine) as session:
            session.execute(delete(LegalSourceSection))
            session.execute(delete(LegalSource))
            session.commit()

    wipe()
    yield engine
    wipe()
    engine.dispose()


def _ingest(pages, *, revision="01.2030", dry_run=False, now=None):
    from app.database import async_engine

    async def run():
        engine = create_async_engine(str(async_engine.url))
        try:
            factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
            async with factory() as session:
                return await ingest_pages(
                    session,
                    pages,
                    name="MPEP",
                    edition=EDITION,
                    revision=revision,
                    published_on="Fixture month",
                    source_url=INDEX_URL,
                    dry_run=dry_run,
                    now=now,
                )
        finally:
            await engine.dispose()

    return asyncio.run(run())


def _count(engine, model) -> int:
    with Session(engine) as session:
        return session.query(model).count()


def test_ingest_is_idempotent_per_revision_and_never_rewrites_a_section(tables):
    first = _ingest([(PAGE_URL, PAGE)])
    assert first.as_dict() == {
        "pages": 1,
        "sections_seen": 3,
        "added": 3,
        "unchanged": 0,
        "conflicts": [],
        "empty_pages": [],
    }
    again = _ingest([(PAGE_URL, PAGE)])
    assert (again.added, again.unchanged, again.conflicts) == (0, 3, [])
    assert _count(tables, LegalSource) == 1 and _count(tables, LegalSourceSection) == 3

    # The page now prints different text under the same revision label.
    edited = PAGE.replace("FIXTURE TEXT GAMMA", "FIXTURE TEXT GAMMA EDITED")
    conflict = _ingest([(PAGE_URL, edited)])
    assert conflict.conflicts == ["9990.01"] and conflict.added == 0
    with Session(tables) as session:
        stored = session.query(LegalSourceSection).filter_by(section_id="9990.01").one()
        assert stored.text == "FIXTURE TEXT GAMMA about a sprocket."  # unchanged

    # A new revision label is a new source with its own rows.
    newer = _ingest([(PAGE_URL, edited)], revision="02.2031")
    assert newer.added == 3
    assert _count(tables, LegalSource) == 2 and _count(tables, LegalSourceSection) == 6


def test_dry_run_stores_nothing_and_empty_pages_are_reported(tables):
    empty_url = "https://www.uspto.gov/web/offices/pac/mpep/s9991.html"
    report = _ingest([(PAGE_URL, PAGE), (empty_url, "<p>no headings</p>")], dry_run=True)
    assert report.added == 3 and report.empty_pages == [empty_url]
    assert _count(tables, LegalSource) == 0 and _count(tables, LegalSourceSection) == 0


def test_ingest_requires_an_edition_and_revision(tables):
    with pytest.raises(ValueError):
        _ingest([(PAGE_URL, PAGE)], revision=" ")


# ------------------------------------------------------------------ API


def test_api_is_empty_until_an_operator_ingests(client, tables):
    user = make_user("src-empty")
    resp = client.get(BASE, headers=headers(user))
    assert resp.status_code == 200 and resp.json() == {"sources": []}
    found = client.get(f"{BASE}/sections", headers=headers(user), params={"q": "widget"})
    assert found.status_code == 200
    assert found.json() == {"source": None, "query": "widget", "results": []}


def test_api_searches_by_section_number_and_words_and_returns_provenance(client, tables):
    when = datetime(2030, 1, 2, 3, 4, 5)
    _ingest([(PAGE_URL, PAGE)], now=when)
    user = make_user("src-reader")

    sources = client.get(BASE, headers=headers(user)).json()["sources"]
    assert len(sources) == 1
    source = sources[0]
    assert source["edition"] == EDITION and source["revision"] == "01.2030"
    assert source["section_count"] == 3 and source["source_url"] == INDEX_URL

    by_number = client.get(f"{BASE}/sections", headers=headers(user), params={"q": "§ 9990.01"})
    assert [r["section_id"] for r in by_number.json()["results"]] == ["9990.01", "9990.01(a)"]

    by_words = client.get(f"{BASE}/sections", headers=headers(user), params={"q": "widget"})
    hits = by_words.json()["results"]
    # Both mention a widget; 9990 mentions it more often.
    assert [h["section_id"] for h in hits] == ["9990", "9990.01(a)"]
    top = hits[0]
    assert top["url"] == PAGE_URL and top["revision_note"] == "R-01.2030"
    assert top["fetched_at"].startswith("2030-01-02T03:04:05")
    assert "widget" in top["snippet"].lower() and len(top["text_sha256"]) == 64

    both = client.get(f"{BASE}/sections", headers=headers(user), params={"q": "widget sprocket"})
    assert both.json()["results"] == []  # every word must match

    detail = client.get(f"{BASE}/sections/{top['id']}", headers=headers(user)).json()
    assert detail["text"].startswith("FIXTURE TEXT ALPHA.")
    assert detail["text_sha256"] == sha256_text(detail["text"])
    assert detail["source"]["id"] == source["id"]

    assert client.get(f"{BASE}/sections/missing", headers=headers(user)).status_code == 404
    unknown = client.get(
        f"{BASE}/sections", headers=headers(user), params={"q": "widget", "source_id": "nope"}
    )
    assert unknown.status_code == 404


def test_api_needs_a_signed_in_user_and_a_real_query(client, tables):
    from app.services.auth import UserRole

    viewer = make_user("src-viewer", UserRole.VIEWER)  # viewers hold tools.research
    assert client.get(BASE, headers=headers(viewer)).status_code == 200
    assert client.get(BASE).status_code == 401
    assert (
        client.get(f"{BASE}/sections", headers=headers(viewer), params={"q": "x"}).status_code
        == 422
    )
