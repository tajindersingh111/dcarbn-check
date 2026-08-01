"""Add versioned emission-factor registry and import tracking.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    factor_set_status = postgresql.ENUM(
        "draft",
        "approved",
        "superseded",
        "rejected",
        name="factor_set_status",
        create_type=False,
    )
    factor_import_status = postgresql.ENUM(
        "queued",
        "processing",
        "completed",
        "failed",
        "duplicate",
        name="factor_import_status",
        create_type=False,
    )
    greenhouse_gas_component = postgresql.ENUM(
        "total_co2e",
        "co2",
        "ch4",
        "n2o",
        "other",
        name="greenhouse_gas_component",
        create_type=False,
    )
    factor_set_status.create(op.get_bind(), checkfirst=True)
    factor_import_status.create(op.get_bind(), checkfirst=True)
    greenhouse_gas_component.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "emission_factor_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("publisher", sa.String(length=250), nullable=False),
        sa.Column("dataset_name", sa.String(length=300), nullable=False),
        sa.Column("dataset_version", sa.String(length=100), nullable=False),
        sa.Column("reporting_year", sa.Integer(), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=False),
        sa.Column(
            "geography_code",
            sa.String(length=20),
            nullable=False,
            server_default="GB",
        ),
        sa.Column("source_filename", sa.String(length=500), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_reference", sa.String(length=1000), nullable=True),
        sa.Column("methodology_reference", sa.String(length=1000), nullable=True),
        sa.Column("licence_name", sa.String(length=250), nullable=True),
        sa.Column("licence_reference", sa.String(length=1000), nullable=True),
        sa.Column("status", factor_set_status, nullable=False, server_default="draft"),
        sa.Column(
            "is_authoritative",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("imported_by", sa.String(length=200), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(length=200), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "superseded_by_set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("emission_factor_sets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "publisher",
            "dataset_name",
            "dataset_version",
            "source_sha256",
            name="uq_factor_set_source_version_hash",
        ),
    )
    op.create_index(
        "ix_emission_factor_sets_publisher",
        "emission_factor_sets",
        ["publisher"],
    )
    op.create_index(
        "ix_emission_factor_sets_reporting_year",
        "emission_factor_sets",
        ["reporting_year"],
    )
    op.create_index(
        "ix_emission_factor_sets_source_sha256",
        "emission_factor_sets",
        ["source_sha256"],
    )

    op.create_table(
        "emission_factors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "factor_set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("emission_factor_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_factor_id", sa.String(length=150), nullable=False),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.Column("level_1", sa.String(length=250), nullable=False),
        sa.Column("level_2", sa.String(length=250), nullable=True),
        sa.Column("level_3", sa.String(length=250), nullable=True),
        sa.Column("level_4", sa.String(length=250), nullable=True),
        sa.Column("column_text", sa.String(length=500), nullable=True),
        sa.Column("activity_unit", sa.String(length=100), nullable=False),
        sa.Column("factor_unit_text", sa.String(length=250), nullable=False),
        sa.Column(
            "greenhouse_gas_component",
            greenhouse_gas_component,
            nullable=False,
        ),
        sa.Column("greenhouse_gas_label", sa.String(length=100), nullable=False),
        sa.Column("factor_value", sa.Numeric(30, 15), nullable=False),
        sa.Column(
            "factor_numerator_unit",
            sa.String(length=100),
            nullable=False,
            server_default="kg CO2e",
        ),
        sa.Column("factor_denominator_unit", sa.String(length=100), nullable=False),
        sa.Column(
            "geography_code",
            sa.String(length=20),
            nullable=False,
            server_default="GB",
        ),
        sa.Column("reporting_year", sa.Integer(), nullable=False),
        sa.Column("lifecycle_boundary", sa.String(length=150), nullable=True),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("raw_source_data", postgresql.JSONB(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "factor_set_id",
            "source_factor_id",
            name="uq_factor_set_source_factor_id",
        ),
    )
    for column in (
        "factor_set_id",
        "scope",
        "level_1",
        "level_2",
        "level_3",
        "level_4",
        "activity_unit",
        "greenhouse_gas_component",
        "reporting_year",
    ):
        op.create_index(
            f"ix_emission_factors_{column}",
            "emission_factors",
            [column],
        )

    op.create_table(
        "factor_import_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "factor_set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("emission_factor_sets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            factor_import_status,
            nullable=False,
            server_default="queued",
        ),
        sa.Column("source_filename", sa.String(length=500), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("dataset_version", sa.String(length=100), nullable=False),
        sa.Column("reporting_year", sa.Integer(), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imported_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by", sa.String(length=200), nullable=False),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_factor_import_jobs_factor_set_id",
        "factor_import_jobs",
        ["factor_set_id"],
    )
    op.create_index(
        "ix_factor_import_jobs_source_sha256",
        "factor_import_jobs",
        ["source_sha256"],
    )

    op.create_table(
        "factor_import_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "import_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("factor_import_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("worksheet_name", sa.String(length=250), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("raw_row_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_factor_import_errors_import_job_id",
        "factor_import_errors",
        ["import_job_id"],
    )


def downgrade() -> None:
    op.drop_table("factor_import_errors")
    op.drop_table("factor_import_jobs")
    op.drop_table("emission_factors")
    op.drop_table("emission_factor_sets")
    postgresql.ENUM(name="greenhouse_gas_component").drop(
        op.get_bind(),
        checkfirst=True,
    )
    postgresql.ENUM(name="factor_import_status").drop(
        op.get_bind(),
        checkfirst=True,
    )
    postgresql.ENUM(name="factor_set_status").drop(
        op.get_bind(),
        checkfirst=True,
    )
