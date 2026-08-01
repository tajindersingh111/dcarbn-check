"""Add inventory approval, locking, restatement and audit reporting.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    approval_status = postgresql.ENUM(
        "pending",
        "in_review",
        "approved",
        "rejected",
        "withdrawn",
        name="inventory_approval_status",
        create_type=False,
    )
    restatement_status = postgresql.ENUM(
        "requested",
        "under_review",
        "approved",
        "rejected",
        "completed",
        name="inventory_restatement_status",
        create_type=False,
    )
    report_status = postgresql.ENUM(
        "draft",
        "final",
        "superseded",
        name="audit_report_status",
        create_type=False,
    )
    for enum in (approval_status, restatement_status, report_status):
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "inventory_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inventory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("calculation_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calculation_runs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", approval_status, nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.String(200), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewer_id", sa.String(200), nullable=True),
        sa.Column("review_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("evidence_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("boundary_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("factor_lineage_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("calculation_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("review_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("inventory_id", "version", name="uq_inventory_approval_version"),
    )
    for column in ("tenant_id", "inventory_id", "calculation_run_id", "status"):
        op.create_index(f"ix_inventory_approvals_{column}", "inventory_approvals", [column])

    op.create_table(
        "inventory_locks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inventory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approval_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventory_approvals.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("calculation_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calculation_runs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("locked_by", sa.String(200), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lock_reason", sa.Text(), nullable=False),
        sa.Column("lock_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint("inventory_id", name="uq_inventory_lock_inventory"),
    )
    op.create_index("ix_inventory_locks_tenant_id", "inventory_locks", ["tenant_id"])
    op.create_index("ix_inventory_locks_inventory_id", "inventory_locks", ["inventory_id"])

    op.create_table(
        "inventory_restatements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_inventory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("replacement_inventory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventories.id", ondelete="RESTRICT"), nullable=True, unique=True),
        sa.Column("status", restatement_status, nullable=False, server_default="requested"),
        sa.Column("requested_by", sa.String(200), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.String(200), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("materiality_assessment", sa.Text(), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("requested_changes", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("tenant_id", "original_inventory_id", "status"):
        op.create_index(f"ix_inventory_restatements_{column}", "inventory_restatements", [column])

    op.create_table(
        "audit_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inventory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("calculation_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calculation_runs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approval_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventory_approvals.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", report_status, nullable=False, server_default="draft"),
        sa.Column("generated_by", sa.String(200), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_by", sa.String(200), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_sha256", sa.String(64), nullable=False),
        sa.Column("report_payload", postgresql.JSONB(), nullable=False),
        sa.Column("superseded_by_report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audit_reports.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("inventory_id", "version", name="uq_audit_report_inventory_version"),
        sa.UniqueConstraint("report_sha256", name="uq_audit_report_sha256"),
    )
    for column in ("tenant_id", "inventory_id", "calculation_run_id", "status"):
        op.create_index(f"ix_audit_reports_{column}", "audit_reports", [column])


def downgrade() -> None:
    op.drop_table("audit_reports")
    op.drop_table("inventory_restatements")
    op.drop_table("inventory_locks")
    op.drop_table("inventory_approvals")
    for name in (
        "audit_report_status",
        "inventory_restatement_status",
        "inventory_approval_status",
    ):
        postgresql.ENUM(name=name).drop(op.get_bind(), checkfirst=True)
