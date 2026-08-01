"""Add DATa operational-emissions review and conversion workflow.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    data_review_status = postgresql.ENUM(
        "pending",
        "in_review",
        "approved",
        "rejected",
        "converted",
        name="data_review_status",
        create_type=False,
    )
    data_review_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "data_operational_emission_reviews",
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
            sa.ForeignKey(
                "data_operational_emissions.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "inventory_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inventories.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "status",
            data_review_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("reviewer_id", sa.String(length=200), nullable=True),
        sa.Column(
            "review_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_comment", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("conversion_failure", sa.Text(), nullable=True),
        sa.Column(
            "calculation_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calculation_runs.id", ondelete="RESTRICT"),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "calculation_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calculation_results.id", ondelete="RESTRICT"),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "activity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activity_records.id", ondelete="RESTRICT"),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "review_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "operational_emission_id",
            name="uq_data_review_operational_emission",
        ),
    )
    op.create_index(
        "ix_data_operational_emission_reviews_tenant_id",
        "data_operational_emission_reviews",
        ["tenant_id"],
    )
    op.create_index(
        "ix_data_operational_emission_reviews_operational_emission_id",
        "data_operational_emission_reviews",
        ["operational_emission_id"],
    )
    op.create_index(
        "ix_data_operational_emission_reviews_inventory_id",
        "data_operational_emission_reviews",
        ["inventory_id"],
    )
    op.create_index(
        "ix_data_operational_emission_reviews_status",
        "data_operational_emission_reviews",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("data_operational_emission_reviews")
    postgresql.ENUM(name="data_review_status").drop(
        op.get_bind(),
        checkfirst=True,
    )
