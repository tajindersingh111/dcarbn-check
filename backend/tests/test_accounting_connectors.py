from datetime import UTC, datetime

import pytest

from app.integrations.data.accounting_connectors import (
    AccountingProvider,
    AuthenticationMode,
    ConnectorContractError,
    MappingProfile,
    PROVIDER_CAPABILITIES,
    SyncRequest,
    redact_connector_diagnostics,
)


def test_provider_register_declares_safe_authentication_modes() -> None:
    assert PROVIDER_CAPABILITIES[AccountingProvider.CSV].authentication_mode == (
        AuthenticationMode.NONE
    )
    assert PROVIDER_CAPABILITIES[
        AccountingProvider.QUICKBOOKS
    ].authentication_mode == AuthenticationMode.OAUTH2
    assert PROVIDER_CAPABILITIES[
        AccountingProvider.XERO
    ].supports_incremental_sync
    assert PROVIDER_CAPABILITIES[
        AccountingProvider.SAGE
    ].requires_external_company_id
    assert PROVIDER_CAPABILITIES[AccountingProvider.API].authentication_mode == (
        AuthenticationMode.API_KEY
    )


def test_mapping_profile_requires_each_governed_target() -> None:
    profile = MappingProfile(
        provider=AccountingProvider.XERO,
        version="2026.1",
        mappings={"supplier_name": "ContactName"},
    )

    with pytest.raises(
        ConnectorContractError,
        match="Missing required target mappings: evidence_reference",
    ):
        profile.validate(("supplier_name", "evidence_reference"))


def test_mapping_profile_rejects_reused_source_field() -> None:
    profile = MappingProfile(
        provider=AccountingProvider.QUICKBOOKS,
        version="2026.1",
        mappings={
            "supplier_name": "VendorName",
            "description": "VendorName",
        },
    )

    with pytest.raises(
        ConnectorContractError,
        match="source field may map to only one governed target",
    ):
        profile.validate(("supplier_name", "description"))


def test_sync_identity_is_deterministic_and_cursor_sensitive() -> None:
    request = SyncRequest(
        tenant_id="tenant-1",
        external_customer_id="customer-1042",
        provider=AccountingProvider.XERO,
        external_company_id="xero-tenant-7",
        mapping_profile_version="2026.1",
        cursor="page-42",
        requested_from=datetime(2026, 1, 1, tzinfo=UTC),
        requested_to=datetime(2026, 6, 30, tzinfo=UTC),
    )
    duplicate = SyncRequest(
        tenant_id="tenant-1",
        external_customer_id="customer-1042",
        provider=AccountingProvider.XERO,
        external_company_id="xero-tenant-7",
        mapping_profile_version="2026.1",
        cursor="page-42",
        requested_from=datetime(2026, 1, 1, tzinfo=UTC),
        requested_to=datetime(2026, 6, 30, tzinfo=UTC),
    )
    next_page = SyncRequest(
        tenant_id="tenant-1",
        external_customer_id="customer-1042",
        provider=AccountingProvider.XERO,
        external_company_id="xero-tenant-7",
        mapping_profile_version="2026.1",
        cursor="page-43",
        requested_from=datetime(2026, 1, 1, tzinfo=UTC),
        requested_to=datetime(2026, 6, 30, tzinfo=UTC),
    )

    assert request.sync_identity == duplicate.sync_identity
    assert len(request.sync_identity) == 64
    assert request.sync_identity != next_page.sync_identity


def test_connected_provider_requires_external_company_identity() -> None:
    with pytest.raises(
        ConnectorContractError,
        match="external_company_id is required for quickbooks",
    ):
        SyncRequest(
            tenant_id="tenant-1",
            external_customer_id="customer-1042",
            provider=AccountingProvider.QUICKBOOKS,
            external_company_id=None,
            mapping_profile_version="2026.1",
        )


def test_sync_request_rejects_reversed_window() -> None:
    with pytest.raises(
        ConnectorContractError,
        match="requested_to must not precede requested_from",
    ):
        SyncRequest(
            tenant_id="tenant-1",
            external_customer_id="customer-1042",
            provider=AccountingProvider.API,
            external_company_id="source-company-1",
            mapping_profile_version="2026.1",
            requested_from=datetime(2026, 7, 1, tzinfo=UTC),
            requested_to=datetime(2026, 6, 30, tzinfo=UTC),
        )


def test_connector_diagnostics_redact_nested_secrets() -> None:
    diagnostics = {
        "provider": "xero",
        "access_token": "access-value",
        "nested": {
            "client_secret": "secret-value",
            "headers": ["Bearer abc123", "application/json"],
        },
        "cursor": "page-42",
    }

    assert redact_connector_diagnostics(diagnostics) == {
        "provider": "xero",
        "access_token": "[REDACTED]",
        "nested": {
            "client_secret": "[REDACTED]",
            "headers": ["[REDACTED]", "application/json"],
        },
        "cursor": "page-42",
    }
