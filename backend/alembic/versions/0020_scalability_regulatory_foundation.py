"""Add durable workload and methodology-pack foundations.

Revision ID: 0020
Revises: 0019
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "durable_workloads",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("organisation_id", sa.Uuid(), nullable=True),
        sa.Column("inventory_id", sa.Uuid(), nullable=True),
        sa.Column("workload_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("requested_by", sa.String(200), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_owner", sa.String(200), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("progress_current", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_total", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("cancelled_by", sa.String(200), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempts >= 0", name="ck_durable_workloads_workload_attempts_non_negative"),
        sa.CheckConstraint("max_attempts > 0", name="ck_durable_workloads_workload_max_attempts_positive"),
        sa.CheckConstraint("progress_current >= 0", name="ck_durable_workloads_workload_progress_non_negative"),
        sa.ForeignKeyConstraint(["inventory_id"], ["inventories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_workload_tenant_idempotency"),
    )
    op.create_index(
        "ix_workload_claim",
        "durable_workloads",
        ["status", "scheduled_at", "priority", "created_at"],
    )
    op.create_index(
        "ix_workload_tenant_status",
        "durable_workloads",
        ["tenant_id", "status", "created_at"],
    )
    for column in ("tenant_id", "organisation_id", "inventory_id", "workload_type", "status", "lease_expires_at"):
        op.create_index(f"ix_durable_workloads_{column}", "durable_workloads", [column])

    op.create_table(
        "methodology_packs",
        sa.Column("pack_key", sa.String(250), nullable=False),
        sa.Column("semantic_version", sa.String(50), nullable=False),
        sa.Column("selection_owner", sa.String(100), nullable=False, server_default="platform"),
        sa.Column("owner_tenant_id", sa.Uuid(), nullable=True),
        sa.Column("jurisdiction", sa.String(20), nullable=False),
        sa.Column("framework", sa.String(100), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("supported_scopes", sa.JSON(), nullable=False),
        sa.Column("scope_3_categories", sa.JSON(), nullable=False),
        sa.Column("activity_types", sa.JSON(), nullable=False),
        sa.Column("required_inputs", sa.JSON(), nullable=False),
        sa.Column("validation_rules", sa.JSON(), nullable=False),
        sa.Column("operator_identifier", sa.String(150), nullable=False),
        sa.Column("operator_configuration", sa.JSON(), nullable=False),
        sa.Column("factor_resolution", sa.JSON(), nullable=False),
        sa.Column("lifecycle_boundary", sa.Text(), nullable=False),
        sa.Column("reporting_disclosures", sa.JSON(), nullable=False),
        sa.Column("evidence_references", sa.JSON(), nullable=False),
        sa.Column("change_rationale", sa.Text(), nullable=False),
        sa.Column("compatibility_notes", sa.Text(), nullable=True),
        sa.Column("golden_examples", sa.JSON(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("reviewed_by", sa.String(200), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(200), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supersedes_pack_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supersedes_pack_id"], ["methodology_packs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pack_key", "semantic_version", name="uq_methodology_pack_version"),
    )
    op.create_index(
        "ix_methodology_pack_selection",
        "methodology_packs",
        ["selection_owner", "pack_key", "jurisdiction", "framework", "status", "effective_from", "effective_to"],
    )
    for column in ("pack_key", "owner_tenant_id", "jurisdiction", "framework", "status", "supersedes_pack_id"):
        op.create_index(f"ix_methodology_packs_{column}", "methodology_packs", [column])

    # Service validation is portable; PostgreSQL triggers provide the final write boundary.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION dcarbn_guard_methodology_pack()
        RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND OLD.status IN ('approved', 'superseded', 'withdrawn') THEN
            RAISE EXCEPTION 'approved methodology packs cannot be deleted';
          END IF;
          IF TG_OP = 'UPDATE' AND OLD.status IN ('approved', 'superseded', 'withdrawn') AND
             (ROW(OLD.pack_key, OLD.semantic_version, OLD.selection_owner, OLD.owner_tenant_id,
                  OLD.jurisdiction, OLD.framework, OLD.effective_from, OLD.effective_to,
                  OLD.supported_scopes, OLD.scope_3_categories, OLD.activity_types,
                  OLD.required_inputs, OLD.validation_rules, OLD.operator_identifier,
                  OLD.operator_configuration, OLD.factor_resolution, OLD.lifecycle_boundary,
                  OLD.reporting_disclosures, OLD.evidence_references, OLD.change_rationale,
                  OLD.compatibility_notes, OLD.golden_examples, OLD.content_sha256)
              IS DISTINCT FROM
              ROW(NEW.pack_key, NEW.semantic_version, NEW.selection_owner, NEW.owner_tenant_id,
                  NEW.jurisdiction, NEW.framework, NEW.effective_from, NEW.effective_to,
                  NEW.supported_scopes, NEW.scope_3_categories, NEW.activity_types,
                  NEW.required_inputs, NEW.validation_rules, NEW.operator_identifier,
                  NEW.operator_configuration, NEW.factor_resolution, NEW.lifecycle_boundary,
                  NEW.reporting_disclosures, NEW.evidence_references, NEW.change_rationale,
                  NEW.compatibility_notes, NEW.golden_examples, NEW.content_sha256)) THEN
            RAISE EXCEPTION 'approved methodology pack content is immutable';
          END IF;
          IF NEW.status = 'approved' AND EXISTS (
            SELECT 1 FROM methodology_packs existing
            WHERE existing.id <> NEW.id
              AND existing.selection_owner = NEW.selection_owner
              AND existing.pack_key = NEW.pack_key
              AND existing.jurisdiction = NEW.jurisdiction
              AND existing.framework = NEW.framework
              AND existing.status = 'approved'
              AND existing.effective_from <= COALESCE(NEW.effective_to, DATE '9999-12-31')
              AND COALESCE(existing.effective_to, DATE '9999-12-31') >= NEW.effective_from
          ) THEN
            RAISE EXCEPTION 'approved methodology pack effective periods overlap';
          END IF;
          IF TG_OP = 'DELETE' THEN
            RETURN OLD;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_methodology_pack_guard
        BEFORE UPDATE OR DELETE ON methodology_packs
        FOR EACH ROW EXECUTE FUNCTION dcarbn_guard_methodology_pack()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_methodology_pack_approval_guard
        BEFORE INSERT ON methodology_packs
        FOR EACH ROW WHEN (NEW.status = 'approved')
        EXECUTE FUNCTION dcarbn_guard_methodology_pack()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_methodology_pack_approval_guard ON methodology_packs")
    op.execute("DROP TRIGGER IF EXISTS trg_methodology_pack_guard ON methodology_packs")
    op.execute("DROP FUNCTION IF EXISTS dcarbn_guard_methodology_pack")
    op.drop_table("methodology_packs")
    op.drop_table("durable_workloads")
