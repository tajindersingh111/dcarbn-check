from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MethodologyPackStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"


class MethodologyPack(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable, effective-dated configuration for reviewed calculation operators."""

    __tablename__ = "methodology_packs"
    __table_args__ = (
        UniqueConstraint("pack_key", "semantic_version", name="uq_methodology_pack_version"),
        Index(
            "ix_methodology_pack_selection",
            "selection_owner",
            "pack_key",
            "jurisdiction",
            "framework",
            "status",
            "effective_from",
            "effective_to",
        ),
    )

    pack_key: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    semantic_version: Mapped[str] = mapped_column(String(50), nullable=False)
    selection_owner: Mapped[str] = mapped_column(String(100), nullable=False, default="platform")
    owner_tenant_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
    )
    jurisdiction: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    framework: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    status: Mapped[MethodologyPackStatus] = mapped_column(
        Enum(MethodologyPackStatus, name="methodology_pack_status"),
        nullable=False,
        default=MethodologyPackStatus.DRAFT,
        index=True,
    )
    supported_scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    scope_3_categories: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    activity_types: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    required_inputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    validation_rules: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    operator_identifier: Mapped[str] = mapped_column(String(150), nullable=False)
    operator_configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    factor_resolution: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    lifecycle_boundary: Mapped[str] = mapped_column(Text, nullable=False)
    reporting_disclosures: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence_references: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False)
    change_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    compatibility_notes: Mapped[str | None] = mapped_column(Text)
    golden_examples: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_pack_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("methodology_packs.id", ondelete="SET NULL"),
        index=True,
    )
