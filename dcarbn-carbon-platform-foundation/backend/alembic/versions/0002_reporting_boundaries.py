"""Add reporting boundaries and organisational-control model.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    consolidation_approach = postgresql.ENUM(
        "operational_control",
        "financial_control",
        "equity_share",
        name="consolidation_approach",
        create_type=False,
    )
    boundary_status = postgresql.ENUM(
        "draft",
        "approved",
        "locked",
        "superseded",
        name="boundary_status",
        create_type=False,
    )
    membership_decision = postgresql.ENUM(
        "auto",
        "included",
        "excluded",
        name="membership_decision",
        create_type=False,
    )
    consolidation_approach.create(op.get_bind(), checkfirst=True)
    boundary_status.create(op.get_bind(), checkfirst=True)
    membership_decision.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "organisational_boundaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reporting_period_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reporting_periods.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("consolidation_approach", consolidation_approach, nullable=False),
        sa.Column(
            "status",
            boundary_status,
            nullable=False,
            server_default="draft",
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "control_threshold_percentage",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="50.00",
        ),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(length=200), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "reporting_period_id",
            "version",
            name="uq_boundary_reporting_period_version",
        ),
        sa.CheckConstraint(
            "control_threshold_percentage >= 0 "
            "AND control_threshold_percentage <= 100",
            name="ck_organisational_boundaries_boundary_control_threshold_range",
        ),
    )
    op.create_index(
        "ix_organisational_boundaries_tenant_id",
        "organisational_boundaries",
        ["tenant_id"],
    )
    op.create_index(
        "ix_organisational_boundaries_reporting_period_id",
        "organisational_boundaries",
        ["reporting_period_id"],
    )

    op.create_table(
        "boundary_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "boundary_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organisational_boundaries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "legal_entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("legal_entities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "decision",
            membership_decision,
            nullable=False,
            server_default="auto",
        ),
        sa.Column(
            "ownership_percentage",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column(
            "has_operational_control",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "has_financial_control",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("is_included", sa.Boolean(), nullable=False),
        sa.Column("allocation_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("evidence_reference", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "boundary_id",
            "legal_entity_id",
            "effective_from",
            name="uq_boundary_membership_entity_effective_from",
        ),
        sa.CheckConstraint(
            "ownership_percentage >= 0 AND ownership_percentage <= 100",
            name="ck_boundary_memberships_membership_ownership_range",
        ),
        sa.CheckConstraint(
            "allocation_percentage >= 0 AND allocation_percentage <= 100",
            name="ck_boundary_memberships_membership_allocation_range",
        ),
        sa.CheckConstraint(
            "effective_to >= effective_from",
            name="ck_boundary_memberships_membership_effective_dates",
        ),
    )
    op.create_index(
        "ix_boundary_memberships_tenant_id",
        "boundary_memberships",
        ["tenant_id"],
    )
    op.create_index(
        "ix_boundary_memberships_boundary_id",
        "boundary_memberships",
        ["boundary_id"],
    )
    op.create_index(
        "ix_boundary_memberships_legal_entity_id",
        "boundary_memberships",
        ["legal_entity_id"],
    )


def downgrade() -> None:
    op.drop_table("boundary_memberships")
    op.drop_table("organisational_boundaries")
    postgresql.ENUM(name="membership_decision").drop(
        op.get_bind(),
        checkfirst=True,
    )
    postgresql.ENUM(name="boundary_status").drop(
        op.get_bind(),
        checkfirst=True,
    )
    postgresql.ENUM(name="consolidation_approach").drop(
        op.get_bind(),
        checkfirst=True,
    )
