"""Patent snapshot preview: guards, encryption and bounded input."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.exceptions import ConflictError, NotFoundError
from app.models.patent_schemas import PatentWorksheet
from app.services import patent


def worksheet():
    return PatentWorksheet(fictional_data_only=True, disclosure={"title": "Fictional valve"})


def test_snapshot_ciphertext_and_identity():
    value = worksheet()
    ciphertext = patent.encode_snapshot("id1", "matter1", value)
    assert "Fictional valve" not in ciphertext
    row = SimpleNamespace(id="id1", matter_id="matter1", created_by="u1", ciphertext=ciphertext)
    assert patent.decode_snapshot(row).worksheet == value
    row.matter_id = "matter2"
    with pytest.raises(ValueError, match="identity mismatch"):
        patent.decode_snapshot(row)


def test_cannot_assert_verification_or_omit_acknowledgement():
    with pytest.raises(ValidationError):
        PatentWorksheet(fictional_data_only=False, disclosure={})
    with pytest.raises(ValidationError):
        PatentWorksheet(fictional_data_only=True, disclosure={}, claim_mappings=[{"verified": True}])


@pytest.mark.asyncio
async def test_matter_access_and_governance(monkeypatch):
    monkeypatch.setattr(patent.settings, "debug", True)
    monkeypatch.setattr(patent.settings, "patent_preview_enabled", True)
    db = AsyncMock()
    member = AsyncMock(return_value=False)
    matter = SimpleNamespace(owner_id="u1", legal_hold=False, retention_days=None)
    monkeypatch.setattr(patent.matters, "is_member", member)
    monkeypatch.setattr(patent.matters, "get_matter", AsyncMock(return_value=matter))
    with pytest.raises(NotFoundError):
        await patent.require_matter(db, "m1", "u1")
    member.return_value = True
    assert await patent.require_matter(db, "m1", "u2") is matter
    with pytest.raises(NotFoundError):
        await patent.require_matter(db, "m1", "u2", write=True)
    matter.legal_hold = True
    with pytest.raises(ConflictError):
        await patent.require_matter(db, "m1", "u1", write=True)
    matter.legal_hold = False
    matter.retention_days = 30
    with pytest.raises(ConflictError):
        await patent.require_matter(db, "m1", "u1", write=True)


def test_production_cannot_enable_preview(monkeypatch):
    monkeypatch.setattr(patent.settings, "debug", False)
    monkeypatch.setattr(patent.settings, "patent_preview_enabled", True)
    with pytest.raises(NotFoundError):
        patent.require_preview()
