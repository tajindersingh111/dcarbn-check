# Disk Pressure

1. Identify the filesystem and fastest-growing directory.
2. Check PostgreSQL data, Redis AOF, backups, Prometheus, Loki, Tempo, and container logs.
3. Preserve required retention and audit evidence before deletion.
4. Remove expired backups only after confirming remote copies and a recent restore drill.
5. Expand storage when growth is legitimate.
6. Resolve only after free space exceeds 25% and growth is understood.
