"""Create DLQ permanent storage table.

Revision ID: 014
Revises: 013
Create Date: 2026-03-12 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dlq_permanent",
        sa.Column("id", sa.dialects.postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("topic", sa.String(200), nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("first_failed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_retried_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index(
        "ix_dlq_permanent_topic",
        "dlq_permanent",
        ["topic", sa.text("created_at DESC")],
        postgresql_where=sa.text("resolved = FALSE"),
    )


def downgrade() -> None:
    op.drop_index("ix_dlq_permanent_topic", table_name="dlq_permanent")
    op.drop_table("dlq_permanent")
