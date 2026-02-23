"""Add agent sessions and zero-day push tables for escalation.

Revision ID: 002_escalation
Revises: 001_initial
Create Date: 2026-02-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_escalation"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agent sessions table — tracks escalation state per agent fingerprint
    op.create_table(
        "agent_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("site_id", sa.String(36), nullable=False),
        sa.Column("fingerprint_hash", sa.String(16), nullable=False),
        sa.Column("surface", sa.String(16), nullable=False, server_default="web"),
        sa.Column("vectors_seen", sa.Text(), nullable=False),
        sa.Column("visit_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_agent_sessions_site_fingerprint_surface",
        "agent_sessions",
        ["site_id", "fingerprint_hash", "surface"],
        unique=True,
    )
    op.create_index("ix_agent_sessions_site_id", "agent_sessions", ["site_id"])

    # Zero-day pushes table — active zero-day vectors
    op.create_table(
        "zero_day_pushes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("site_id", sa.String(36), nullable=True),
        sa.Column("test_id", sa.String(16), nullable=False),
        sa.Column("surface", sa.String(16), nullable=False, server_default="web"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("sample_target", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deprioritized_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_zero_day_pushes_site_id", "zero_day_pushes", ["site_id"])


def downgrade() -> None:
    op.drop_table("zero_day_pushes")
    op.drop_table("agent_sessions")
