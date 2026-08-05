"""Add mandatory Scope 3 category dispositions.

Revision ID: 0012
Revises: 0011
"""

from alembic import op
import sqlalchemy as sa


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    disposition_status = sa.Enum(
        "INCLUDED",
        "NOT_RELEVANT",
        "EXCLUDED",
        name="scope_3_category_disposition_status",
    )
    op.create_table(
        "scope_3_category_dispositions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.Integer(), nullable=False),
        sa.Column("disposition", disposition_status, nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("evidence_reference", sa.String(length=1000), nullable=True),
        sa.Column("prepared_by", sa.String(length=200), nullable=False),
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.String(length=200), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category >= 1 AND category <= 15",
            name=op.f("ck_scope_3_category_dispositions_scope_3_disposition_category_range"),
        ),
        sa.ForeignKeyConstraint(
            ["inventory_id"],
            ["inventories.id"],
            name=op.f("fk_scope_3_category_dispositions_inventory_id_inventories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_scope_3_category_dispositions_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_scope_3_category_dispositions"),
        ),
        sa.UniqueConstraint(
            "inventory_id",
            "category",
            name="uq_scope_3_disposition_inventory_category",
        ),
    )
    op.create_index(
        op.f("ix_scope_3_category_dispositions_inventory_id"),
        "scope_3_category_dispositions",
        ["inventory_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scope_3_category_dispositions_tenant_id"),
        "scope_3_category_dispositions",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_scope_3_category_dispositions_tenant_id"),
        table_name="scope_3_category_dispositions",
    )
    op.drop_index(
        op.f("ix_scope_3_category_dispositions_inventory_id"),
        table_name="scope_3_category_dispositions",
    )
    op.drop_table("scope_3_category_dispositions")
    sa.Enum(name="scope_3_category_disposition_status").drop(
        op.get_bind(),
        checkfirst=True,
    )
