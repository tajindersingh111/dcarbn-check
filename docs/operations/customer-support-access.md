# Customer support access

## Purpose

D-carbN operators sometimes need to diagnose a customer workspace or help complete a
configuration change. Support access must never rely on a shared password, a hidden
administrator URL, or a permanent tenant bypass.

## Required control model

1. A platform administrator requests access to one named tenant and records a support
   reason or ticket reference.
2. A tenant administrator approves the request, except during a declared break-glass
   incident covered by the customer contract.
3. The platform requires multi-factor authentication and creates a short-lived support
   session with a maximum duration of 60 minutes.
4. The session is read-only by default. Any requested write capability is selected
   explicitly and shown to the tenant approver.
5. The application displays a persistent support-session banner containing the operator,
   tenant, expiry time, and an **End session** control.
6. Entry, exit, every record viewed, export, and write are added to the immutable security
   audit log with the operator identity and original support request.
7. The tenant can revoke the session immediately and can export the complete support log.

## Implementation boundaries

- Preserve normal tenant row-level security; support access supplies an audited tenant
  context rather than disabling isolation.
- Do not expose customer passwords, session cookies, invitation tokens, Railway secrets,
  or database credentials to support staff or automation.
- Do not allow a support operator to approve their own calculation, inventory, or report.
- Require a second platform administrator for break-glass activation and notify the tenant
  immediately.
- Application code changes continue through a reviewed GitHub branch and Railway
  deployment. Support sessions are for customer configuration and diagnostics, not for
  editing production source code.

## Delivery sequence

1. Add support-request and support-session database models.
2. Add tenant approval, revocation, and expiry endpoints.
3. Add step-up MFA and narrowly scoped support-session claims.
4. Add the support banner and platform administration queue.
5. Add audit, security, tenant-isolation, expiry, and break-glass tests.
6. Complete an independent security review before enabling the feature in production.
