"""Patent Studio models (Counsel) — matter-scoped workspaces for organizing an
invention disclosure and a claim-element evidence chart for practitioner review.

A ``PatentWorkspace`` always belongs to a matter (``matter_id`` is required),
so it is shared with the matter's members and fenced by the same ethical walls
and row-level security as other work product. Its children:

* ``InventionDisclosure`` — append-only versions. Each save of a changed
  disclosure adds a version; nothing rewrites an earlier one. The free text is
  stored encrypted (``services/encryption.py``) and the plaintext's SHA-256 is
  kept so a version can be identified without decrypting it.
* ``ClaimElement`` — one row of the claim chart: the element, the disclosure
  support, a candidate reference and pinpoint passage, the reviewer's status
  and open issues. Free text encrypted; position and status in the clear.
  ``verified`` is reserved for server-side quote verification against an
  indexed reference document (a later change); no request can set it.

Nothing here is a patentability determination. These tables store what a
reviewer typed; they draw no conclusions from it.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Reviewer mapping statuses (match the Patent Studio UI).
ELEMENT_STATUSES = ("unreviewed", "candidate", "gap", "unclear")

# Disclosure field keys (match frontend/src/constants/patentStudio.ts).
DISCLOSURE_KEYS = (
    "title",
    "problem",
    "solution",
    "alternatives",
    "disclosures",
    "contributions",
    "officeAction",
)


class PatentWorkspace(Base):
    """A Patent Studio workspace filed under a matter."""

    __tablename__ = "patent_workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Required: a workspace is always matter work product.
    matter_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # A short working label shown in lists. Kept in the clear like other
    # work-product names; the UI asks for a label, not invention detail.
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # Practitioner notes, encrypted.
    reviewer_notes_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("ix_patent_workspaces_owner_matter", "owner_id", "matter_id"),)


class InventionDisclosure(Base):
    """One saved version of a workspace's invention disclosure (append-only)."""

    __tablename__ = "invention_disclosures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patent_workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # JSON object of DISCLOSURE_KEYS -> text, encrypted as one string.
    fields_enc: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("workspace_id", "version", name="uq_invention_disclosures_version"),
    )


class ClaimElement(Base):
    """One row of a workspace's claim-element evidence chart."""

    __tablename__ = "claim_elements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patent_workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    # JSON object {element, disclosureSupport, reference, referencePassage,
    # notes}, encrypted as one string.
    payload_enc: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unreviewed")
    # Set only by server-side quote verification (not yet implemented); never
    # from a request body.
    verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
