"""Add isolated patent snapshots (development preview).

Revision ID: 028
Revises: 027
"""
from alembic import op
import sqlalchemy as sa

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "patent_snapshots" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "patent_snapshots",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("matter_id", sa.String(36), sa.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_by", sa.String(64), nullable=False),
            sa.Column("ciphertext", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_patent_snapshots_matter_id", "patent_snapshots", ["matter_id"])
    if op.get_bind().dialect.name == "postgresql":
        from app.rls import rls_enable_statements

        for statement in rls_enable_statements():
            if statement.startswith("ALTER TABLE patent_snapshots ") or " ON patent_snapshots " in statement:
                op.execute(statement)


def downgrade() -> None:
    if "patent_snapshots" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("patent_snapshots")
