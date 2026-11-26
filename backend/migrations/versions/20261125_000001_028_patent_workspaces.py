"""Patent Studio (Counsel): matter-scoped workspaces, disclosure versions and
the claim-element chart.

Creates ``patent_workspaces`` (owner + required matter), and its children
``invention_disclosures`` (append-only, encrypted) and ``claim_elements``
(encrypted). On PostgreSQL the new tables get the same row-level-security
policies as the other work product (app/rls.py: an owned table and two
children). Purely additive; downgrade drops the three tables.

Revision ID: 028
Revises: 027
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "028"
down_revision: str = "027"
branch_labels = None
depends_on = None

_TABLES = ("patent_workspaces", "invention_disclosures", "claim_elements")


def _metadata():
    from app.models.base import Base
    from app.models.patent import (  # noqa: F401
        ClaimElement,
        InventionDisclosure,
        PatentWorkspace,
    )

    return Base.metadata


def upgrade() -> None:
    bind = op.get_bind()
    metadata = _metadata()
    tables = [metadata.tables[name] for name in _TABLES if name in metadata.tables]
    metadata.create_all(bind=bind, tables=tables, checkfirst=True)
    if bind.dialect.name != "postgresql":
        return
    from app.rls import table_policy_statements

    for statement in table_policy_statements(_TABLES):
        op.execute(statement)


def downgrade() -> None:
    present = set(sa.inspect(op.get_bind()).get_table_names())
    for name in reversed(_TABLES):  # children first
        if name in present:
            op.drop_table(name)
