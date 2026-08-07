from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final, Mapping


class ConnectorContractError(ValueError):
    """Raised when a connector request violates a governed contract."""


class AccountingProvider(StrEnum):
    CSV = "csv"
    QUICKBOOKS = "quickbooks"
    XERO = "xero"
    SAGE = "sage"
    API = "api"


class AuthenticationMode(StrEnum):
    NONE = "none"
    OAUTH2 = "oauth2"
    API_KEY = "api_key"


class ConnectionStatus(StrEnum):
    DRAFT = "draft"
    AUTHORIZING = "authorizing"
    ACTIVE = "active"
    ACTION_REQUIRED = "action_required"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class ProviderCapability:
    provider: AccountingProvider
    authentication_mode: AuthenticationMode
    supports_incremental_sync: bool
    supports_webhooks: bool
    requires_external_company_id: bool


PROVIDER_CAPABILITIES: Final[dict[AccountingProvider, ProviderCapability]] = {
    AccountingProvider.CSV: ProviderCapability(
        provider=AccountingProvider.CSV,
        authentication_mode=AuthenticationMode.NONE,
        supports_incremental_sync=False,
        supports_webhooks=False,
        requires_external_company_id=False,
    ),
    AccountingProvider.QUICKBOOKS: ProviderCapability(
        provider=AccountingProvider.QUICKBOOKS,
        authentication_mode=AuthenticationMode.OAUTH2,
        supports_incremental_sync=True,
        supports_webhooks=True,
        requires_external_company_id=True,
    ),
    AccountingProvider.XERO: ProviderCapability(
        provider=AccountingProvider.XERO,
        authentication_mode=AuthenticationMode.OAUTH2,
        supports_incremental_sync=True,
        supports_webhooks=True,
        requires_external_company_id=True,
    ),
    AccountingProvider.SAGE: ProviderCapability(
        provider=AccountingProvider.SAGE,
        authentication_mode=AuthenticationMode.OAUTH2,
        supports_incremental_sync=True,
        supports_webhooks=False,
        requires_external_company_id=True,
    ),
    AccountingProvider.API: ProviderCapability(
        provider=AccountingProvider.API,
        authentication_mode=AuthenticationMode.API_KEY,
        supports_incremental_sync=True,
        supports_webhooks=False,
        requires_external_company_id=True,
    ),
}


@dataclass(frozen=True, slots=True)
class MappingProfile:
    provider: AccountingProvider
    version: str
    mappings: Mapping[str, str]

    def validate(self, required_targets: tuple[str, ...]) -> None:
        if not self.version.strip():
            raise ConnectorContractError("Mapping profile version is required")

        missing = [
            target
            for target in required_targets
            if not self.mappings.get(target, "").strip()
        ]
        if missing:
            raise ConnectorContractError(
                "Missing required target mappings: " + ", ".join(sorted(missing))
            )

        sources = [
            source.strip()
            for source in self.mappings.values()
            if source.strip()
        ]
        duplicates = sorted(
            source for source in set(sources) if sources.count(source) > 1
        )
        if duplicates:
            raise ConnectorContractError(
                "A source field may map to only one governed target: "
                + ", ".join(duplicates)
            )


@dataclass(frozen=True, slots=True)
class SyncRequest:
    tenant_id: str
    external_customer_id: str
    provider: AccountingProvider
    external_company_id: str | None
    mapping_profile_version: str
    cursor: str | None = None
    requested_from: datetime | None = None
    requested_to: datetime | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("tenant_id", self.tenant_id),
            ("external_customer_id", self.external_customer_id),
            ("mapping_profile_version", self.mapping_profile_version),
        ):
            if not value.strip():
                raise ConnectorContractError(f"{label} is required")

        capability = PROVIDER_CAPABILITIES[self.provider]
        if (
            capability.requires_external_company_id
            and not (self.external_company_id or "").strip()
        ):
            raise ConnectorContractError(
                f"external_company_id is required for {self.provider.value}"
            )
        if (
            self.requested_from
            and self.requested_to
            and self.requested_to < self.requested_from
        ):
            raise ConnectorContractError(
                "requested_to must not precede requested_from"
            )

    @property
    def sync_identity(self) -> str:
        payload = {
            "tenant_id": self.tenant_id,
            "external_customer_id": self.external_customer_id,
            "provider": self.provider.value,
            "external_company_id": self.external_company_id,
            "mapping_profile_version": self.mapping_profile_version,
            "cursor": self.cursor,
            "requested_from": (
                self.requested_from.isoformat() if self.requested_from else None
            ),
            "requested_to": (
                self.requested_to.isoformat() if self.requested_to else None
            ),
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


SENSITIVE_KEY_MARKERS: Final[tuple[str, ...]] = (
    "access_token",
    "api_key",
    "authorization",
    "client_secret",
    "credential",
    "password",
    "refresh_token",
    "secret",
    "token",
)


def redact_connector_diagnostics(value: object) -> object:
    """Return diagnostics safe for API responses, logs and audit metadata."""

    if isinstance(value, Mapping):
        redacted: dict[str, object] = {}
        for key, item in value.items():
            normalized_key = str(key).lower()
            if any(marker in normalized_key for marker in SENSITIVE_KEY_MARKERS):
                redacted[str(key)] = "[REDACTED]"
            else:
                redacted[str(key)] = redact_connector_diagnostics(item)
        return redacted
    if isinstance(value, list):
        return [redact_connector_diagnostics(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_connector_diagnostics(item) for item in value)
    if isinstance(value, str) and value.lower().startswith("bearer "):
        return "[REDACTED]"
    return value
