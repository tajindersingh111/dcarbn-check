# Rate-Limit Saturation

1. Identify affected policy, routes, IPs, and tenants.
2. Distinguish abuse from a legitimate client retry loop or deployment defect.
3. Stop faulty clients before raising limits.
4. Block abusive sources at the gateway where safe.
5. Change limits through reviewed configuration and monitor error and latency impact.
6. Never disable production rate limiting globally during an active attack.
