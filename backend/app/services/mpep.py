"""Read-only, bounded USPTO page corpus. No tenant documents or outbound calls."""

import hashlib
import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.services.quote_verify import find_quote_offset

BASE_URL = "https://www.uspto.gov/web/offices/pac/mpep/"
SECTIONS = ("2106", "2131", "2141", "2163", "2164", "2109", "2109.01", "714")
MAX_BYTES = 16 * 1024 * 1024


def source_url(section: str) -> str:
    if section not in SECTIONS:
        raise ValueError("Unknown MPEP page")
    return BASE_URL + "s" + section + ".html"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Page(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section: str
    heading: str = Field(min_length=1, max_length=500)
    url: str
    fetched_at: str
    text: str = Field(min_length=100, max_length=1_000_000)
    sha256: str
    html_sha256: str


class Corpus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    edition_label: str = Field(min_length=1, max_length=100)
    pages: list[Page] = Field(min_length=1, max_length=8)


class Hit(BaseModel):
    section: str
    heading: str
    url: str
    edition_label: str
    fetched_at: str
    sha256: str
    quote: str
    start: int
    end: int


class SearchResult(BaseModel):
    indexed_pages: int
    edition_label: str
    hits: list[Hit]


def load_corpus(path: Path) -> Corpus:
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("MPEP corpus exceeds size limit")
    corpus = Corpus.model_validate(json.loads(raw))
    seen: set[str] = set()
    for page in corpus.pages:
        if (
            page.section in seen
            or page.url != source_url(page.section)
            or page.sha256 != digest(page.text)
            or not re.fullmatch(r"[0-9a-f]{64}", page.html_sha256)
            or not re.match(re.escape(page.section) + r"(?![\d.])", page.heading)
        ):
            raise ValueError("Invalid MPEP corpus page")
        seen.add(page.section)
    return corpus


def search(corpus: Corpus, query: str) -> SearchResult:
    terms = re.findall(r"[\w.]+", query.casefold())
    hits: list[Hit] = []
    if not terms or len(terms) > 12:
        return SearchResult(indexed_pages=len(corpus.pages), edition_label=corpus.edition_label, hits=[])
    for page in corpus.pages:
        # Search the full imported page, returning only exact matching passages.
        # Paragraph boundaries are retained by the operator's HTML extractor.
        for passage in page.text.split("\n\n"):
            if not passage.strip():
                continue
            # Long blocks are searched in overlapping windows, retaining exact text.
            for pos in range(0, len(passage), 700):
                quote = passage[max(0, pos - 100) : pos + 800].strip()
                haystack = (page.section + " " + page.heading + " " + quote).casefold()
                if len(quote) < 12 or not all(term in haystack for term in terms):
                    continue
                span = find_quote_offset(page.text, quote)
                if span is None:
                    continue
                hits.append(
                    Hit(
                        section=page.section,
                        heading=page.heading,
                        url=page.url,
                        edition_label=corpus.edition_label,
                        fetched_at=page.fetched_at,
                        sha256=page.sha256,
                        quote=quote,
                        start=span[0],
                        end=span[1],
                    )
                )
                if len(hits) >= 20:
                    return SearchResult(
                        indexed_pages=len(corpus.pages),
                        edition_label=corpus.edition_label,
                        hits=hits,
                    )
                break
    return SearchResult(
        indexed_pages=len(corpus.pages), edition_label=corpus.edition_label, hits=hits
    )


def verify(corpus: Corpus, section: str, sha256: str, quote: str) -> bool:
    if len(quote.strip()) < 12:
        return False
    return any(
        page.section == section
        and page.sha256 == sha256
        and find_quote_offset(page.text, quote) is not None
        for page in corpus.pages
    )
