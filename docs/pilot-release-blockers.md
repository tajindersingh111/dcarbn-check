# Pilot Release Blockers

## P0 — Frontend dependency lockfile

`frontend/package-lock.json` is absent. Generate it using the approved public or
mirrored npm registry, review the resolved dependency tree, and commit it.
The pilot release remains blocked until `npm ci`, type checking, linting,
production build, and every Playwright suite pass from that lockfile.

## P0 — Complete backend quality suite

Run the repository with Python 3.12 and install `backend[dev]`. Execute PostgreSQL
migrations, pytest, Ruff, and strict Mypy against PostgreSQL and Redis. No
mandatory test may fail or be silently skipped.

## P0 — Production-equivalent integration environment

Build and scan backend and frontend images, start PostgreSQL and Redis, execute
all API and browser workflows, and retain logs and test artifacts.

## P0 — Carbon-accounting reconciliation

An independent carbon-accounting reviewer must reconcile Scope 1, Scope 2,
supported Scope 3, UK 2026 factors, unit conversions, DATa results, inventory
locks, restatements, and representative audit-report hashes.

## P0 — Recovery and regional exercises

Complete an encrypted backup, physical base backup, selected-time PITR restore,
regional failover, and failback. Provider fencing and routing hooks must replace
the example implementations.

## P1 — Kubernetes acceptance

Render every Kustomize overlay, validate schemas, enforce admission policies,
synchronize Argo CD applications, and complete successful and failed canary
tests.

## P1 — Security, accessibility, privacy, and UAT

Close or formally accept penetration-test findings, complete browser security
testing, accessibility review, privacy approval, pilot-admin training, and
end-user acceptance scenarios.
