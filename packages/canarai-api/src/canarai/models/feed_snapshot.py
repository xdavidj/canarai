"""Feed snapshot model — caches precomputed aggregate feed data."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from canarai.db.types import JSONType
from canarai.models.base import Base


class AgentFeedSnapshot(Base):
    __tablename__ = "agent_feed_snapshots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    snapshot_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )
    period: Mapped[str] = mapped_column(
        String(32), nullable=False
    )
    data: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_feed_snapshots_type_period", "snapshot_type", "period"),
    )
