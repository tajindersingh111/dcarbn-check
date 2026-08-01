# Redis Unavailable

Redis contains rate-limit counters and operational session support. PostgreSQL
remains the source of truth for refresh-session records.

1. Confirm Redis health, authentication, memory policy, and disk state.
2. Production rate limiting fails closed, so authentication and API traffic may return 503.
3. Restore Redis service from AOF when available; otherwise start a clean instance.
4. A clean Redis start loses counters but does not lose inventory or audit data.
5. Monitor login and rate-limit activity closely for one hour after recovery.
6. Confirm readiness and normal refresh-token rotation before resolution.
