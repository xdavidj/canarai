"""Site model - represents a registered website being monitored."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from canary_api.models.base import Base
from canary_api.db.types import JSONType


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    site_key: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    config: Mapped[dict] = mapped_column(
        JSONType,
        nullable=False,
        default=lambda: {
            "enabled_tests": ["CAN-0001", "CAN-0002", "CAN-0003"],
            "detection_threshold": 0.5,
            "delivery_methods": ["html_comment", "meta_tag", "http_header"],
        },
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    api_keys: Mapped[list["ApiKey"]] = relationship(  # noqa: F821
        back_populates="site", cascade="all, delete-orphan"
    )
    visits: Mapped[list["Visit"]] = relationship(  # noqa: F821
        back_populates="site", cascade="all, delete-orphan"
    )
    webhooks: Mapped[list["Webhook"]] = relationship(  # noqa: F821
        back_populates="site", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_sites_domain", "domain"),
    )
