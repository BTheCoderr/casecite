"""Patent Studio workspaces (Counsel): matter-scoped persistence of an invention
disclosure (append-only versions) and a claim-element chart.

Proves the data boundary: the owner and matter members read; only the owner
writes; a stranger, a member of another matter, and a walled user get 404
(never 403); a workspace cannot be filed under a matter the caller cannot
access; the text is encrypted at rest; ``verified`` cannot be set by a request;
audit entries carry ids and counts only. All content below is fictional.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-32chars!")
os.environ.setdefault("ENCRYPTION_SALT", "test-salt-16chars!")
os.environ.setdefault("DEBUG", "true")

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from app.models.matters import MatterWall
from app.models.patent import ClaimElement, InventionDisclosure, PatentWorkspace
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.helpers import (
    _sync_engine,
    db_add,
    db_count,
    headers,
    insert_db_user,
    make_shared_matter,
    make_user,
)

pytestmark = pytest.mark.usefixtures("no_rate_limit")

BASE = "/api/v1/patent-workspaces"

# Fictional invention: a self-watering planter. No real client data.
DISCLOSURE = {
    "title": "Capillary wick planter (fictional)",
    "problem": "Houseplants dry out when the owner travels.",
    "solution": "A felt wick draws water from a sealed reservoir by capillary action.",
    "alternatives": "Cotton or polyester wicks; reservoir in the base or the side.",
    "disclosures": "None known (fictional exercise).",
    "contributions": "Inventor A: wick geometry. Inventor B: reservoir seal.",
    "officeAction": "",
}
SECRET_PHRASE = "felt wick draws water"

ROWS = [
    {
        "element": "A reservoir configured to hold water",
        "disclosureSupport": "Fig. 1, para. 3",
        "reference": "Fictional Ref. X",
        "referencePassage": "col. 2, lines 4-9",
        "status": "candidate",
        "notes": "Check whether the seal is described.",
    },
    {
        "element": "A wick extending from the reservoir into the soil",
        "status": "gap",
    },
]


def _create(client, user, matter_id, title="Planter review"):
    resp = client.post(BASE, headers=headers(user), json={"matter_id": matter_id, "title": title})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _fill(client, user, ws_id):
    saved = client.post(
        f"{BASE}/{ws_id}/disclosures", headers=headers(user), json={"fields": DISCLOSURE}
    )
    assert saved.status_code == 200, saved.text
    rows = client.put(
        f"{BASE}/{ws_id}/claim-elements", headers=headers(user), json={"elements": ROWS}
    )
    assert rows.status_code == 200, rows.text
    return saved.json(), rows.json()


# ------------------------------------------------------------ create / read


def test_owner_creates_saves_and_reloads_a_workspace(client, audit_events):
    owner = make_user("pat-owner")
    matter_id = make_shared_matter(owner)
    ws = _create(client, owner, matter_id)
    assert ws["matter_id"] == matter_id and ws["role"] == "owner"
    assert ws["disclosure"] is None and ws["elements"] == [] and ws["disclosure_versions"] == 0

    saved, rows = _fill(client, owner, ws["id"])
    assert saved["created"] is True and saved["disclosure"]["version"] == 1
    assert len(saved["disclosure"]["content_sha256"]) == 64
    assert [r["position"] for r in rows] == [0, 1]
    assert rows[1]["reference"] == "" and rows[1]["status"] == "gap"

    notes = client.patch(
        f"{BASE}/{ws['id']}",
        headers=headers(owner),
        json={"reviewer_notes": "Ask about the seal."},
    )
    assert notes.status_code == 200, notes.text

    detail = client.get(f"{BASE}/{ws['id']}", headers=headers(owner)).json()
    assert detail["disclosure"]["fields"] == DISCLOSURE
    assert [r["element"] for r in detail["elements"]] == [r["element"] for r in ROWS]
    assert detail["reviewer_notes"] == "Ask about the seal."
    assert all(r["verified"] is False for r in detail["elements"])

    listed = client.get(BASE, headers=headers(owner), params={"matter_id": matter_id})
    assert [w["id"] for w in listed.json()["workspaces"]] == [ws["id"]]

    actions = [e["details"]["action"] for e in audit_events]
    for expected in (
        "patent_workspace_created",
        "invention_disclosure_saved",
        "claim_elements_saved",
        "patent_workspace_updated",
    ):
        assert expected in actions
    # Audit entries never carry the disclosure or claim text.
    flat = repr(audit_events)
    assert SECRET_PHRASE not in flat and "reservoir" not in flat
    assert "Ask about the seal" not in flat


def test_disclosure_versions_are_append_only_and_unchanged_saves_are_no_ops(client):
    owner = make_user("pat-ver")
    matter_id = make_shared_matter(owner)
    ws = _create(client, owner, matter_id)
    _fill(client, owner, ws["id"])

    again = client.post(
        f"{BASE}/{ws['id']}/disclosures", headers=headers(owner), json={"fields": DISCLOSURE}
    ).json()
    assert again["created"] is False and again["disclosure"]["version"] == 1

    changed = {**DISCLOSURE, "officeAction": "Fictional rejection; respond by the stated date."}
    second = client.post(
        f"{BASE}/{ws['id']}/disclosures", headers=headers(owner), json={"fields": changed}
    ).json()
    assert second["created"] is True and second["disclosure"]["version"] == 2

    versions = client.get(f"{BASE}/{ws['id']}/disclosures", headers=headers(owner)).json()
    assert [v["version"] for v in versions["versions"]] == [2, 1]
    first = client.get(f"{BASE}/{ws['id']}/disclosures/1", headers=headers(owner)).json()
    assert first["fields"] == DISCLOSURE  # the earlier version is untouched
    assert client.get(f"{BASE}/{ws['id']}/disclosures/9", headers=headers(owner)).status_code == 404
    assert db_count(InventionDisclosure, InventionDisclosure.workspace_id == ws["id"]) == 2


def test_text_is_encrypted_at_rest(client):
    owner = make_user("pat-enc")
    matter_id = make_shared_matter(owner)
    ws = _create(client, owner, matter_id)
    _fill(client, owner, ws["id"])
    engine = _sync_engine()
    try:
        with Session(engine) as session:
            stored = session.execute(
                select(InventionDisclosure.fields_enc).where(
                    InventionDisclosure.workspace_id == ws["id"]
                )
            ).scalar_one()
            payloads = (
                session.execute(
                    select(ClaimElement.payload_enc).where(ClaimElement.workspace_id == ws["id"])
                )
                .scalars()
                .all()
            )
    finally:
        engine.dispose()
    assert SECRET_PHRASE not in stored
    assert all("reservoir" not in p for p in payloads)


def test_requests_cannot_mark_rows_verified_or_send_unknown_fields(client):
    owner = make_user("pat-verify")
    matter_id = make_shared_matter(owner)
    ws = _create(client, owner, matter_id)
    forged = [{**ROWS[0], "verified": True}]
    resp = client.put(
        f"{BASE}/{ws['id']}/claim-elements", headers=headers(owner), json={"elements": forged}
    )
    assert resp.status_code == 422
    resp = client.post(
        f"{BASE}/{ws['id']}/disclosures",
        headers=headers(owner),
        json={"fields": {**DISCLOSURE, "patentable": "yes"}},
    )
    assert resp.status_code == 422
    resp = client.put(
        f"{BASE}/{ws['id']}/claim-elements",
        headers=headers(owner),
        json={"elements": [{**ROWS[0], "status": "novel"}]},
    )
    assert resp.status_code == 422
    too_many = client.put(
        f"{BASE}/{ws['id']}/claim-elements",
        headers=headers(owner),
        json={"elements": [ROWS[1]] * 51},
    )
    assert too_many.status_code == 422


# -------------------------------------------------------------- isolation


def test_cannot_file_a_workspace_under_a_matter_you_cannot_access(client):
    owner, outsider = make_user("pat-mo"), make_user("pat-out")
    matter_id = make_shared_matter(owner)
    resp = client.post(BASE, headers=headers(outsider), json={"matter_id": matter_id, "title": "x"})
    assert resp.status_code == 404
    resp = client.post(
        BASE, headers=headers(outsider), json={"matter_id": str(uuid.uuid4()), "title": "x"}
    )
    assert resp.status_code == 404
    assert client.post(BASE, headers=headers(owner), json={"title": "no matter"}).status_code == 422


def test_member_reads_but_cannot_write_and_strangers_get_404(client):
    owner, member, stranger = make_user("pat-o"), make_user("pat-m"), make_user("pat-s")
    matter_id = make_shared_matter(owner, member)
    ws = _create(client, owner, matter_id)
    _fill(client, owner, ws["id"])

    as_member = client.get(f"{BASE}/{ws['id']}", headers=headers(member))
    assert as_member.status_code == 200
    assert as_member.json()["role"] == "member"
    assert as_member.json()["disclosure"]["fields"]["title"] == DISCLOSURE["title"]
    assert [w["id"] for w in client.get(BASE, headers=headers(member)).json()["workspaces"]] == [
        ws["id"]
    ]

    # Members read; the owner alone writes. A refused write is a 404.
    for method, path, body in (
        ("patch", "", {"title": "renamed"}),
        ("post", "/disclosures", {"fields": DISCLOSURE}),
        ("put", "/claim-elements", {"elements": []}),
        ("delete", "", None),
    ):
        kwargs = {"headers": headers(member)}
        if body is not None:
            kwargs["json"] = body
        assert getattr(client, method)(f"{BASE}/{ws['id']}{path}", **kwargs).status_code == 404

    for path in ("", "/disclosures", "/disclosures/1"):
        assert client.get(f"{BASE}/{ws['id']}{path}", headers=headers(stranger)).status_code == 404
    assert client.get(BASE, headers=headers(stranger)).json()["workspaces"] == []
    assert (
        client.put(
            f"{BASE}/{ws['id']}/claim-elements", headers=headers(stranger), json={"elements": []}
        ).status_code
        == 404
    )
    # Nothing the refused writes asked for happened.
    detail = client.get(f"{BASE}/{ws['id']}", headers=headers(owner)).json()
    assert detail["title"] == "Planter review" and len(detail["elements"]) == 2


def test_cross_matter_denial(client):
    """Membership of one matter grants nothing in another, even for the same owner."""
    owner, member_a = make_user("pat-xo"), make_user("pat-xa")
    matter_a = make_shared_matter(owner, member_a)
    matter_b = make_shared_matter(owner)
    ws_a = _create(client, owner, matter_a, title="A")
    ws_b = _create(client, owner, matter_b, title="B")

    assert client.get(f"{BASE}/{ws_a['id']}", headers=headers(member_a)).status_code == 200
    assert client.get(f"{BASE}/{ws_b['id']}", headers=headers(member_a)).status_code == 404
    listed = client.get(BASE, headers=headers(member_a)).json()["workspaces"]
    assert [w["id"] for w in listed] == [ws_a["id"]]
    filtered = client.get(BASE, headers=headers(member_a), params={"matter_id": matter_b})
    assert filtered.json()["workspaces"] == []
    # And a member cannot file into the other matter either.
    resp = client.post(BASE, headers=headers(member_a), json={"matter_id": matter_b, "title": "x"})
    assert resp.status_code == 404


def test_an_ethical_wall_defeats_membership(client):
    owner, walled = make_user("pat-wo"), make_user("pat-ww")
    matter_id = make_shared_matter(owner, walled)
    ws = _create(client, owner, matter_id)
    assert client.get(f"{BASE}/{ws['id']}", headers=headers(walled)).status_code == 200
    db_add(
        MatterWall(
            id=str(uuid.uuid4()),
            matter_id=matter_id,
            user_id=walled.id,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    assert client.get(f"{BASE}/{ws['id']}", headers=headers(walled)).status_code == 404
    assert client.get(BASE, headers=headers(walled)).json()["workspaces"] == []


def test_walling_a_member_hands_their_workspace_to_the_matter_owner(client, auth_headers):
    owner, conflicted = make_user("pat-wall-o"), make_user("pat-wall-c")
    insert_db_user(conflicted)
    matter_id = make_shared_matter(owner, conflicted)
    ws = _create(client, conflicted, matter_id, title="Theirs")
    vdb = MagicMock()
    with patch("app.services.vectordb.get_vector_db", return_value=vdb):
        resp = client.post(
            f"/api/v1/matters/{matter_id}/walls",
            json={"email": conflicted.email, "reason": "Fictional conflict"},
            headers=auth_headers,
        )
    assert resp.status_code == 200, resp.text
    assert client.get(f"{BASE}/{ws['id']}", headers=headers(conflicted)).status_code == 404
    as_owner = client.get(f"{BASE}/{ws['id']}", headers=headers(owner))
    assert as_owner.status_code == 200 and as_owner.json()["role"] == "owner"


def test_owner_delete_removes_children(client, audit_events):
    owner = make_user("pat-del")
    matter_id = make_shared_matter(owner)
    ws = _create(client, owner, matter_id)
    _fill(client, owner, ws["id"])
    resp = client.delete(f"{BASE}/{ws['id']}", headers=headers(owner))
    assert resp.status_code == 200, resp.text
    assert client.get(f"{BASE}/{ws['id']}", headers=headers(owner)).status_code == 404
    assert db_count(PatentWorkspace, PatentWorkspace.id == ws["id"]) == 0
    assert db_count(InventionDisclosure, InventionDisclosure.workspace_id == ws["id"]) == 0
    assert db_count(ClaimElement, ClaimElement.workspace_id == ws["id"]) == 0
    assert any(e["details"]["action"] == "patent_workspace_deleted" for e in audit_events)


def test_viewer_role_without_contracts_permission_is_refused(client):
    from app.services.auth import UserRole

    owner = make_user("pat-viewer", UserRole.VIEWER)
    matter_id = make_shared_matter(owner)
    resp = client.post(BASE, headers=headers(owner), json={"matter_id": matter_id, "title": "x"})
    assert resp.status_code == 403


def test_saved_report_formats_and_access(client, audit_events):
    import io

    from docx import Document
    from pypdf import PdfReader

    owner, member, stranger = make_user("pat-report-o"), make_user("pat-report-m"), make_user(
        "pat-report-s"
    )
    matter_id = make_shared_matter(owner, member)
    ws = _create(client, owner, matter_id)
    _fill(client, owner, ws["id"])
    path = f"{BASE}/{ws['id']}/report"
    for fmt in ("pdf", "docx"):
        body = {"format": fmt, "fictional_data_only": True}
        reply = client.post(path, headers=headers(member), json=body)
        assert reply.status_code == 200, reply.text
        assert reply.headers["cache-control"] == "no-store"
        assert reply.headers["content-disposition"].endswith(f'.{fmt}"')
        if fmt == "pdf":
            assert reply.content.startswith(b"%PDF")
            text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(reply.content)).pages)
        else:
            assert reply.content.startswith(b"PK")
            text = "\n".join(p.text for p in Document(io.BytesIO(reply.content)).paragraphs)
        assert "FICTIONAL DATA ONLY" in text
        assert "Unverified candidate" in text
        assert "Capillary wick planter" in text
        assert client.post(path, headers=headers(stranger), json=body).status_code == 404
    assert client.post(
        path, headers=headers(owner), json={"format": "pdf", "fictional_data_only": False}
    ).status_code == 422
    assert client.post(
        path, headers=headers(owner), json={"format": "pdf", "fictional_data_only": True, "verified": True}
    ).status_code == 422
    assert SECRET_PHRASE not in repr(audit_events)
    assert any(e["details"]["action"] == "patent_report_exported" for e in audit_events)
