"""Add waste-generated activity type.

Revision ID: 0014
Revises: 0013
"""

from alembic import op


revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE activity_type ADD VALUE IF NOT EXISTS 'WASTE_GENERATED'")


def downgrade() -> None:
    # PostgreSQL enum values are intentionally retained to avoid destructive rewrites.
    pass
