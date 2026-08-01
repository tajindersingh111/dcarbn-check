# Infrastructure

The local environment uses Docker Compose.

Production infrastructure should add:

- Managed PostgreSQL with point-in-time recovery
- Managed Redis
- S3-compatible encrypted object storage
- Secret manager
- TLS termination
- Web application firewall
- Central logs, metrics and traces
- Automated database backups
- Separate development, staging and production environments
- Infrastructure as code
