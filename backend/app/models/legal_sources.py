"""Public legal sources (Counsel): an operator-ingested copy of official text,
starting with the USPTO's Manual of Patent Examining Procedure (MPEP).

These rows are not tenant data. They hold public government text that every
signed-in user may read, so they are deliberately left out of row-level
security (app/rls.py) and carry no owner or matter.

A ``LegalSource`` is one edition and revision of a publication, as the
operator labelled it when ingesting. A ``LegalSourceSection`` is one section
as published on the official page it came from, with the section's own
revision marker (for example ``R-10.2019``), the page URL, when it was fetched
and the SHA-256 of the stored text so a later citation can be bound to exactly
the text it quotes. A new revision is a new ``LegalSource``; ingesting never
rewrites a stored section.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LegalSource(Base):
    __tablename__ = "legal_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    edition: Mapped[str] = mapped_column(String(100), nullable=False)
    revision: Mapped[str] = mapped_column(String(50), nullable=False)
    # As the operator gave it (free text, e.g. "November 2024"); never guessed.
    published_on: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    # Last ingestion run that touched this source.
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("name", "edition", "revision", name="uq_legal_sources_revision"),
    )


class LegalSourceSection(Base):
    __tablename__ = "legal_source_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("legal_sources.id", ondelete="CASCADE"), nullable=False
    )
    section_id: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    # The section's own revision marker from its heading, e.g. "R-10.2019".
    revision_note: Mapped[str] = mapped_column(String(20), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("source_id", "section_id", name="uq_legal_source_sections_section"),
        Index("ix_legal_source_sections_section_id", "section_id"),
    )
