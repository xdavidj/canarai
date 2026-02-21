"""Test result model - individual canary test outcomes per visit."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from canary_api.models.base import Base
from canary_api.db.types import JSONType


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    visit_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("visits.visit_id", ondelete="CASCADE"),
        nullable=False,
    )
    test_id: Mapped[str] = mapped_column(String(16), nullable=False)
    test_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")
    delivery_method: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    injected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    visit: Mapped["Visit"] = relationship(back_populates="test_results")  # noqa: F821

    __table_args__ = (
        Index("ix_test_results_test_id", "test_id"),
        Index("ix_test_results_outcome", "outcome"),
        Index("ix_test_results_visit_id", "visit_id"),
    )
