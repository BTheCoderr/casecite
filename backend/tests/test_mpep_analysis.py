"""Synthetic source tests; no real model or network."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import mpep, mpep_analysis


def evidence():
    passage = "Synthetic test source. A fictional review question needs evidence."
    return mpep.SearchResult(
        indexed_pages=1,
        edition_label="synthetic",
        hits=[
            mpep.Hit(
                section="2109",
                heading="2109 synthetic",
                url=mpep.source_url("2109"),
                edition_label="synthetic",
                fetched_at="synthetic",
                sha256=mpep.digest(passage),
                quote=passage,
                start=0,
                end=len(passage),
            )
        ],
    )


def test_rejects_wrong_passage_fabricated_quote_and_conclusion():
    result = mpep_analysis.validate_proposals(
        json.dumps({"issues": [
            {"passage_id": 1, "question": "What evidence is available?", "quote": "A fictional review question needs evidence."},
            {"passage_id": 2, "question": "Is this sourced?", "quote": "A fictional review question needs evidence."},
            {"passage_id": 1, "question": "Is this sourced?", "quote": "Invented quotation not in source."},
            {"passage_id": 1, "question": "This is patentable.", "quote": "A fictional review question needs evidence."},
        ]}),
        evidence(),
    )
    assert result.rejected == 3
    assert len(result.issues) == 1
    citation = result.issues[0].citation
    assert evidence().hits[0].quote[citation.start:citation.end] == citation.quote


def test_bad_json_is_not_displayed():
    result = mpep_analysis.validate_proposals("not json", evidence())
    assert not result.issues
    assert result.rejected == 1


@pytest.mark.asyncio
async def test_model_call_requires_retrieved_sources(monkeypatch):
    call = AsyncMock(return_value=SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"issues":[]}'))]
    ))
    monkeypatch.setattr(mpep_analysis, "openai_chat", call)
    empty = mpep.SearchResult(indexed_pages=1, edition_label="synthetic", hits=[])
    await mpep_analysis.draft_questions(None, "local", "http://127.0.0.1:11434/v1", "topic", empty)
    call.assert_not_awaited()
    await mpep_analysis.draft_questions(None, "local", "http://127.0.0.1:11434/v1", "topic", evidence())
    assert call.call_args.kwargs["required_base_url"] == "http://127.0.0.1:11434/v1"
