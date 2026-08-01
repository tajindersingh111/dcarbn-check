"""Add DATa integration records, batch imports and reconciliation.

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    data_import_status = postgresql.ENUM(
        "queued", "processing", "completed", "partial", "failed", "duplicate",
        name="data_import_status", create_type=False,
    )
    data_record_type = postgresql.ENUM(
        "vehicle", "shipment", "journey", "fuel", "payload", "operational_emission",
        name="data_record_type", create_type=False,
    )
    data_classification_status = postgresql.ENUM(
        "suggested", "confirmed", "rejected", "review_required",
        name="data_classification_status", create_type=False,
    )
    for enum in (
        data_import_status,
        data_record_type,
        data_classification_status,
    ):
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "data_organisation_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_customer_id", sa.String(200), nullable=False),
        sa.Column("external_customer_name", sa.String(300), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("mapping_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "external_customer_id", name="uq_data_mapping_external_customer"),
    )
    op.create_index("ix_data_organisation_mappings_tenant_id", "data_organisation_mappings", ["tenant_id"])
    op.create_index("ix_data_organisation_mappings_organisation_id", "data_organisation_mappings", ["organisation_id"])

    op.create_table(
        "data_import_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("schema_version", sa.String(50), nullable=False),
        sa.Column("record_type", data_record_type, nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("source_payload_sha256", sa.String(64), nullable=False),
        sa.Column("status", data_import_status, nullable=False, server_default="queued"),
        sa.Column("records_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by", sa.String(200), nullable=False),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_data_import_batch_idempotency"),
    )
    op.create_index("ix_data_import_batches_tenant_id", "data_import_batches", ["tenant_id"])
    op.create_index("ix_data_import_batches_record_type", "data_import_batches", ["record_type"])
    op.create_index("ix_data_import_batches_status", "data_import_batches", ["status"])

    op.create_table(
        "data_import_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_import_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("record_index", sa.Integer(), nullable=True),
        sa.Column("external_record_id", sa.String(200), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("raw_record", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_data_import_errors_batch_id", "data_import_errors", ["batch_id"])

    def standard_columns(table_name: str, id_column: str) -> None:
        op.create_index(f"ix_{table_name}_tenant_id", table_name, ["tenant_id"])
        op.create_index(f"ix_{table_name}_organisation_id", table_name, ["organisation_id"])

    op.create_table(
        "data_vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_vehicle_id", sa.String(200), nullable=False),
        sa.Column("registration_number", sa.String(100), nullable=True),
        sa.Column("vehicle_type", sa.String(150), nullable=False),
        sa.Column("fuel_type", sa.String(100), nullable=True),
        sa.Column("gross_vehicle_weight_kg", sa.Numeric(18, 3), nullable=True),
        sa.Column("model_year", sa.Integer(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_record_hash", sa.String(64), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "external_vehicle_id", name="uq_data_vehicle_external_id"),
    )
    standard_columns("data_vehicles", "external_vehicle_id")

    op.create_table(
        "data_shipments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_shipment_id", sa.String(200), nullable=False),
        sa.Column("external_consignment_id", sa.String(200), nullable=True),
        sa.Column("shipment_date", sa.Date(), nullable=True),
        sa.Column("origin_country_code", sa.String(20), nullable=True),
        sa.Column("origin_postcode", sa.String(30), nullable=True),
        sa.Column("destination_country_code", sa.String(20), nullable=True),
        sa.Column("destination_postcode", sa.String(30), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_record_hash", sa.String(64), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "external_shipment_id", name="uq_data_shipment_external_id"),
    )
    standard_columns("data_shipments", "external_shipment_id")

    op.create_table(
        "data_journeys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_journey_id", sa.String(200), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_vehicles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_shipments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("journey_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("journey_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("distance_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("distance_unit", sa.String(100), nullable=True),
        sa.Column("distance_source", sa.String(100), nullable=True),
        sa.Column("route_reference", sa.String(300), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_record_hash", sa.String(64), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "external_journey_id", name="uq_data_journey_external_id"),
    )
    standard_columns("data_journeys", "external_journey_id")
    op.create_index("ix_data_journeys_vehicle_id", "data_journeys", ["vehicle_id"])
    op.create_index("ix_data_journeys_shipment_id", "data_journeys", ["shipment_id"])

    op.create_table(
        "data_fuel_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_fuel_record_id", sa.String(200), nullable=False),
        sa.Column("journey_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_journeys.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_vehicles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fuel_type", sa.String(100), nullable=False),
        sa.Column("quantity_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("quantity_unit", sa.String(100), nullable=False),
        sa.Column("quantity_source", sa.String(100), nullable=True),
        sa.Column("transaction_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_record_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "external_fuel_record_id", name="uq_data_fuel_external_id"),
    )
    standard_columns("data_fuel_records", "external_fuel_record_id")
    op.create_index("ix_data_fuel_records_journey_id", "data_fuel_records", ["journey_id"])
    op.create_index("ix_data_fuel_records_vehicle_id", "data_fuel_records", ["vehicle_id"])

    op.create_table(
        "data_payload_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_payload_record_id", sa.String(200), nullable=False),
        sa.Column("journey_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_journeys.id", ondelete="SET NULL"), nullable=True),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_shipments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quantity_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("quantity_unit", sa.String(100), nullable=False),
        sa.Column("quantity_source", sa.String(100), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_record_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "external_payload_record_id", name="uq_data_payload_external_id"),
    )
    standard_columns("data_payload_records", "external_payload_record_id")
    op.create_index("ix_data_payload_records_journey_id", "data_payload_records", ["journey_id"])
    op.create_index("ix_data_payload_records_shipment_id", "data_payload_records", ["shipment_id"])

    op.create_table(
        "data_operational_emissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_calculation_id", sa.String(200), nullable=False),
        sa.Column("journey_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_journeys.id", ondelete="SET NULL"), nullable=True),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_shipments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_vehicles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("activity_records.id", ondelete="SET NULL"), nullable=True),
        sa.Column("suggested_scope", sa.String(50), nullable=True),
        sa.Column("suggested_scope_3_category", sa.Integer(), nullable=True),
        sa.Column("classification_reason", sa.Text(), nullable=True),
        sa.Column("classification_status", data_classification_status, nullable=False, server_default="suggested"),
        sa.Column("confirmed_scope", sa.String(50), nullable=True),
        sa.Column("confirmed_scope_3_category", sa.Integer(), nullable=True),
        sa.Column("methodology_version", sa.String(100), nullable=False),
        sa.Column("total_kg_co2e", sa.Numeric(30, 15), nullable=False),
        sa.Column("co2_kg", sa.Numeric(30, 15), nullable=True),
        sa.Column("ch4_kg_co2e", sa.Numeric(30, 15), nullable=True),
        sa.Column("n2o_kg_co2e", sa.Numeric(30, 15), nullable=True),
        sa.Column("data_quality_level", sa.String(50), nullable=True),
        sa.Column("data_quality_score", sa.Integer(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_record_version", sa.String(100), nullable=True),
        sa.Column("source_record_hash", sa.String(64), nullable=False),
        sa.Column("lineage_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "external_calculation_id", name="uq_data_operational_emission_external_id"),
    )
    standard_columns("data_operational_emissions", "external_calculation_id")
    for column in ("journey_id", "shipment_id", "vehicle_id", "activity_id", "classification_status"):
        op.create_index(f"ix_data_operational_emissions_{column}", "data_operational_emissions", [column])


def downgrade() -> None:
    op.drop_table("data_operational_emissions")
    op.drop_table("data_payload_records")
    op.drop_table("data_fuel_records")
    op.drop_table("data_journeys")
    op.drop_table("data_shipments")
    op.drop_table("data_vehicles")
    op.drop_table("data_import_errors")
    op.drop_table("data_import_batches")
    op.drop_table("data_organisation_mappings")
    for name in (
        "data_classification_status",
        "data_record_type",
        "data_import_status",
    ):
        postgresql.ENUM(name=name).drop(op.get_bind(), checkfirst=True)
