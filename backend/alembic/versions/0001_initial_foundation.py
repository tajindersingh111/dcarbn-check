"""Create initial platform foundation.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inventory_status = postgresql.ENUM(
        "draft",
        "data_collection",
        "validation_required",
        "ready_for_calculation",
        "calculating",
        "review_required",
        "approved",
        "locked",
        "calculation_failed",
        "restatement_required",
        "superseded",
        name="inventory_status",
        create_type=False,
    )
    inventory_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "organisations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("legal_name", sa.String(length=250), nullable=True),
        sa.Column("registration_number", sa.String(length=100), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "name", name="uq_organisation_tenant_name"),
    )
    op.create_index("ix_organisations_tenant_id", "organisations", ["tenant_id"])

    op.create_table(
        "legal_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organisation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("registration_number", sa.String(length=100), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("ownership_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_legal_entities_tenant_id", "legal_entities", ["tenant_id"])
    op.create_index(
        "ix_legal_entities_organisation_id", "legal_entities", ["organisation_id"]
    )

    op.create_table(
        "sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organisation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("site_type", sa.String(length=100), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("postcode", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sites_tenant_id", "sites", ["tenant_id"])
    op.create_index("ix_sites_organisation_id", "sites", ["organisation_id"])

    op.create_table(
        "reporting_periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organisation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_base_year", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("end_date >= start_date", name="ck_reporting_period_dates"),
    )
    op.create_index("ix_reporting_periods_tenant_id", "reporting_periods", ["tenant_id"])

    op.create_table(
        "inventories",
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
        sa.Column(
            "status",
            inventory_status,
            nullable=False,
            server_default="draft",
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inventories_tenant_id", "inventories", ["tenant_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_type", sa.String(length=50), nullable=False),
        sa.Column("actor_id", sa.String(length=200), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source_system", sa.String(length=100), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.Column("event_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_tenant_id", "audit_events", ["tenant_id"])
    op.create_index(
        "ix_audit_events_entity", "audit_events", ["entity_type", "entity_id"]
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("inventories")
    op.drop_table("reporting_periods")
    op.drop_table("sites")
    op.drop_table("legal_entities")
    op.drop_table("organisations")
    op.drop_table("tenants")
    postgresql.ENUM(name="inventory_status").drop(op.get_bind(), checkfirst=True)
