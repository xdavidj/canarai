"""AgentSession model — tracks escalation state per agent fingerprint."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from canarai.models.base import Base
from canarai.db.types import JSONType


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    site_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    fingerprint_hash: Mapped[str] = mapped_column(
        String(16), nullable=False
    )
    surface: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="web"
    )
    vectors_seen: Mapped[dict] = mapped_column(
        JSONType, nullable=False, default=list
    )
    visit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_agent_sessions_site_fingerprint_surface",
            "site_id",
            "fingerprint_hash",
            "surface",
            unique=True,
        ),
    )
