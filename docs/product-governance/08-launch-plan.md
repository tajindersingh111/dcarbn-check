# Launch plan

## Launch stages

### 1. Internal completion
- Product Owner confirms MVP against the PRD.
- QA runs functional, role, accessibility, browser, migration and negative-path tests.
- Security gates, backup restore and disaster-recovery evidence pass.
- User guide and operating manual match the release.

### 2. Paul demonstration and business acceptance
Use a scripted journey: login; organisation/inventory; manual and CSV input; connected systems; Scope 3 screening; review; approval; report. Record accepted items, defects, enhancements and explicit sign-off.

### 3. Pilot customer validation
Select one representative customer with controlled non-production or approved pilot data. Agree success criteria, responsibilities, retention, support channel and feedback cadence. Complete onboarding, one inventory journey, report review and exit interview.

### 4. Production readiness
Approve hosting, domain/DNS/TLS, secret manager, identity decision, vendor OAuth apps, email delivery, observability, backups, support roster, privacy/legal terms and penetration-test remediation. Rehearse migration, rollback, restore and incident communication.

### 5. Production launch
Use a controlled release window. Deploy signed immutable images, migrate, run smoke tests, verify monitoring/email/auth/reporting/backups, invite initial users and maintain a launch bridge. Record go/no-go and evidence.

### 6. Hypercare
For the first two weeks, review health and customer feedback daily. Classify issues by severity, publish workarounds, measure activation, and hold a launch retrospective.

## Go/no-go gates

- No unresolved severity-1/2 defect or critical/high exploitable vulnerability.
- CI and supply-chain security green at the release commit.
- Independent penetration test completed and accepted.
- Pilot success criteria met or deviations explicitly accepted.
- Restore test and operational monitoring verified.
- Identity, hosting, secrets, legal/privacy, support and commercial owners signed off.
- Rollback path and customer communication ready.

## Roles

Product Owner: scope and acceptance. Technical Owner: architecture/release. Security Owner: risk and incident readiness. Operations Owner: hosting, monitoring, backup and support. Commercial Owner: contract/pricing. Customer Success Owner: onboarding/training/pilot feedback. One person may hold multiple roles, but every role must have a named owner and deputy.

## Launch-day evidence

Release digest, migration output, test/security results, configuration approval, smoke-test results, monitoring screenshots, backup confirmation, customer invitations, incident contact list and go/no-go decision.
