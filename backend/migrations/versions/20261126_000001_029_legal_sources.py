"""Public legal sources (Counsel): operator-ingested MPEP text.

Creates ``legal_sources`` (one row per edition and revision) and
``legal_source_sections`` (one row per section, with its official URL,
revision marker, fetch time and text hash). Public government text, not
tenant data, so no row-level security. Purely additive; downgrade drops both.

Revision ID: 029
Revises: 028
Create Date: 2026-11-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "029"
down_revision: str = "028"
branch_labels = None
depends_on = None

_TABLES = ("legal_sources", "legal_source_sections")


def _metadata():
    from app.models.base import Base
    from app.models.legal_sources import LegalSource, LegalSourceSection  # noqa: F401

    return Base.metadata


def upgrade() -> None:
    metadata = _metadata()
    tables = [metadata.tables[name] for name in _TABLES if name in metadata.tables]
    metadata.create_all(bind=op.get_bind(), tables=tables, checkfirst=True)


def downgrade() -> None:
    present = set(sa.inspect(op.get_bind()).get_table_names())
    for name in reversed(_TABLES):
        if name in present:
            op.drop_table(name)
