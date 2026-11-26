"""Parse official MPEP HTML pages into sections, and police which URLs may be fetched.

An MPEP section page (``https://www.uspto.gov/web/offices/pac/mpep/s2106.html``)
prints each section and subsection under a heading of the form::

    2106 Patent Subject Matter Eligibility [R-10.2019]

that is, the section number, the title and the section's own revision marker.
Site navigation comes before the first heading, and the chapter's table of
contents follows the content after a ``[top]`` marker, as lines such as
``2106.03-Eligibility Step 1: ...`` (number, hyphen, title, no revision). The
parser keeps only text between a heading and the next heading, a reserved
slot (``2106.01 [Reserved]``), ``[top]`` or a table-of-contents line, so
navigation never ends up in a section.

The parser stores what the page says. It does not summarise, merge or infer.
If USPTO changes the page layout, it finds no headings and reports zero
sections rather than guessing.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from lxml import html as lxml_html  # nosec B410 - parses operator-fetched USPTO pages, no network

MPEP_HOST = "www.uspto.gov"
MPEP_PREFIX = "/web/offices/pac/mpep/"
MPEP_BASE_URL = f"https://{MPEP_HOST}{MPEP_PREFIX}"

# A page under the MPEP prefix: one path segment ending in .html, no query.
_PAGE_PATH = re.compile(r"^/web/offices/pac/mpep/[A-Za-z0-9][A-Za-z0-9._-]*\.html$")
# A section page link, e.g. s2106.html or s2187-2189.html.
_SECTION_PAGE = re.compile(r"^s\d{3,4}(?:-\d{3,4})?\.html$")

_SECTION_NO = r"\d{3,4}(?:\.\d{1,2})?(?:\([a-z0-9]{1,3}\))*"
_HEADING = re.compile(
    # The number and title may sit in adjacent inline elements with no space.
    rf"^(?P<id>{_SECTION_NO})(?:\s+|(?=[A-Z\u201c\"]))(?P<title>\S.*?)\s*"
    rf"\[(?P<rev>R-\d{{2}}\.\d{{4}})\]$"
)
_TOC_LINE = re.compile(rf"^(?:{_SECTION_NO})(?:-\d{{3,4}})?-\S")
# A reserved slot prints a number and "[Reserved]" with no revision marker; it
# ends the section before it and starts nothing.
_RESERVED = re.compile(rf"^(?:{_SECTION_NO})(?:-\d{{3,4}})?\s*\[Reserved\]$", re.IGNORECASE)
_TOP = "[top]"

_BLOCK_TAGS = {
    "p", "div", "br", "li", "ul", "ol", "table", "tr", "td", "th", "h1", "h2", "h3",
    "h4", "h5", "h6", "section", "article", "blockquote", "pre", "dd", "dt", "dl",
    "header", "footer", "nav", "hr",
}  # fmt: skip


class DisallowedUrlError(ValueError):
    """A URL outside the official MPEP pages."""


@dataclass(frozen=True)
class ParsedSection:
    section_id: str
    title: str
    revision_note: str
    text: str
    url: str

    @property
    def text_sha256(self) -> str:
        return sha256_text(self.text)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_mpep_url(url: str) -> str:
    """Return ``url`` if it is an https page under the official MPEP path, else raise."""
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != MPEP_HOST or parts.port not in (None, 443):
        raise DisallowedUrlError(f"Not an official MPEP URL: {url!r}")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise DisallowedUrlError(f"Not an official MPEP URL: {url!r}")
    if not _PAGE_PATH.match(parts.path) or ".." in parts.path:
        raise DisallowedUrlError(f"Not an official MPEP URL: {url!r}")
    return f"https://{MPEP_HOST}{parts.path}"


def _lines(page_html: str) -> list[str]:
    parser = lxml_html.HTMLParser(no_network=True, remove_comments=True)
    root = lxml_html.fromstring(page_html, parser=parser)
    for bad in root.xpath("//script|//style|//noscript|//template"):
        bad.drop_tree()
    for el in root.iter():
        if isinstance(el.tag, str) and el.tag.lower() in _BLOCK_TAGS:
            el.text = "\n" + (el.text or "")
            el.tail = "\n" + (el.tail or "")
    text = root.text_content().replace("\xa0", " ")
    out = []
    for raw in text.split("\n"):
        line = re.sub(r"[ \t\r\f\v]+", " ", raw).strip()
        if line:
            out.append(line)
    return out


def parse_mpep_page(page_html: str, url: str) -> list[ParsedSection]:
    """The sections printed on one official MPEP page, in page order.

    A section number that appears twice on a page keeps its first occurrence.
    """
    url = check_mpep_url(url)
    sections: list[ParsedSection] = []
    seen: set[str] = set()
    current: dict[str, str] | None = None
    body: list[str] = []

    def close() -> None:
        nonlocal current, body
        if current is not None and current["id"] not in seen:
            seen.add(current["id"])
            sections.append(
                ParsedSection(
                    section_id=current["id"],
                    title=current["title"],
                    revision_note=current["rev"],
                    text="\n".join(body).strip(),
                    url=url,
                )
            )
        current, body = None, []

    for line in _lines(page_html):
        heading = _HEADING.match(line)
        if heading:
            close()
            current = {
                "id": heading.group("id"),
                "title": heading.group("title"),
                "rev": heading.group("rev"),
            }
            continue
        if current is None:
            continue  # navigation before the first heading
        if line == _TOP or _TOC_LINE.match(line) or _RESERVED.match(line):
            close()
            continue
        body.append(line)
    close()
    return sections


def discover_section_pages(index_html: str, index_url: str) -> list[str]:
    """Section-page URLs linked from an official chapter index (e.g. mpep-2100.html),
    de-duplicated in link order. Links elsewhere are ignored."""
    base = check_mpep_url(index_url)
    parser = lxml_html.HTMLParser(no_network=True, remove_comments=True)
    root = lxml_html.fromstring(index_html, parser=parser)
    found: list[str] = []
    for href in root.xpath("//a/@href"):
        absolute = urljoin(base, str(href).split("#", 1)[0].strip())
        try:
            url = check_mpep_url(absolute)
        except DisallowedUrlError:
            continue
        if _SECTION_PAGE.match(url.rsplit("/", 1)[1]) and url not in found:
            found.append(url)
    return found
