"""Add query-aligned indexes for deterministic cursor pagination.

Revision ID: 0021
Revises: 0020
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql.elements import TextClause

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _descending(name: str) -> TextClause:
    return sa.text(f"{name} DESC")


def upgrade() -> None:
    op.create_index(
        "ix_data_accounting_connection_tenant_created_id",
        "data_accounting_connections",
        ["tenant_id", _descending("created_at"), _descending("id")],
    )
    op.create_index(
        "ix_data_accounting_sync_tenant_created_id",
        "data_accounting_sync_jobs",
        ["tenant_id", _descending("created_at"), _descending("id")],
    )
    op.create_index(
        "ix_data_accounting_sync_tenant_connection_created_id",
        "data_accounting_sync_jobs",
        [
            "tenant_id",
            "connection_id",
            _descending("created_at"),
            _descending("id"),
        ],
    )
    op.create_index(
        "ix_data_import_error_batch_created_id",
        "data_import_errors",
        ["batch_id", _descending("created_at"), _descending("id")],
    )
    op.create_index(
        "ix_calculation_result_tenant_run_created_id",
        "calculation_results",
        [
            "tenant_id",
            "calculation_run_id",
            "created_at",
            "id",
        ],
    )
    op.create_index(
        "ix_durable_workload_tenant_created_id",
        "durable_workloads",
        ["tenant_id", _descending("created_at"), _descending("id")],
    )
    op.create_index(
        "ix_durable_workload_tenant_status_created_id",
        "durable_workloads",
        [
            "tenant_id",
            "status",
            _descending("created_at"),
            _descending("id"),
        ],
    )
    op.create_index(
        "ix_durable_workload_tenant_type_created_id",
        "durable_workloads",
        [
            "tenant_id",
            "workload_type",
            _descending("created_at"),
            _descending("id"),
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_durable_workload_tenant_type_created_id",
        table_name="durable_workloads",
    )
    op.drop_index(
        "ix_durable_workload_tenant_status_created_id",
        table_name="durable_workloads",
    )
    op.drop_index(
        "ix_durable_workload_tenant_created_id",
        table_name="durable_workloads",
    )
    op.drop_index(
        "ix_calculation_result_tenant_run_created_id",
        table_name="calculation_results",
    )
    op.drop_index(
        "ix_data_import_error_batch_created_id",
        table_name="data_import_errors",
    )
    op.drop_index(
        "ix_data_accounting_sync_tenant_connection_created_id",
        table_name="data_accounting_sync_jobs",
    )
    op.drop_index(
        "ix_data_accounting_sync_tenant_created_id",
        table_name="data_accounting_sync_jobs",
    )
    op.drop_index(
        "ix_data_accounting_connection_tenant_created_id",
        table_name="data_accounting_connections",
    )
