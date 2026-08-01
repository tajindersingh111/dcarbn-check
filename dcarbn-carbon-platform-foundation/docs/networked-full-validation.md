# Networked Full Validation

The workflow `.github/workflows/networked-full-validation.yml` is the release
candidate validation entry point for dependencies and tools that are unavailable
in the artifact environment.

## Start the workflow

1. Push this repository to GitHub.
2. Open **Actions**.
3. Select **Networked full validation**.
4. Select **Run workflow**.
5. Keep **Create a pull request containing frontend/package-lock.json** enabled.
6. Enable the live API test only after configuring `E2E_ACCESS_TOKEN` and
   `E2E_API_BASE_URL`.

The workflow uses the public npm registry to generate
`frontend/package-lock.json`, uploads it as an artifact, and optionally creates a
pull request containing the generated lockfile.

## Required repository configuration

Optional live API test:

```text
Secret: E2E_ACCESS_TOKEN
Variable: E2E_API_BASE_URL
```

The default deterministic browser suites do not require those values because
they intercept the API requests.

## Jobs

### Frontend lockfile

- Pins npm 10.8.2.
- Generates the lockfile twice from the same package manifest.
- Calculates a SHA-256 checksum.
- Uploads the lockfile for downstream jobs.
- Optionally creates a pull request.

### Backend

- Starts PostgreSQL 16 and Redis 7 service containers.
- Installs `backend[dev]`.
- Applies all Alembic migrations.
- Runs Ruff, strict Mypy, pytest, and coverage.
- Uploads JUnit and coverage evidence.

### Frontend

- Downloads and verifies the generated lockfile.
- Runs `npm ci`.
- Runs TypeScript, ESLint, and the Next.js production build.
- Installs Playwright Chromium.
- Runs authentication, security, and workflow browser suites.
- Optionally runs the configured live API smoke test.

### Containers

- Builds backend and frontend production images.
- Starts PostgreSQL, Redis, backend, and frontend containers.
- Applies migrations using the built backend image.
- Verifies backend and frontend health.
- Validates development and production Compose models.
- Uploads image metadata and container logs.

### Kubernetes

- Renders staging, primary, and standby Kustomize overlays.
- Substitutes validation-only immutable image digests.
- Runs kubeconform.
- Rejects mutable images.
- Evaluates the Kyverno policy set.
- Validates Argo CD and policy YAML.
- Uploads rendered manifests and checksums.

### Summary

The summary job fails unless every preceding job succeeds. It uploads
`networked-validation.json` with the lockfile checksum, commit SHA, job results,
and final decision.

## Acceptance

Do not merge the lockfile pull request or approve the pilot release unless all
jobs in the same workflow run pass. Download and retain these artifacts:

```text
frontend-lockfile
backend-validation
frontend-validation
container-validation
kubernetes-validation
networked-validation-summary
```
