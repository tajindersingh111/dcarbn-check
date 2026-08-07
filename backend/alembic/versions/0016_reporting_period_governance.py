"""Add governed base-year and comparative reporting-period controls.

Revision ID: 0016
Revises: 0015
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reporting_periods",
        sa.Column("base_year_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "reporting_periods",
        sa.Column("recalculation_policy", sa.Text(), nullable=True),
    )
    op.add_column(
        "reporting_periods",
        sa.Column(
            "recalculation_significance_threshold_percent",
            sa.Numeric(7, 4),
            nullable=False,
            server_default=sa.text("5.0"),
        ),
    )
    op.add_column(
        "reporting_periods",
        sa.Column("comparative_reporting_period_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_reporting_periods_comparative_period",
        "reporting_periods",
        "reporting_periods",
        ["comparative_reporting_period_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_reporting_periods_comparative_reporting_period_id",
        "reporting_periods",
        ["comparative_reporting_period_id"],
    )
    op.create_check_constraint(
        "reporting_period_recalculation_threshold",
        "reporting_periods",
        "recalculation_significance_threshold_percent > 0 "
        "AND recalculation_significance_threshold_percent <= 100",
    )
    op.create_index(
        "uq_reporting_periods_organisation_base_year",
        "reporting_periods",
        ["organisation_id"],
        unique=True,
        postgresql_where=sa.text("is_base_year IS TRUE"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_reporting_periods_organisation_base_year",
        table_name="reporting_periods",
    )
    op.drop_constraint(
        "reporting_period_recalculation_threshold",
        "reporting_periods",
        type_="check",
    )
    op.drop_index(
        "ix_reporting_periods_comparative_reporting_period_id",
        table_name="reporting_periods",
    )
    op.drop_constraint(
        "fk_reporting_periods_comparative_period",
        "reporting_periods",
        type_="foreignkey",
    )
    for column in (
        "comparative_reporting_period_id",
        "recalculation_significance_threshold_percent",
        "recalculation_policy",
        "base_year_reason",
    ):
        op.drop_column("reporting_periods", column)
