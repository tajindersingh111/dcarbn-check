"""Add activity records and emissions calculations.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    activity_status = postgresql.ENUM(
        "draft", "validated", "calculated", "rejected", "superseded",
        name="activity_status", create_type=False,
    )
    activity_type = postgresql.ENUM(
        "mobile_combustion",
        "stationary_combustion",
        "refrigerant",
        "purchased_electricity",
        "purchased_heat_steam_cooling",
        "freight_transport",
        "business_travel",
        "employee_commuting",
        name="activity_type",
        create_type=False,
    )
    emission_scope = postgresql.ENUM(
        "scope_1", "scope_2", "scope_3",
        name="emission_scope", create_type=False,
    )
    scope_2_method = postgresql.ENUM(
        "not_applicable", "location_based", "market_based",
        name="scope_2_method", create_type=False,
    )
    data_quality_level = postgresql.ENUM(
        "primary", "secondary", "estimated", "unknown",
        name="data_quality_level", create_type=False,
    )
    calculation_run_status = postgresql.ENUM(
        "draft", "running", "completed", "failed", "approved", "superseded",
        name="calculation_run_status", create_type=False,
    )
    calculation_method = postgresql.ENUM(
        "activity_factor", "external_operational_result",
        name="calculation_method", create_type=False,
    )
    for enum in (
        activity_status,
        activity_type,
        emission_scope,
        scope_2_method,
        data_quality_level,
        calculation_run_status,
        calculation_method,
    ):
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "activity_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inventory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("legal_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("legal_entities.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("activity_type", activity_type, nullable=False),
        sa.Column("status", activity_status, nullable=False, server_default="draft"),
        sa.Column("scope", emission_scope, nullable=False),
        sa.Column("scope_3_category", sa.Integer(), nullable=True),
        sa.Column("scope_2_method", scope_2_method, nullable=False, server_default="not_applicable"),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("activity_value", sa.Numeric(30, 15), nullable=False),
        sa.Column("activity_unit", sa.String(length=100), nullable=False),
        sa.Column("normalized_value", sa.Numeric(30, 15), nullable=True),
        sa.Column("normalized_unit", sa.String(length=100), nullable=True),
        sa.Column("geography_code", sa.String(length=20), nullable=False, server_default="GB"),
        sa.Column("factor_level_1", sa.String(length=250), nullable=True),
        sa.Column("factor_level_2", sa.String(length=250), nullable=True),
        sa.Column("factor_level_3", sa.String(length=250), nullable=True),
        sa.Column("factor_level_4", sa.String(length=250), nullable=True),
        sa.Column("factor_column_text", sa.String(length=500), nullable=True),
        sa.Column("lifecycle_boundary", sa.String(length=150), nullable=True),
        sa.Column("allocation_percentage", sa.Numeric(5, 2), nullable=False, server_default="100.00"),
        sa.Column("data_quality_level", data_quality_level, nullable=False, server_default="unknown"),
        sa.Column("data_quality_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_system", sa.String(length=100), nullable=False, server_default="carbon-platform"),
        sa.Column("source_record_id", sa.String(length=200), nullable=False),
        sa.Column("source_record_hash", sa.String(length=64), nullable=True),
        sa.Column("evidence_reference", sa.String(length=1000), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("superseded_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("activity_records.id", ondelete="SET NULL"), nullable=True),
        sa.Column("validation_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "source_system", "source_record_id", "version", name="uq_activity_source_version"),
        sa.CheckConstraint("activity_value >= 0", name="ck_activity_records_activity_value_non_negative"),
        sa.CheckConstraint("allocation_percentage >= 0 AND allocation_percentage <= 100", name="ck_activity_records_activity_allocation_range"),
        sa.CheckConstraint("data_quality_score >= 0 AND data_quality_score <= 100", name="ck_activity_records_activity_data_quality_range"),
    )
    for column in ("tenant_id", "inventory_id", "organisation_id", "legal_entity_id", "site_id", "activity_type", "status", "scope", "scope_3_category", "activity_date"):
        op.create_index(f"ix_activity_records_{column}", "activity_records", [column])

    op.create_table(
        "calculation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inventory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", calculation_run_status, nullable=False, server_default="draft"),
        sa.Column("software_version", sa.String(length=100), nullable=False),
        sa.Column("factor_policy_version", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(length=200), nullable=True),
        sa.Column("activity_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("inventory_id", "version", name="uq_calculation_run_inventory_version"),
    )
    op.create_index("ix_calculation_runs_tenant_id", "calculation_runs", ["tenant_id"])
    op.create_index("ix_calculation_runs_inventory_id", "calculation_runs", ["inventory_id"])
    op.create_index("ix_calculation_runs_status", "calculation_runs", ["status"])

    op.create_table(
        "calculation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("calculation_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calculation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("activity_records.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("factor_resolution_record_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("factor_resolution_records.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("selected_factor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("emission_factors.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("method", calculation_method, nullable=False),
        sa.Column("scope", emission_scope, nullable=False),
        sa.Column("scope_3_category", sa.Integer(), nullable=True),
        sa.Column("scope_2_method", scope_2_method, nullable=False),
        sa.Column("original_activity_value", sa.Numeric(30, 15), nullable=False),
        sa.Column("original_activity_unit", sa.String(length=100), nullable=False),
        sa.Column("factor_activity_value", sa.Numeric(30, 15), nullable=False),
        sa.Column("factor_activity_unit", sa.String(length=100), nullable=False),
        sa.Column("factor_value", sa.Numeric(30, 15), nullable=True),
        sa.Column("allocation_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("allocation_multiplier", sa.Numeric(10, 8), nullable=False),
        sa.Column("gross_kg_co2e", sa.Numeric(30, 15), nullable=False),
        sa.Column("allocated_kg_co2e", sa.Numeric(30, 15), nullable=False),
        sa.Column("co2_kg", sa.Numeric(30, 15), nullable=True),
        sa.Column("ch4_kg_co2e", sa.Numeric(30, 15), nullable=True),
        sa.Column("n2o_kg_co2e", sa.Numeric(30, 15), nullable=True),
        sa.Column("calculation_formula", sa.String(length=500), nullable=False),
        sa.Column("intermediate_values", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("warnings", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("methodology_version", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("calculation_run_id", "activity_id", name="uq_calculation_result_run_activity"),
    )
    for column in ("tenant_id", "calculation_run_id", "activity_id", "factor_resolution_record_id", "selected_factor_id", "scope", "scope_3_category"):
        op.create_index(f"ix_calculation_results_{column}", "calculation_results", [column])


def downgrade() -> None:
    op.drop_table("calculation_results")
    op.drop_table("calculation_runs")
    op.drop_table("activity_records")
    for name in (
        "calculation_method",
        "calculation_run_status",
        "data_quality_level",
        "scope_2_method",
        "emission_scope",
        "activity_type",
        "activity_status",
    ):
        postgresql.ENUM(name=name).drop(op.get_bind(), checkfirst=True)
