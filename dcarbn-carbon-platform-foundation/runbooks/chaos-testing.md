# Chaos Testing

Supported scenarios include backend and gateway pause, Redis and PostgreSQL restart,
WAL-shipping interruption, backend network latency, and regional isolation.

Run only in a controlled environment with current backups, working alerts, and an
identified abort owner. Start with one fault at a time. Record expected behavior,
observed behavior, recovery duration, alerts fired, data-integrity results, and
corrective actions. Regional isolation requires a provider-specific reversible hook.
