# D-carbN Pilot Release Acceptance Checklist

## Release identification

| Field | Value |
|---|---|
| Release version | |
| Commit SHA | |
| Backend image digest | |
| Frontend image digest | |
| Target environment | |
| Pilot tenant | |
| Planned start | |
| Change owner | |
| Incident commander | |
| Rollback owner | |

## Gate A — Build and source assurance

- [ ] Backend dependency installation succeeds from the approved package registry.
- [ ] `pytest` completes with no failed or skipped mandatory tests.
- [ ] Ruff reports no violations.
- [ ] Mypy strict checking passes.
- [ ] Frontend `package-lock.json` exists and is reviewed.
- [ ] `npm ci` succeeds without lockfile changes.
- [ ] TypeScript checking passes.
- [ ] Frontend linting passes.
- [ ] Next.js production build succeeds.
- [ ] Playwright authentication, security, workflow, and live-API suites pass.
- [ ] Gitleaks, pip-audit, and npm audit pass policy.
- [ ] Backend and frontend images use immutable SHA-256 digests.
- [ ] SPDX and CycloneDX SBOMs exist for both images.
- [ ] Grype and Trivy results pass vulnerability policy.
- [ ] Cosign signatures and provenance attestations verify.
- [ ] Release-gate decision is `approved`.

**Owner:** Engineering lead  
**Required evidence:** CI run, test reports, SBOMs, scan reports, signatures, provenance, release-gate JSON.

## Gate B — Database and tenant isolation

- [ ] Alembic upgrade succeeds from a production-equivalent database snapshot.
- [ ] Migration rollback strategy is reviewed.
- [ ] Exactly one Alembic head exists.
- [ ] Tenant A cannot read, mutate, approve, export, or administer Tenant B data.
- [ ] Cross-tenant object identifiers return a non-disclosing response.
- [ ] Audit-report hashes and evidence references remain tenant scoped.
- [ ] Locked inventories reject all mutation paths.
- [ ] Restatement versions cannot collide under concurrent requests.
- [ ] Approval and report version creation is concurrency safe.
- [ ] Database connection-pool limits are validated under expected pilot load.

**Owner:** Backend lead and database owner  
**Required evidence:** Migration report, tenant-isolation test report, concurrency test report.

## Gate C — Carbon-accounting acceptance

- [ ] Scope 1 stationary combustion calculation is independently reconciled.
- [ ] Scope 1 mobile combustion calculation is independently reconciled.
- [ ] Scope 1 fugitive-emission calculation is independently reconciled.
- [ ] Scope 2 location-based calculation is independently reconciled.
- [ ] Scope 2 market-based calculation and contractual-instrument hierarchy are reconciled.
- [ ] All supported Scope 3 categories are mapped to the correct calculation method.
- [ ] Units, conversions, decimal precision, and kgCO2e storage are verified.
- [ ] UK 2026 factors are imported with source, version, geography, validity, and method metadata.
- [ ] Factor selection is deterministic and reproducible.
- [ ] Evidence and factor snapshots remain immutable after approval.
- [ ] DATa results reconcile to the specialist platform's signed/versioned response.
- [ ] DATa review, rejection, conversion, and resubmission paths pass.
- [ ] Inventory approval, locking, restatement, and audit-report workflows pass.
- [ ] Representative audit-report hashes reproduce exactly.

**Owner:** Carbon-accounting subject-matter expert  
**Required evidence:** Reconciliation workbook, factor provenance report, DATa contract results, signed acceptance.

## Gate D — Identity and security

- [ ] Tenant onboarding creates the intended initial administrator only.
- [ ] Invitation expiry, acceptance, replay, and revocation behavior pass.
- [ ] Password policy and recovery flows pass.
- [ ] MFA enrollment, challenge, recovery, and reset pass.
- [ ] HTTP-only, Secure, SameSite session-cookie behavior is verified in the deployed browser.
- [ ] Refresh-token rotation and reuse detection pass.
- [ ] Account lockout and administrator unlock pass.
- [ ] Role changes take effect without cross-session privilege leakage.
- [ ] Rate limits behave correctly behind the production proxy.
- [ ] CSP, HSTS, trusted-host, referrer, permissions, and frame protections are present.
- [ ] Security events are tenant scoped and visible to authorized administrators.
- [ ] Penetration-test critical and high findings are closed or formally accepted.

**Owner:** Security lead  
**Required evidence:** Security test report, browser header capture, penetration-test report, exception register.

## Gate E — Reliability and recovery

- [ ] Logical backup completes, encrypts, uploads, and verifies.
- [ ] Physical base backup completes and verifies.
- [ ] WAL archive freshness remains within policy.
- [ ] PITR reaches a selected timestamp in an isolated environment.
- [ ] Restore validation confirms migrations, tenants, inventories, calculations, and reports.
- [ ] Regional standby is healthy and replaying the current timeline.
- [ ] Fencing and routing hooks are real provider integrations, not examples.
- [ ] Regional failover exercise meets RPO and RTO targets.
- [ ] Failback procedure is reviewed and exercised.
- [ ] Redis-loss recovery behavior is accepted.
- [ ] Backup, WAL, PITR, database, Redis, and regional alerts reach the on-call destination.

**Owner:** Operations lead  
**Required evidence:** Backup ID, restore report, PITR target, failover evidence, alert-delivery evidence.

## Gate F — Kubernetes and GitOps

- [ ] Staging, primary, and standby Kustomize overlays render successfully.
- [ ] Kubeconform validates all rendered resources.
- [ ] Argo CD applications are `Synced` and `Healthy`.
- [ ] Kyverno or Gatekeeper policies enforce the approved production policy set.
- [ ] External Secrets synchronize all required values.
- [ ] Network policies allow required dependencies and deny unintended traffic.
- [ ] Horizontal autoscaling and disruption budgets are exercised.
- [ ] Database PreSync migration job succeeds.
- [ ] Backend canary completes all analysis stages.
- [ ] Frontend canary completes all analysis stages.
- [ ] Failed canary automatically preserves or restores the stable revision.
- [ ] GitOps reconciliation and promotion evidence is retained.

**Owner:** Platform lead  
**Required evidence:** Rendered manifests, policy reports, Argo CD status, rollout analysis, promotion JSON.

## Gate G — Observability and support

- [ ] API throughput, latency, error, dependency, security, backup, WAL, PITR, and region metrics are present.
- [ ] Logs contain correlation and trace identifiers without secrets or personal data.
- [ ] Traces link frontend/API requests to database and Redis operations.
- [ ] Grafana dashboards load and represent current data.
- [ ] Fast- and slow-burn SLO alerts are tested.
- [ ] Alertmanager routes warning and critical alerts correctly.
- [ ] On-call contacts, escalation paths, and support hours are confirmed.
- [ ] Incident, security, backup, restore, failover, rollback, and policy runbooks are approved.
- [ ] Pilot-user support and defect-triage procedures are active.

**Owner:** Operations and support leads  
**Required evidence:** Dashboard screenshots, synthetic alert results, on-call schedule, approved runbooks.

## Gate H — Accessibility, privacy, and user acceptance

- [ ] Keyboard-only navigation passes for every pilot workflow.
- [ ] Focus order and visible focus indicators pass.
- [ ] Forms expose labels, descriptions, required state, and actionable errors.
- [ ] Tables and status changes are usable by screen readers.
- [ ] Colour contrast meets the agreed WCAG target.
- [ ] Responsive behavior passes supported desktop, tablet, and mobile widths.
- [ ] Privacy notice, data-retention policy, processor list, and lawful basis are approved.
- [ ] Data export and deletion procedures are tested.
- [ ] Pilot administrators complete onboarding and role-administration scenarios.
- [ ] Pilot users complete organisation, inventory, activity, DATa review, approval, and report scenarios.
- [ ] All severity-one and severity-two acceptance defects are closed.

**Owner:** Product owner, accessibility reviewer, and privacy lead  
**Required evidence:** Accessibility report, privacy approval, UAT scripts, defect register.

## Launch decision

A pilot release is approved only when every mandatory checkbox above is complete
or a written exception includes an owner, risk statement, compensating control,
expiry, and approving authority.

| Approval | Name | Decision | Date | Signature/reference |
|---|---|---|---|---|
| Product owner | | | | |
| Engineering lead | | | | |
| Carbon-accounting SME | | | | |
| Security lead | | | | |
| Operations lead | | | | |
| Privacy lead | | | | |

## Immediate rollback criteria

Rollback or disable pilot traffic when any of the following occurs:

- Cross-tenant data exposure or privilege escalation.
- Incorrect approved inventory totals or non-reproducible report hashes.
- Irrecoverable evidence, approval, lock, or restatement corruption.
- Sustained critical SLO burn or elevated 5xx errors.
- Database integrity failure, unbounded WAL accumulation, or failed backup chain.
- Authentication bypass, signing-key compromise, or refresh-token reuse incident.
- Failed canary with stable-service impact.
- A severity-one privacy, security, or carbon-accounting defect.
