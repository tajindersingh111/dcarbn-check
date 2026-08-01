# Release Gate Blocked

A release remains blocked when readiness fails, recovery readiness is degraded,
an SLO is outside policy, image references are mutable, signed failover evidence
is absent or stale, or evidence verification fails.

Do not bypass the gate without recorded executive, security, and operations
approval. Correct the failing check, regenerate signed evidence, and rerun the
gate. Preserve both blocked and approved decisions for audit.
