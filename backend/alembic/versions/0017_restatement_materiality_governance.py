"""Add structured restatement materiality governance.

Revision ID: 0017
Revises: 0016
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


restatement_trigger = postgresql.ENUM(
    "ACQUISITION",
    "DIVESTMENT",
    "OUTSOURCING_INSOURCING",
    "ORGANISATIONAL_BOUNDARY_CHANGE",
    "OPERATIONAL_BOUNDARY_CHANGE",
    "METHODOLOGY_CHANGE",
    "EMISSION_FACTOR_CHANGE",
    "MATERIAL_ERROR",
    "OTHER",
    name="inventory_restatement_trigger",
    create_type=False,
)


def upgrade() -> None:
    restatement_trigger.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "inventory_restatements",
        sa.Column(
            "trigger",
            restatement_trigger,
            nullable=False,
            server_default="OTHER",
        ),
    )
    op.add_column(
        "inventory_restatements",
        sa.Column("estimated_impact_percent", sa.Numeric(10, 4), nullable=True),
    )
    op.add_column(
        "inventory_restatements",
        sa.Column(
            "significance_threshold_percent",
            sa.Numeric(7, 4),
            nullable=False,
            server_default=sa.text("5.0"),
        ),
    )
    op.add_column(
        "inventory_restatements",
        sa.Column(
            "threshold_exceeded",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "inventory_restatements",
        sa.Column(
            "qualitative_override",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "inventory_restatements",
        sa.Column("qualitative_override_rationale", sa.Text(), nullable=True),
    )
    op.add_column(
        "inventory_restatements",
        sa.Column("boundary_change_summary", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_inventory_restatements_trigger",
        "inventory_restatements",
        ["trigger"],
    )
    op.create_check_constraint(
        "inventory_restatement_impact_nonnegative",
        "inventory_restatements",
        "estimated_impact_percent IS NULL OR estimated_impact_percent >= 0",
    )
    op.create_check_constraint(
        "inventory_restatement_threshold_range",
        "inventory_restatements",
        "significance_threshold_percent > 0 AND significance_threshold_percent <= 100",
    )


def downgrade() -> None:
    op.drop_constraint(
        "inventory_restatement_threshold_range",
        "inventory_restatements",
        type_="check",
    )
    op.drop_constraint(
        "inventory_restatement_impact_nonnegative",
        "inventory_restatements",
        type_="check",
    )
    op.drop_index(
        "ix_inventory_restatements_trigger",
        table_name="inventory_restatements",
    )
    for column in (
        "boundary_change_summary",
        "qualitative_override_rationale",
        "qualitative_override",
        "threshold_exceeded",
        "significance_threshold_percent",
        "estimated_impact_percent",
        "trigger",
    ):
        op.drop_column("inventory_restatements", column)
    restatement_trigger.drop(op.get_bind(), checkfirst=True)
