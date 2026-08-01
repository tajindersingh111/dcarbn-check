"""Add progressive account-lockout state.

Revision ID: 0011
Revises: 0010
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "failed_login_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "last_failed_login_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "locked_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index("ix_users_locked_until", "users", ["locked_until"])


def downgrade() -> None:
    op.drop_index("ix_users_locked_until", table_name="users")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "last_failed_login_at")
    op.drop_column("users", "failed_login_count")
