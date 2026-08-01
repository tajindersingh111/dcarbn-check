"""Add unit-normalisation and factor-resolution records.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    resolution_outcome = postgresql.ENUM(
        "resolved",
        "ambiguous",
        "no_match",
        "incompatible_unit",
        name="resolution_outcome",
        create_type=False,
    )
    factor_match_strength = postgresql.ENUM(
        "exact",
        "strong",
        "fallback",
        name="factor_match_strength",
        create_type=False,
    )
    resolution_source = postgresql.ENUM(
        "api",
        "calculation_engine",
        "data_import",
        "manual",
        name="resolution_source",
        create_type=False,
    )
    resolution_outcome.create(op.get_bind(), checkfirst=True)
    factor_match_strength.create(op.get_bind(), checkfirst=True)
    resolution_source.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "factor_resolution_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "inventory_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inventories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "selected_factor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("emission_factors.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("outcome", resolution_outcome, nullable=False),
        sa.Column("match_strength", factor_match_strength, nullable=True),
        sa.Column(
            "source",
            resolution_source,
            nullable=False,
            server_default="api",
        ),
        sa.Column(
            "original_activity_value",
            sa.Numeric(30, 15),
            nullable=False,
        ),
        sa.Column(
            "original_activity_unit",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "normalized_activity_value",
            sa.Numeric(30, 15),
            nullable=True,
        ),
        sa.Column(
            "normalized_activity_unit",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "selected_factor_activity_value",
            sa.Numeric(30, 15),
            nullable=True,
        ),
        sa.Column(
            "selected_factor_activity_unit",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "selected_factor_value",
            sa.Numeric(30, 15),
            nullable=True,
        ),
        sa.Column(
            "resulting_kg_co2e",
            sa.Numeric(30, 15),
            nullable=True,
        ),
        sa.Column("selected_score", sa.Integer(), nullable=True),
        sa.Column("criteria", postgresql.JSONB(), nullable=False),
        sa.Column(
            "candidate_summary",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "warnings",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_factor_resolution_records_tenant_id",
        "factor_resolution_records",
        ["tenant_id"],
    )
    op.create_index(
        "ix_factor_resolution_records_inventory_id",
        "factor_resolution_records",
        ["inventory_id"],
    )
    op.create_index(
        "ix_factor_resolution_records_selected_factor_id",
        "factor_resolution_records",
        ["selected_factor_id"],
    )
    op.create_index(
        "ix_factor_resolution_records_outcome",
        "factor_resolution_records",
        ["outcome"],
    )


def downgrade() -> None:
    op.drop_table("factor_resolution_records")
    postgresql.ENUM(name="resolution_source").drop(
        op.get_bind(),
        checkfirst=True,
    )
    postgresql.ENUM(name="factor_match_strength").drop(
        op.get_bind(),
        checkfirst=True,
    )
    postgresql.ENUM(name="resolution_outcome").drop(
        op.get_bind(),
        checkfirst=True,
    )
