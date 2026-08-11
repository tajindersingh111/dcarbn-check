"""Enable PostgreSQL row-level security for tenant-owned data.

Revision ID: 0022
Revises: 0021
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = (
    "activity_records",
    "audit_events",
    "organisational_boundaries",
    "boundary_memberships",
    "calculation_runs",
    "calculation_results",
    "data_organisation_mappings",
    "data_import_batches",
    "data_vehicles",
    "data_shipments",
    "data_journeys",
    "data_fuel_records",
    "data_payload_records",
    "data_operational_emissions",
    "data_calculation_comparisons",
    "data_accounting_connections",
    "data_accounting_sync_jobs",
    "data_operational_emission_reviews",
    "factor_resolution_records",
    "tenant_memberships",
    "roles",
    "user_invitations",
    "refresh_sessions",
    "reporting_periods",
    "inventories",
    "scope_3_category_dispositions",
    "inventory_approvals",
    "inventory_locks",
    "inventory_restatements",
    "audit_reports",
    "organisations",
    "legal_entities",
    "sites",
    "password_reset_tokens",
    "mfa_challenges",
    "durable_workloads",
)

_CONTEXT = (
    "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid"
)


def _execute(statement: str) -> None:
    op.execute(statement)


def upgrade() -> None:
    _execute(
        """
        DO $roles$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dcarbn_app') THEN
                CREATE ROLE dcarbn_app NOLOGIN NOBYPASSRLS;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dcarbn_worker') THEN
                CREATE ROLE dcarbn_worker NOLOGIN NOBYPASSRLS;
            END IF;
            EXECUTE format('GRANT dcarbn_app, dcarbn_worker TO %I', current_user);
        END
        $roles$;
        """
    )
    _execute("GRANT USAGE ON SCHEMA public TO dcarbn_app, dcarbn_worker")
    _execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
        "TO dcarbn_app"
    )
    _execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON "
        "durable_workloads, calculation_runs, calculation_results, "
        "activity_records, inventories, reporting_periods, "
        "factor_resolution_records, audit_events "
        "TO dcarbn_worker"
    )
    _execute(
        "GRANT SELECT ON emission_factor_sets, emission_factors, "
        "methodology_versions, methodology_packs TO dcarbn_worker"
    )
    _execute(
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public "
        "TO dcarbn_app, dcarbn_worker"
    )

    for table in TENANT_TABLES:
        _execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        _execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        _execute(
            f'CREATE POLICY "{table}_tenant_isolation" ON "{table}" '
            f"USING (tenant_id = {_CONTEXT}) "
            f"WITH CHECK (tenant_id = {_CONTEXT})"
        )

    _execute("ALTER TABLE security_events ENABLE ROW LEVEL SECURITY")
    _execute("ALTER TABLE security_events FORCE ROW LEVEL SECURITY")
    _execute(
        "CREATE POLICY security_events_tenant_read ON security_events "
        f"FOR SELECT USING (tenant_id = {_CONTEXT})"
    )
    _execute(
        "CREATE POLICY security_events_tenant_write ON security_events "
        "FOR INSERT WITH CHECK "
        f"(tenant_id = {_CONTEXT} OR tenant_id IS NULL)"
    )

    _execute("ALTER TABLE data_import_errors ENABLE ROW LEVEL SECURITY")
    _execute("ALTER TABLE data_import_errors FORCE ROW LEVEL SECURITY")
    _execute(
        "CREATE POLICY data_import_errors_tenant_isolation ON data_import_errors "
        "USING (EXISTS ("
        "SELECT 1 FROM data_import_batches batch "
        "WHERE batch.id = data_import_errors.batch_id "
        f"AND batch.tenant_id = {_CONTEXT}"
        ")) WITH CHECK (EXISTS ("
        "SELECT 1 FROM data_import_batches batch "
        "WHERE batch.id = data_import_errors.batch_id "
        f"AND batch.tenant_id = {_CONTEXT}"
        "))"
    )

    _execute("ALTER TABLE membership_roles ENABLE ROW LEVEL SECURITY")
    _execute("ALTER TABLE membership_roles FORCE ROW LEVEL SECURITY")
    _execute(
        "CREATE POLICY membership_roles_tenant_isolation ON membership_roles "
        "USING (EXISTS ("
        "SELECT 1 FROM tenant_memberships membership "
        "WHERE membership.id = membership_roles.membership_id "
        f"AND membership.tenant_id = {_CONTEXT}"
        ")) WITH CHECK (EXISTS ("
        "SELECT 1 FROM tenant_memberships membership "
        "JOIN roles role ON role.id = membership_roles.role_id "
        "WHERE membership.id = membership_roles.membership_id "
        f"AND membership.tenant_id = {_CONTEXT} "
        f"AND role.tenant_id = {_CONTEXT}"
        "))"
    )

    _execute("ALTER TABLE methodology_packs ENABLE ROW LEVEL SECURITY")
    _execute("ALTER TABLE methodology_packs FORCE ROW LEVEL SECURITY")
    _execute(
        "CREATE POLICY methodology_packs_visible ON methodology_packs "
        "FOR SELECT USING ("
        f"owner_tenant_id IS NULL OR owner_tenant_id = {_CONTEXT}"
        ")"
    )
    _execute(
        "CREATE POLICY methodology_packs_tenant_write ON methodology_packs "
        "FOR ALL USING ("
        f"owner_tenant_id = {_CONTEXT}"
        ") WITH CHECK ("
        f"owner_tenant_id = {_CONTEXT}"
        ")"
    )

    _execute(
        """
        CREATE OR REPLACE FUNCTION public.dcarbn_resolve_auth_tenant(
            purpose text,
            supplied_token_hash text
        )
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT CASE purpose
                WHEN 'refresh_session' THEN (
                    SELECT tenant_id FROM public.refresh_sessions
                    WHERE token_hash = supplied_token_hash
                    LIMIT 1
                )
                WHEN 'mfa_challenge' THEN (
                    SELECT tenant_id FROM public.mfa_challenges
                    WHERE token_hash = supplied_token_hash
                    LIMIT 1
                )
                WHEN 'user_invitation' THEN (
                    SELECT tenant_id FROM public.user_invitations
                    WHERE token_hash = supplied_token_hash
                    LIMIT 1
                )
                WHEN 'password_reset' THEN (
                    SELECT tenant_id FROM public.password_reset_tokens
                    WHERE token_hash = supplied_token_hash
                    LIMIT 1
                )
                ELSE NULL
            END
        $function$;
        """
    )
    _execute(
        "REVOKE ALL ON FUNCTION public.dcarbn_resolve_auth_tenant(text, text) "
        "FROM PUBLIC"
    )
    _execute(
        "GRANT EXECUTE ON FUNCTION public.dcarbn_resolve_auth_tenant(text, text) "
        "TO dcarbn_app"
    )


def downgrade() -> None:
    _execute(
        "DROP FUNCTION IF EXISTS public.dcarbn_resolve_auth_tenant(text, text)"
    )
    for table in (
        "methodology_packs",
        "membership_roles",
        "data_import_errors",
        "security_events",
        *reversed(TENANT_TABLES),
    ):
        _execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
