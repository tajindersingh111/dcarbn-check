"""Add versioned methodology registry.

Revision ID: 0013
Revises: 0012
"""

from alembic import op
import sqlalchemy as sa


revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    methodology_status = sa.Enum(
        "DRAFT",
        "IN_REVIEW",
        "APPROVED",
        "ACTIVE",
        "RETIRED",
        "SUPERSEDED",
        name="methodology_status",
    )
    op.create_table(
        "methodology_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("method_key", sa.String(length=250), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("status", methodology_status, nullable=False),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.Column("scope_3_category", sa.Integer(), nullable=True),
        sa.Column("jurisdiction", sa.String(length=20), nullable=False),
        sa.Column("reporting_year", sa.Integer(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("output_unit", sa.String(length=100), nullable=False),
        sa.Column("input_schema", sa.JSON(), nullable=False),
        sa.Column("validation_rules", sa.JSON(), nullable=False),
        sa.Column("golden_tests", sa.JSON(), nullable=False),
        sa.Column("source_reference", sa.String(length=1000), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=200), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(length=200), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by", sa.String(length=200), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supersedes_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["supersedes_version_id"],
            ["methodology_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "method_key",
            "version",
            name="uq_methodology_key_version",
        ),
    )
    op.create_index(
        op.f("ix_methodology_versions_method_key"),
        "methodology_versions",
        ["method_key"],
    )
    op.create_index(
        op.f("ix_methodology_versions_status"),
        "methodology_versions",
        ["status"],
    )
    op.create_index(
        op.f("ix_methodology_versions_scope"),
        "methodology_versions",
        ["scope"],
    )
    op.create_index(
        op.f("ix_methodology_versions_scope_3_category"),
        "methodology_versions",
        ["scope_3_category"],
    )
    op.create_index(
        op.f("ix_methodology_versions_reporting_year"),
        "methodology_versions",
        ["reporting_year"],
    )


def downgrade() -> None:
    for index in (
        "reporting_year",
        "scope_3_category",
        "scope",
        "status",
        "method_key",
    ):
        op.drop_index(
            op.f(f"ix_methodology_versions_{index}"),
            table_name="methodology_versions",
        )
    op.drop_table("methodology_versions")
    sa.Enum(name="methodology_status").drop(op.get_bind(), checkfirst=True)
