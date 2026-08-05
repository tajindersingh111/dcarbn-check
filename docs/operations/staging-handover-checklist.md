# Staging operational handover checklist

## Ownership

| Responsibility | Named owner required |
|---|---|
| Business acceptance and go/no-go | Product owner |
| Application and database | Technical owner |
| IONOS account, network and DNS | Infrastructure owner |
| Security incidents and access reviews | Security owner |
| Deployment approval and rollback | Release owner |
| Backup monitoring and restore drills | Recovery owner |

No staging deployment should begin until every responsibility has a named primary and deputy.

## Infrastructure handover

- [ ] IONOS Ubuntu 24.04 server specification recorded.
- [ ] Public IP and asset identifier recorded outside the repository.
- [ ] DNS A/AAAA records approved.
- [ ] SSH restricted to named administrators and dedicated keys.
- [ ] Root password login disabled after key access is proven.
- [ ] UFW permits only controlled SSH, HTTP and HTTPS.
- [ ] Automatic security updates and time synchronisation enabled.
- [ ] IONOS snapshot schedule and retention approved.
- [ ] Disk, memory and certificate-expiry monitoring enabled.

## Application handover

- [ ] Merged commit SHA and release owner recorded.
- [ ] `deploy/ionos/staging.env` created on host with mode 600.
- [ ] Docker secret files created with mode 600; none appear in Git.
- [ ] Compose configuration validates.
- [ ] Database migrations complete.
- [ ] Initial platform administrator bootstrapped once.
- [ ] Bootstrap password file, if used, securely removed.
- [ ] Staging label and URL verified.
- [ ] Health checks pass through HTTPS.
- [ ] SMTP invitation and password-reset delivery verified.
- [ ] Logs contain correlation IDs and no credentials or tokens.

## GitHub handover

- [ ] Protected `staging` environment created.
- [ ] Deployment requires a named reviewer.
- [ ] SSH host key independently verified and pinned.
- [ ] Environment secrets and path variable configured.
- [ ] Branch protection requires CI and supply-chain checks.
- [ ] Deployment workflow tested with a non-production change.
- [ ] Repository administrator list reviewed.

## Recovery handover

- [ ] Encrypted database backup completes.
- [ ] Backup exists outside the application server.
- [ ] Retention and deletion operate as configured.
- [ ] Isolated restore drill succeeds.
- [ ] Restored record counts and sampled audit hashes reconcile.
- [ ] Application-image rollback succeeds.
- [ ] Migration compatibility decision is recorded for every release.
- [ ] Recovery time and recovery point achieved are recorded.

## Security and compliance handover

- [ ] Staging contains no production personal data.
- [ ] Test accounts are individually assigned and MFA-enabled.
- [ ] Least-privilege role review completed.
- [ ] Access-removal process tested.
- [ ] Security-event alerts reach the named owner.
- [ ] Data retention and staging reset date recorded.
- [ ] Dependency, image and secret scans are green.
- [ ] Known risks and temporary exceptions have owners and expiry dates.

## Handover evidence

The infrastructure owner supplies a handover record containing the asset ID, domain, operating-system version, Docker/Compose versions, deployed commit, backup location reference, monitoring destinations, owner/deputy list, UAT evidence location and approved rollback decision. Credentials and private keys must never be included.

## Acceptance decision

- [ ] Technical owner confirms deployability and recovery.
- [ ] Security owner accepts remaining staging risks.
- [ ] Product owner accepts UAT entry.
- [ ] Release owner authorises the first staging deployment.
