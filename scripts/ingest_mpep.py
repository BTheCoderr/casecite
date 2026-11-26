"""Fetch a fixed set of official MPEP HTML pages into a reviewable JSON file.

Run from backend/: python -m app.scripts.ingest_mpep is NOT required;
use PYTHONPATH=backend python scripts/ingest_mpep.py from the repository root.
No tenant input, redirects, model calls, or automatic activation.
"""

import argparse
import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

import httpx
from lxml import html

from app.services.mpep import SECTIONS, Corpus, Page, digest, source_url

MAX_HTML = 4 * 1024 * 1024


def extract(section: str, raw: bytes, fetched_at: str) -> Page:
    document = html.fromstring(raw)
    for node in document.xpath("//script|//style|//nav|//header|//footer|//noscript"):
        node.drop_tree()
    headings = document.xpath("//h1|//h2|//h3|//h4")
    heading = next(
        (
            node
            for node in headings
            if re.match(re.escape(section) + r"(?![\d.])", " ".join(node.text_content().split()))
        ),
        None,
    )
    if heading is None:
        raise ValueError("Expected MPEP section heading not found: " + section)
    title = " ".join(heading.text_content().split())
    # Preserve block text in document order after the confirmed section heading.
    # Import is page-level: nested subsections are not separately classified.
    blocks = [title]
    for node in heading.xpath("following::p|following::h2|following::h3|following::h4|following::li|following::tr"):
        if node.xpath("ancestor::li|ancestor::tr"):
            continue
        value = " ".join(node.text_content().split())
        if value:
            blocks.append(value)
    text = "\n\n".join(blocks)
    return Page(
        section=section,
        heading=title,
        url=source_url(section),
        fetched_at=fetched_at,
        text=text,
        sha256=digest(text),
        html_sha256=hashlib.sha256(raw).hexdigest(),
    )


def fetch_page(client: httpx.Client, section: str) -> Page:
    with client.stream("GET", source_url(section)) as response:
        response.raise_for_status()
        if "text/html" not in response.headers.get("content-type", "").lower():
            raise ValueError("Expected official HTML")
        raw = bytearray()
        for chunk in response.iter_bytes():
            raw.extend(chunk)
            if len(raw) > MAX_HTML:
                raise ValueError("MPEP page exceeds size limit")
    return extract(section, bytes(raw), datetime.now(UTC).isoformat())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition-label", required=True, help="Operator-confirmed manual revision")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with httpx.Client(follow_redirects=False, timeout=30, trust_env=False) as client:
        pages = [fetch_page(client, section) for section in SECTIONS]
    corpus = Corpus(edition_label=args.edition_label, pages=pages)
    # Exclusive creation: never overwrite an earlier captured revision.
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(corpus.model_dump_json(indent=2))
    print("Captured pages:", len(pages))
    print("Inspect headings, revision and extracted text before enabling the preview.")


if __name__ == "__main__":
    main()
