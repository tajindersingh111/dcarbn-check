# Resilience Exercises, SLOs and Release Evidence

The platform defines release-gating SLOs for API availability, p95 latency,
server-error rate, backup freshness, WAL freshness, PITR readiness, failover RPO,
and failover RTO.

Weekly automation validates code and deployment contracts. Environment exercises
produce JSON evidence with timestamps, measurements, outcomes, and checksums.
Production evidence is signed with Ed25519 and verified before release approval.

Dry-run failover exercises validate readiness without promotion. Simulation mode
uses a deployment-specific reversible hook. Destructive exercises invoke the
controlled failover command and require explicit confirmation.

The release gate checks application and recovery readiness, Prometheus SLO
queries, latest signed failover evidence, RPO/RTO measurements, evidence age, and
immutable image digest references. Its JSON decision is retained as release
evidence.
