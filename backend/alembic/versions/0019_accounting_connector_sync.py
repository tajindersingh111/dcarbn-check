"""Add tenant-scoped accounting connections and sync jobs.

Revision ID: 0019
Revises: 0018
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_accounting_connections",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("organisation_id", sa.Uuid(), nullable=False),
        sa.Column("external_customer_id", sa.String(200), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("external_company_id", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(300), nullable=False),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("secret_reference", sa.String(500), nullable=True),
        sa.Column("mapping_profile_version", sa.String(100), nullable=False),
        sa.Column("mapping_json", sa.JSON(), nullable=False),
        sa.Column("last_cursor", sa.String(1000), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(100), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "provider",
            "external_company_id",
            name="uq_data_accounting_connection_company",
        ),
    )
    op.create_index(
        "ix_data_accounting_connections_tenant_id",
        "data_accounting_connections",
        ["tenant_id"],
    )
    op.create_index(
        "ix_data_accounting_connections_organisation_id",
        "data_accounting_connections",
        ["organisation_id"],
    )
    op.create_index(
        "ix_data_accounting_connections_provider",
        "data_accounting_connections",
        ["provider"],
    )
    op.create_index(
        "ix_data_accounting_connections_status",
        "data_accounting_connections",
        ["status"],
    )

    op.create_table(
        "data_accounting_sync_jobs",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("sync_identity", sa.String(64), nullable=False),
        sa.Column("cursor_before", sa.String(1000), nullable=True),
        sa.Column("cursor_after", sa.String(1000), nullable=True),
        sa.Column("requested_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="queued",
        ),
        sa.Column(
            "records_received",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "records_imported",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "records_rejected",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("requested_by", sa.String(200), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(100), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["data_accounting_connections.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "sync_identity",
            name="uq_data_accounting_sync_identity",
        ),
    )
    op.create_index(
        "ix_data_accounting_sync_jobs_tenant_id",
        "data_accounting_sync_jobs",
        ["tenant_id"],
    )
    op.create_index(
        "ix_data_accounting_sync_jobs_connection_id",
        "data_accounting_sync_jobs",
        ["connection_id"],
    )
    op.create_index(
        "ix_data_accounting_sync_jobs_status",
        "data_accounting_sync_jobs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_data_accounting_sync_jobs_status",
        table_name="data_accounting_sync_jobs",
    )
    op.drop_index(
        "ix_data_accounting_sync_jobs_connection_id",
        table_name="data_accounting_sync_jobs",
    )
    op.drop_index(
        "ix_data_accounting_sync_jobs_tenant_id",
        table_name="data_accounting_sync_jobs",
    )
    op.drop_table("data_accounting_sync_jobs")

    op.drop_index(
        "ix_data_accounting_connections_status",
        table_name="data_accounting_connections",
    )
    op.drop_index(
        "ix_data_accounting_connections_provider",
        table_name="data_accounting_connections",
    )
    op.drop_index(
        "ix_data_accounting_connections_organisation_id",
        table_name="data_accounting_connections",
    )
    op.drop_index(
        "ix_data_accounting_connections_tenant_id",
        table_name="data_accounting_connections",
    )
    op.drop_table("data_accounting_connections")
