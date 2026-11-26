"""Synthetic fixtures only; no outbound requests."""
import json

import pytest

from app.services import mpep


def page():
    text = ("Synthetic test text for quote verification. " * 4).strip()
    return mpep.Page(
        section="2109",
        heading="2109 Synthetic fixture",
        url=mpep.source_url("2109"),
        fetched_at="2026-11-25T00:00:00+00:00",
        text=text,
        sha256=mpep.digest(text),
        html_sha256="0" * 64,
    )


def test_search_exact_excerpt_and_verify():
    item = page()
    corpus = mpep.Corpus(edition_label="Synthetic", pages=[item])
    result = mpep.search(corpus, "quote verification")
    assert result.indexed_pages == 1
    assert result.hits
    hit = result.hits[0]
    assert item.text[hit.start : hit.end] == hit.quote
    assert mpep.verify(corpus, item.section, item.sha256, hit.quote)
    assert not mpep.verify(corpus, item.section, "1" * 64, hit.quote)
    assert not mpep.verify(corpus, item.section, item.sha256, "fabricated sentence")
    assert not mpep.search(corpus, "absent term").hits


def test_tampered_corpus_and_wrong_origin(tmp_path):
    item = page()
    file = tmp_path / "fixture.json"
    corpus = mpep.Corpus(edition_label="Synthetic", pages=[item])
    file.write_text(corpus.model_dump_json())
    assert mpep.load_corpus(file).pages[0] == item
    payload = corpus.model_dump()
    payload["pages"][0]["text"] += " tampered"
    file.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        mpep.load_corpus(file)
    payload = corpus.model_dump()
    payload["pages"][0]["url"] = "https://example.com/s2109.html"
    file.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        mpep.load_corpus(file)
