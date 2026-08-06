"""Add DcarbN and UK Government calculation comparison foundation.

Revision ID: 0015
Revises: 0014
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    comparison_status = postgresql.ENUM(
        "pending",
        "ready",
        "unavailable",
        name="data_comparison_status",
        create_type=False,
    )
    reporting_basis = postgresql.ENUM(
        "dcarbn_operational",
        "uk_government",
        name="data_reporting_basis",
        create_type=False,
    )
    comparison_status.create(op.get_bind(), checkfirst=True)
    reporting_basis.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "data_operational_emissions",
        sa.Column("external_activity_key", sa.String(200), nullable=True),
    )
    op.add_column(
        "data_operational_emissions",
        sa.Column("method_identifier", sa.String(200), nullable=True),
    )
    op.add_column(
        "data_operational_emissions",
        sa.Column("calculation_software_version", sa.String(100), nullable=True),
    )
    op.add_column(
        "data_operational_emissions",
        sa.Column("reporting_period_start", sa.Date(), nullable=True),
    )
    op.add_column(
        "data_operational_emissions",
        sa.Column("reporting_period_end", sa.Date(), nullable=True),
    )
    op.add_column(
        "data_operational_emissions",
        sa.Column("uncertainty_percentage", sa.Numeric(10, 4), nullable=True),
    )
    op.add_column(
        "data_operational_emissions",
        sa.Column(
            "comparison_inputs_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index(
        "ix_data_operational_emissions_external_activity_key",
        "data_operational_emissions",
        ["external_activity_key"],
    )

    op.create_table(
        "data_calculation_comparisons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "operational_emission_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_operational_emissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("comparison_group_key", sa.String(300), nullable=False),
        sa.Column(
            "dcarbn_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calculation_results.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "government_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calculation_results.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "status",
            comparison_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "reporting_basis",
            reporting_basis,
            nullable=False,
            server_default="dcarbn_operational",
        ),
        sa.Column("basis_reason", sa.Text(), nullable=True),
        sa.Column("basis_selected_by", sa.String(200), nullable=True),
        sa.Column("basis_selected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comparison_unavailable_reason", sa.Text(), nullable=True),
        sa.Column("absolute_delta_kg_co2e", sa.Numeric(30, 15), nullable=True),
        sa.Column("percentage_delta", sa.Numeric(18, 8), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "comparison_group_key",
            name="uq_data_comparison_group",
        ),
        sa.UniqueConstraint(
            "operational_emission_id",
            name="uq_data_comparison_operational_emission",
        ),
    )
    for column in (
        "tenant_id",
        "operational_emission_id",
        "dcarbn_result_id",
        "government_result_id",
        "status",
    ):
        op.create_index(
            f"ix_data_calculation_comparisons_{column}",
            "data_calculation_comparisons",
            [column],
        )


def downgrade() -> None:
    op.drop_table("data_calculation_comparisons")
    op.drop_index(
        "ix_data_operational_emissions_external_activity_key",
        table_name="data_operational_emissions",
    )
    for column in (
        "comparison_inputs_json",
        "uncertainty_percentage",
        "reporting_period_end",
        "reporting_period_start",
        "calculation_software_version",
        "method_identifier",
        "external_activity_key",
    ):
        op.drop_column("data_operational_emissions", column)
    postgresql.ENUM(name="data_reporting_basis").drop(
        op.get_bind(),
        checkfirst=True,
    )
    postgresql.ENUM(name="data_comparison_status").drop(
        op.get_bind(),
        checkfirst=True,
    )
