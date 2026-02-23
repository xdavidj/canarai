"""ZeroDayPush model — active zero-day vectors pushed to all agents."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from canarai.models.base import Base


class ZeroDayPush(Base):
    __tablename__ = "zero_day_pushes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    site_id: Mapped[str] = mapped_column(
        String(36), nullable=True, index=True
    )
    test_id: Mapped[str] = mapped_column(
        String(16), nullable=False
    )
    surface: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="web"
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    agents_reached: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    deactivated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
