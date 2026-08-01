"""Add cookie-session MFA, password recovery and security monitoring.

Revision ID: 0010
Revises: 0009
"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    severity = postgresql.ENUM("info", "warning", "critical", name="security_event_severity", create_type=False)
    reset_status = postgresql.ENUM("pending", "used", "revoked", "expired", name="password_reset_status", create_type=False)
    severity.create(op.get_bind(), checkfirst=True)
    reset_status.create(op.get_bind(), checkfirst=True)

    op.add_column("users", sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("mfa_secret_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("mfa_pending_secret_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("mfa_recovery_codes_hashes", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("mfa_enabled_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "security_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("severity", severity, nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("ip_address", sa.String(100), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("event_data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    for c in ("tenant_id","user_id","event_type","severity"):
        op.create_index(f"ix_security_events_{c}", "security_events", [c])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("status", reset_status, nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_ip", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_tenant_id", "password_reset_tokens", ["tenant_id"])
    op.create_index("ix_password_reset_tokens_status", "password_reset_tokens", ["status"])

    op.create_table(
        "mfa_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ip_address", sa.String(100), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mfa_challenges_user_id", "mfa_challenges", ["user_id"])
    op.create_index("ix_mfa_challenges_tenant_id", "mfa_challenges", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("mfa_challenges")
    op.drop_table("password_reset_tokens")
    op.drop_table("security_events")
    for column in ("mfa_enabled_at","mfa_recovery_codes_hashes","mfa_pending_secret_encrypted","mfa_secret_encrypted","mfa_enabled"):
        op.drop_column("users", column)
    postgresql.ENUM(name="password_reset_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="security_event_severity").drop(op.get_bind(), checkfirst=True)
