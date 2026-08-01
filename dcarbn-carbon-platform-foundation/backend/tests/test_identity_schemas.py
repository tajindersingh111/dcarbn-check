import pytest
from pydantic import ValidationError

from app.schemas.identity import InvitationAccept, TenantOnboardingRequest


def test_invitation_accept_requires_matching_passwords() -> None:
    with pytest.raises(ValidationError):
        InvitationAccept(
            token="a" * 40,
            password="A-secure-password-2026",
            password_confirmation="Different-password-2026",
        )


def test_tenant_slug_is_validated() -> None:
    payload = TenantOnboardingRequest(
        tenant_name="Northstar Logistics",
        tenant_slug="northstar-logistics",
        owner_email="owner@example.com",
        owner_full_name="Tenant Owner",
    )
    assert payload.tenant_slug == "northstar-logistics"
