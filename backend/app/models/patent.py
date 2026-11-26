"""Encrypted immutable patent worksheet snapshots (development preview)."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PatentSnapshot(Base):
    __tablename__ = "patent_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    matter_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
