# Elevated API Error Rate

1. Break down `dcarbn_http_requests_total` by route and status.
2. Correlate the increase with traces and structured logs using trace IDs.
3. Check PostgreSQL saturation, Redis errors, upstream DATa failures, and recent releases.
4. Disable or isolate the failing workflow when it is not required for core reporting.
5. Roll back when the error is release-related.
6. Confirm the 5xx ratio remains below 1% for 15 minutes before resolving.
