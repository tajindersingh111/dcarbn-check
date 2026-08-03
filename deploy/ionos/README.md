# IONOS Docker Compose staging deployment

This pack deploys D-carbN to one isolated IONOS Ubuntu server with Docker Compose, HTTPS via Caddy, private PostgreSQL and Redis networks, health checks, and an application-image rollback path.

## Recommended server

- Ubuntu 24.04 LTS
- 4 vCPU, 8 GB RAM, 160 GB SSD
- Static public IPv4 address
- Ports 80 and 443 open publicly
- Port 22 restricted to the administrator's public IP

Use a non-production domain such as `staging.scope.d-carbnanalytics.com`. Create its DNS A record before starting Caddy so that TLS can be issued.

## 1. Bootstrap the server

Copy the repository to the server, then run:

```bash
sudo bash deploy/ionos/bootstrap-ubuntu.sh
sudo usermod -aG docker "$USER"
```

Sign out and back in after adding the Docker group. The bootstrap script deliberately does not enable UFW, avoiding accidental SSH lockout. After confirming the administrator IP:

```bash
sudo ufw allow from <ADMIN_IP>/32 to any port 22 proto tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 2. Configure the staging environment

```bash
cp deploy/ionos/staging.env.example deploy/ionos/staging.env
chmod 600 deploy/ionos/staging.env
mkdir -p secrets
chmod 700 secrets
```

Edit `deploy/ionos/staging.env` and create these root-only secret files:

| File | Purpose |
|---|---|
| `secrets/secret_key` | Application signing secret |
| `secrets/mfa_encryption_key` | MFA data encryption key |
| `secrets/postgres_password` | PostgreSQL password |
| `secrets/redis_password` | Redis password |
| `secrets/database_url` | Complete PostgreSQL connection URL |
| `secrets/redis_url` | Complete Redis connection URL |
| `secrets/smtp_password` | SMTP credential |

Generate cryptographic secrets with `openssl rand -hex 32`. URL-encode database and Redis passwords when embedding them in connection URLs. Do not commit `staging.env` or anything under `secrets/`.

## 3. Deploy and verify

```bash
bash deploy/ionos/deploy.sh
bash deploy/ionos/health-check.sh
docker compose --env-file deploy/ionos/staging.env -f docker-compose.staging.yml ps
```

The deployment builds images on the server, retains the preceding application images as `staging-previous`, runs database migrations, starts the stack, and verifies HTTPS.

## 4. Automated deployment

Create a protected GitHub Environment named `staging`, preferably with a required reviewer. Add:

| GitHub setting | Value |
|---|---|
| Secret `IONOS_SSH_HOST` | Server IP or hostname |
| Secret `IONOS_SSH_USER` | Non-root deployment user |
| Secret `IONOS_SSH_PRIVATE_KEY` | Dedicated deployment private key |
| Secret `IONOS_SSH_KNOWN_HOSTS` | Pinned result from `ssh-keyscan`, verified independently |
| Variable `IONOS_STAGING_PATH` | Optional; defaults to `/opt/dcarbn-staging` |

Run **Deploy IONOS staging** from GitHub Actions and set `deploy=true`. Runtime configuration and secrets must already exist on the server.

## 5. Rollback

```bash
bash deploy/ionos/rollback.sh
```

Rollback restores the preceding backend and frontend images. It does not reverse database migrations. Schema changes must remain backwards compatible or have an independently reviewed restore plan.

## Operational gates before stakeholder UAT

- DNS and automatic TLS confirmed
- SMTP delivery tested with a staging-only sender
- Database backup and restore rehearsal completed
- IONOS snapshot schedule enabled
- Logs and disk utilisation monitored
- No production personal data copied into staging
- Named owner for deploy approval, incident response, and rollback
