#!/usr/bin/env python3
"""Ingest official MPEP pages into SmartProBono Counsel's public legal sources.

Operator-run only; the application never fetches. Fetches nothing outside
https://www.uspto.gov/web/offices/pac/mpep/ and follows no redirects. Pages are
fetched one at a time, spaced by --delay seconds.

You must state the edition and revision you are ingesting, as printed on the
USPTO's MPEP pages at the time. This script does not guess them. Each section
keeps its own revision marker from its heading.

Examples (run from the repository root, after `alembic upgrade head`):

    # One chapter: discover its section pages from the chapter index
    python scripts/ingest_mpep.py --edition "Ninth Edition" --revision "01.2024" \\
        --published-on "November 2024" \\
        --chapter-index https://www.uspto.gov/web/offices/pac/mpep/mpep-2100.html

    # Specific pages
    python scripts/ingest_mpep.py --edition "Ninth Edition" --revision "01.2024" \\
        --pages https://www.uspto.gov/web/offices/pac/mpep/s2106.html

    # Pages you saved yourself (named as on the site, e.g. s2106.html)
    python scripts/ingest_mpep.py --edition "Ninth Edition" --revision "01.2024" \\
        --from-dir ./mpep-pages --dry-run

Re-running the same edition and revision adds only missing sections. A
section whose text changed under the same revision is reported as a conflict
and left unchanged: ingest it under a new --revision label instead. Exit code 0
on success, 1 when conflicts or pages with no sections were found, 2 on error.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


def _args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--name", default="MPEP")
    parser.add_argument("--edition", required=True, help='e.g. "Ninth Edition"')
    parser.add_argument("--revision", required=True, help='e.g. "01.2024"')
    parser.add_argument("--published-on", default=None, help='e.g. "November 2024"')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--chapter-index", help="an official mpep-NNNN.html chapter index URL")
    source.add_argument("--pages", nargs="+", help="official section page URLs")
    source.add_argument("--from-dir", type=Path, help="a directory of saved section pages")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between fetches")
    parser.add_argument("--dry-run", action="store_true", help="parse and report; store nothing")
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    from app.database import AsyncSessionLocal
    from app.services.legal_sources.ingest import fetch_pages, ingest_pages, pages_from_dir
    from app.services.legal_sources.mpep import (
        MPEP_BASE_URL,
        check_mpep_url,
        discover_section_pages,
    )

    if args.from_dir is not None:
        pages = pages_from_dir(args.from_dir)
        source_url = MPEP_BASE_URL + "index.html"
    elif args.chapter_index:
        index_url = check_mpep_url(args.chapter_index)
        [(_, index_html)] = await fetch_pages([index_url], delay_seconds=0)
        urls = discover_section_pages(index_html, index_url)
        print(f"{len(urls)} section pages linked from {index_url}", file=sys.stderr)
        pages = await fetch_pages(urls, delay_seconds=args.delay)
        source_url = index_url
    else:
        urls = [check_mpep_url(u) for u in args.pages]
        pages = await fetch_pages(urls, delay_seconds=args.delay)
        source_url = MPEP_BASE_URL + "index.html"

    async with AsyncSessionLocal() as session:
        report = await ingest_pages(
            session,
            pages,
            name=args.name,
            edition=args.edition,
            revision=args.revision,
            published_on=args.published_on,
            source_url=source_url,
            dry_run=args.dry_run,
        )
    print(json.dumps({"dry_run": args.dry_run, **report.as_dict()}, indent=2))
    return 1 if report.conflicts or report.empty_pages else 0


def main(argv: list[str] | None = None) -> int:
    args = _args(argv)
    try:
        return asyncio.run(_run(args))
    except Exception as exc:  # report and fail; nothing partial is committed
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
