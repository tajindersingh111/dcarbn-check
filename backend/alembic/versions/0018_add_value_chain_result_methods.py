"""Add governed supplier-specific value-chain result types.

Revision ID: 0018
Revises: 0017
"""

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE activity_type ADD VALUE IF NOT EXISTS 'VALUE_CHAIN_RESULT'")
    op.execute(
        "ALTER TYPE calculation_method ADD VALUE IF NOT EXISTS "
        "'SUPPLIER_SPECIFIC_RESULT'"
    )


def downgrade() -> None:
    # PostgreSQL enum values are retained to avoid destructive table rewrites.
    pass
