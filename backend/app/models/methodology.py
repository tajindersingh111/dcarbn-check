from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MethodologyStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ACTIVE = "active"
    RETIRED = "retired"
    SUPERSEDED = "superseded"


class MethodologyVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "methodology_versions"
    __table_args__ = (
        UniqueConstraint(
            "method_key",
            "version",
            name="uq_methodology_key_version",
        ),
    )

    method_key: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[MethodologyStatus] = mapped_column(
        Enum(MethodologyStatus, name="methodology_status"),
        nullable=False,
        default=MethodologyStatus.DRAFT,
        index=True,
    )
    scope: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    scope_3_category: Mapped[int | None] = mapped_column(Integer, index=True)
    jurisdiction: Mapped[str] = mapped_column(String(20), nullable=False, default="GB")
    reporting_year: Mapped[int | None] = mapped_column(Integer, index=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    expression: Mapped[str] = mapped_column(Text, nullable=False)
    output_unit: Mapped[str] = mapped_column(String(100), nullable=False)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    validation_rules: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    golden_tests: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    source_reference: Mapped[str] = mapped_column(String(1000), nullable=False)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_by: Mapped[str | None] = mapped_column(String(200))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("methodology_versions.id", ondelete="SET NULL"),
    )
