from app.models.data_integration import (
    DataAccountingConnection,
    DataAccountingSyncJob,
)


def test_accounting_connection_schema_is_tenant_scoped_and_secret_safe() -> None:
    columns = DataAccountingConnection.__table__.columns

    assert {"tenant_id", "organisation_id", "provider"} <= set(columns.keys())
    assert {
        "external_customer_id",
        "external_company_id",
        "mapping_profile_version",
        "mapping_json",
    } <= set(columns.keys())
    assert "secret_reference" in columns
    assert "access_token" not in columns
    assert "refresh_token" not in columns
    assert "password" not in columns
    assert "api_key" not in columns


def test_accounting_connection_company_identity_is_unique_per_tenant() -> None:
    constraint_names = {
        constraint.name
        for constraint in DataAccountingConnection.__table__.constraints
    }

    assert "uq_data_accounting_connection_company" in constraint_names


def test_accounting_sync_job_has_idempotent_identity_and_audit_fields() -> None:
    columns = DataAccountingSyncJob.__table__.columns
    constraint_names = {
        constraint.name
        for constraint in DataAccountingSyncJob.__table__.constraints
    }

    assert "uq_data_accounting_sync_identity" in constraint_names
    assert {"tenant_id", "connection_id", "sync_identity"} <= set(columns.keys())
    assert {
        "cursor_before",
        "cursor_after",
        "requested_from",
        "requested_to",
        "requested_by",
    } <= set(columns.keys())
    assert {
        "records_received",
        "records_imported",
        "records_rejected",
        "diagnostics_json",
    } <= set(columns.keys())
