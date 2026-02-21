"""Visit model - records each page visit with detection signals."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from canary_api.models.base import Base
from canary_api.db.types import JSONType


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    visit_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    site_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )
    page_url: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    detection: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    classification: Mapped[str] = mapped_column(
        String(32), nullable=False, default="human"
    )
    agent_family: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    site: Mapped["Site"] = relationship(back_populates="visits")  # noqa: F821
    test_results: Mapped[list["TestResult"]] = relationship(  # noqa: F821
        back_populates="visit", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_visits_site_id_timestamp", "site_id", "timestamp"),
        Index("ix_visits_classification", "classification"),
    )
